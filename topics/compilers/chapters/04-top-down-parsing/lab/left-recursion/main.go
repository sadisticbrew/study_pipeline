package main

import (
	"fmt"
	"os"
	"runtime/debug"
	"strconv"
	"strings"
)

type node struct {
	text  string
	value int
}
type parser struct {
	tokens []string
	pos    int
}

// Expr -> Expr - Term: the first call has consumed no token.
func (p *parser) naiveExpr() node {
	left := p.naiveExpr()
	if p.peek() == "-" {
		p.pos++
		return combine(left, "-", p.term())
	}
	return p.term()
}

// Expr -> Term ('-' Term)*: fold the terms into the left child.
func (p *parser) expr() node {
	left := p.term()
	for p.peek() == "-" {
		p.pos++
		left = combine(left, "-", p.term())
	}
	return left
}

func (p *parser) peek() string {
	if p.pos == len(p.tokens) {
		return "EOF"
	}
	return p.tokens[p.pos]
}
func (p *parser) number() node {
	text := p.peek()
	p.pos++
	value, err := strconv.Atoi(text)
	if err != nil {
		panic(err)
	}
	return node{text, value}
}
func (p *parser) term() node {
	left := p.number()
	for p.peek() == "*" {
		p.pos++
		left = combine(left, "*", p.number())
	}
	return left
}
func combine(left node, op string, right node) node {
	value := left.value - right.value
	if op == "*" {
		value = left.value * right.value
	}
	return node{"(" + left.text + " " + op + " " + right.text + ")", value}
}
func main() {
	p := parser{tokens: strings.Fields("10 - 4 - 3 * 2")}
	if len(os.Args) > 1 && os.Args[1] == "naive" {
		// Lower the limit only in this process, to keep the demonstration small.
		debug.SetMaxStack(32768)
		fmt.Println("input = 10 - 4 - 3 * 2; consumed tokens =", p.pos)
		fmt.Println("configured maximum stack = 32768 bytes")
		fmt.Println(p.naiveExpr())
	} else {
		result := p.expr()
		fmt.Println("tree =", result.text)
		fmt.Println("value =", result.value)
		fmt.Printf("consumed tokens = %d; lookahead = %s\n", p.pos, p.peek())
	}
}
