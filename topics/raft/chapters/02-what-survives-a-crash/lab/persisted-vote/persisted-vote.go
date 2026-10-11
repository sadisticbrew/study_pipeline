package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

const stateFile = "data/raft-state.json"

// PersistentState is what must survive a crash.
type PersistentState struct {
	CurrentTerm int    `json:"currentTerm"`
	VotedFor    string `json:"votedFor"`
}

// Server keeps vote state in memory and writes it to disk before replying.
type Server struct {
	state PersistentState
}

func NewServer() *Server {
	return &Server{}
}

func (s *Server) load() error {
	b, err := os.ReadFile(stateFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	return json.Unmarshal(b, &s.state)
}

func (s *Server) persist() error {
	if err := os.MkdirAll(filepath.Dir(stateFile), 0750); err != nil {
		return err
	}
	b, err := json.Marshal(s.state)
	if err != nil {
		return err
	}
	f, err := os.OpenFile(stateFile, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0640)
	if err != nil {
		return err
	}
	if _, err := f.Write(b); err != nil {
		f.Close()
		return err
	}
	if err := f.Sync(); err != nil { // fsync before replying
		f.Close()
		return err
	}
	return f.Close()
}

// RequestVote handles a vote request. It persists state before replying.
func (s *Server) RequestVote(term int, candidate string) bool {
	fmt.Printf("term %d: received RequestVote from %s\n", term, candidate)
	if term > s.state.CurrentTerm {
		s.state.CurrentTerm = term
		s.state.VotedFor = ""
	}
	if term < s.state.CurrentTerm {
		return false
	}
	if s.state.VotedFor != "" && s.state.VotedFor != candidate {
		return false
	}
	s.state.VotedFor = candidate
	if err := s.persist(); err != nil {
		fmt.Printf("persist failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("persisted state: term=%d votedFor=%s\n", s.state.CurrentTerm, s.state.VotedFor)
	fmt.Printf("granted vote to %s in term %d\n", candidate, term)
	return true
}

func main() {
	// Clean up any previous run so the demonstration starts fresh.
	os.RemoveAll("data")

	s := NewServer()

	// Server 3 grants its vote to candidate A in term 2 and fsyncs first.
	s.RequestVote(2, "A")

	// The process crashes. Memory is lost, but the disk file remains.
	fmt.Println("CRASH")
	fmt.Println("RESTART, loading persisted state")
	s = NewServer()
	if err := s.load(); err != nil {
		fmt.Printf("load failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("loaded state: term=%d votedFor=%s\n", s.state.CurrentTerm, s.state.VotedFor)

	// After restart, server 3 remembers its vote and refuses to vote again.
	if s.RequestVote(2, "B") {
		fmt.Println("SAFETY VIOLATION: voted twice in term 2")
		os.Exit(1)
	}
	fmt.Printf("refused vote to B in term %d (already voted for %s)\n", s.state.CurrentTerm, s.state.VotedFor)
}
