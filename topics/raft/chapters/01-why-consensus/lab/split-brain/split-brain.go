package main

import (
	"fmt"
	"sync"
	"time"
)

// Config is a tiny container configuration.
type Config struct {
	CPU int
}

func (c Config) String() string { return fmt.Sprintf("{cpu:%d}", c.CPU) }

// Registry is the state machine: a map from container name to config.
type Registry struct {
	mu sync.Mutex
	m  map[string]Config
}

func NewRegistry() *Registry { return &Registry{m: make(map[string]Config)} }

func (r *Registry) Set(name string, c Config) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.m[name] = c
}

func (r *Registry) Snapshot() map[string]Config {
	r.mu.Lock()
	defer r.mu.Unlock()
	cp := make(map[string]Config, len(r.m))
	for k, v := range r.m {
		cp[k] = v
	}
	return cp
}

// Network is the fake in-memory message layer.
type Kind int

const (
	Heartbeat Kind = iota
	Write
)

type Msg struct {
	Kind     Kind
	From, To string
	Name     string
	Cfg      Config
}

type Network struct {
	mu      sync.Mutex
	inbox   map[string]chan Msg
	dropped map[string]bool
}

func NewNetwork(nodes []string) *Network {
	n := &Network{
		inbox:   make(map[string]chan Msg),
		dropped: make(map[string]bool),
	}
	for _, name := range nodes {
		n.inbox[name] = make(chan Msg, 64)
	}
	return n
}

func key(from, to string) string { return from + "->" + to }

func (n *Network) Drop(from, to string) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.dropped[key(from, to)] = true
}

func (n *Network) Send(m Msg) {
	n.mu.Lock()
	dropped := n.dropped[key(m.From, m.To)]
	n.mu.Unlock()
	if dropped {
		return
	}
	select {
	case n.inbox[m.To] <- m:
	default:
	}
}

func (n *Network) Inbox(name string) <-chan Msg { return n.inbox[name] }

// Node is one server in the naive single-leader cluster.
type Role int

const (
	Follower Role = iota
	Leader
)

func (r Role) String() string {
	if r == Leader {
		return "leader"
	}
	return "follower"
}

type Node struct {
	Name     string
	Peers    []string
	Net      *Network
	Registry *Registry

	mu            sync.Mutex
	role          Role
	lastHeartbeat time.Time
	stop          chan struct{}
}

func NewNode(name string, net *Network, peers []string) *Node {
	return &Node{
		Name:          name,
		Peers:         peers,
		Net:           net,
		Registry:      NewRegistry(),
		role:          Follower,
		lastHeartbeat: time.Now(),
		stop:          make(chan struct{}),
	}
}

func (n *Node) setLeader() {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.role = Leader
}

func (n *Node) isLeader() bool {
	n.mu.Lock()
	defer n.mu.Unlock()
	return n.role == Leader
}

func (n *Node) touchHeartbeat() {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.lastHeartbeat = time.Now()
}

func (n *Node) sinceHeartbeat() time.Duration {
	n.mu.Lock()
	defer n.mu.Unlock()
	return time.Since(n.lastHeartbeat)
}

func (n *Node) becomeLeader() {
	n.mu.Lock()
	if n.role == Leader {
		n.mu.Unlock()
		return
	}
	n.role = Leader
	n.mu.Unlock()
	fmt.Printf("[%s] timeout: promoting self to leader\n", n.Name)
}

func (n *Node) run(electionTimeout, heartbeat time.Duration) {
	tick := time.NewTicker(10 * time.Millisecond)
	defer tick.Stop()
	lastSent := time.Now()

	for {
		select {
		case <-n.stop:
			return
		case m := <-n.Net.Inbox(n.Name):
			if m.Kind == Heartbeat {
				n.touchHeartbeat()
			} else {
				n.Registry.Set(m.Name, m.Cfg)
			}
		case <-tick.C:
			if n.isLeader() && time.Since(lastSent) >= heartbeat {
				for _, p := range n.Peers {
					n.Net.Send(Msg{Kind: Heartbeat, From: n.Name, To: p})
				}
				lastSent = time.Now()
			}
			if !n.isLeader() && n.sinceHeartbeat() >= electionTimeout {
				n.becomeLeader()
			}
		}
	}
}

// Propose applies a write locally and fans it out to peers.
func (n *Node) Propose(name string, cfg Config) {
	n.Registry.Set(name, cfg)
	for _, p := range n.Peers {
		n.Net.Send(Msg{Kind: Write, From: n.Name, To: p, Name: name, Cfg: cfg})
	}
}

func (n *Node) View() (Role, map[string]Config) {
	n.mu.Lock()
	r := n.role
	n.mu.Unlock()
	return r, n.Registry.Snapshot()
}

func main() {
	nodes := []string{"A", "B", "C"}
	net := NewNetwork(nodes)

	A := NewNode("A", net, []string{"B", "C"})
	B := NewNode("B", net, []string{"A", "C"})
	C := NewNode("C", net, []string{"A", "B"})

	// A starts as the chosen leader.
	A.setLeader()

	// B and C use different election timeouts so only one promotes itself first.
	go A.run(150*time.Millisecond, 50*time.Millisecond)
	go B.run(150*time.Millisecond, 50*time.Millisecond)
	go C.run(250*time.Millisecond, 50*time.Millisecond)

	// Let initial heartbeats arrive so followers reset their timers.
	time.Sleep(80 * time.Millisecond)

	fmt.Println("== Phase 1: A leader, client writes web-1 cpu=2 ==")
	A.Propose("web-1", Config{CPU: 2})
	time.Sleep(60 * time.Millisecond)

	fmt.Println("== Phase 2: partition A from B,C; B times out and becomes leader ==")
	net.Drop("A", "B")
	net.Drop("A", "C")
	net.Drop("B", "A")
	net.Drop("C", "A")

	time.Sleep(220 * time.Millisecond)

	fmt.Println("== Phase 3: new client writes web-1 cpu=4 to leader B ==")
	B.Propose("web-1", Config{CPU: 4})
	time.Sleep(60 * time.Millisecond)

	fmt.Println("== Result: each node's view ==")
	for _, n := range []*Node{A, B, C} {
		role, reg := n.View()
		fmt.Printf("node %s: %s, registry %v\n", n.Name, role, reg)
	}
}
