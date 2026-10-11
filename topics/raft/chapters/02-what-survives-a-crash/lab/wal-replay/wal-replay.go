package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

const walFile = "data/wal.log"

// Entry is one write-ahead log record.
type Entry struct {
	Op    string `json:"op"`
	Key   string `json:"key"`
	Value string `json:"value"`
}

// Store is an in-memory key-value state machine rebuilt from the WAL.
type Store struct {
	data map[string]string
}

func NewStore() *Store {
	return &Store{data: make(map[string]string)}
}

func (st *Store) append(e Entry) error {
	if err := os.MkdirAll(filepath.Dir(walFile), 0750); err != nil {
		return err
	}
	f, err := os.OpenFile(walFile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0640)
	if err != nil {
		return err
	}
	defer f.Close()

	b, err := json.Marshal(e)
	if err != nil {
		return err
	}
	if _, err := f.Write(append(b, '\n')); err != nil {
		return err
	}
	if err := f.Sync(); err != nil { // fsync the WAL before applying
		return err
	}
	fmt.Printf("WAL entry: %s\n", string(b))
	return nil
}

// apply updates the state machine. Set is idempotent.
func (st *Store) apply(e Entry) {
	if e.Op == "set" {
		st.data[e.Key] = e.Value
		fmt.Printf("applied: %s -> %s\n", e.Key, e.Value)
	}
}

func (st *Store) snapshot() map[string]string {
	out := make(map[string]string, len(st.data))
	for k, v := range st.data {
		out[k] = v
	}
	return out
}

func (st *Store) replay() error {
	f, err := os.Open(walFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	defer f.Close()

	fmt.Println("replaying WAL")
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		var e Entry
		if err := json.Unmarshal(sc.Bytes(), &e); err != nil {
			return err
		}
		fmt.Printf("replay: %s %s %s\n", e.Op, e.Key, e.Value)
		st.apply(e)
	}
	return sc.Err()
}

func main() {
	// Clean up any previous run so the demonstration starts fresh.
	os.RemoveAll("data")

	store := NewStore()

	// Append a command to the WAL, fsync, then apply it to the state machine.
	cmd := Entry{Op: "set", Key: "web-1", Value: "10.0.0.7"}
	if err := store.append(cmd); err != nil {
		fmt.Printf("append failed: %v\n", err)
		os.Exit(1)
	}
	store.apply(cmd)
	fmt.Printf("state before crash: %v\n", store.snapshot())

	// The process crashes. The in-memory map is gone, but the WAL file survives.
	fmt.Println("CRASH (lost in-memory map)")
	fmt.Println("RESTART")

	store = NewStore()
	if err := store.replay(); err != nil {
		fmt.Printf("replay failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("state after replay: %v\n", store.snapshot())
}
