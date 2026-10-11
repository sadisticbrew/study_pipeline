package main

import (
	"fmt"
	"os"
)

// Server keeps Raft vote state only in memory.
// This is the buggy version: a crash erases everything.
type Server struct {
	currentTerm int
	votedFor    string
}

func NewServer() *Server {
	return &Server{}
}

// RequestVote handles a vote request. It returns true if the vote is granted.
func (s *Server) RequestVote(term int, candidate string) bool {
	fmt.Printf("term %d: received RequestVote from %s\n", term, candidate)
	if term > s.currentTerm {
		s.currentTerm = term
		s.votedFor = ""
	}
	if term < s.currentTerm {
		return false
	}
	if s.votedFor != "" && s.votedFor != candidate {
		return false
	}
	s.votedFor = candidate
	fmt.Printf("granted vote to %s in term %d\n", candidate, term)
	return true
}

func main() {
	s := NewServer()

	// Server 3 grants its vote to candidate A in term 2.
	s.RequestVote(2, "A")

	// The process crashes. All memory is lost.
	fmt.Println("CRASH")
	fmt.Println("RESTART with empty memory")
	s = NewServer()

	// After restart, server 3 has no record of its earlier vote.
	// It grants a second vote in the same term, breaking the one-vote rule.
	if s.RequestVote(2, "B") {
		fmt.Printf("SAFETY VIOLATION: voted for both A and B in term 2\n")
		os.Exit(1)
	}

	fmt.Println("OK: refused duplicate vote")
}
