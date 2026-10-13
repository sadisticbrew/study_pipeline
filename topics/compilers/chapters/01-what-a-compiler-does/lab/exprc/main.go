// exprc: nonnegative int64 literals, parentheses, and binary + - * /.
// Arithmetic uses signed 64-bit machine operations; overflow is not checked.
package main

import (
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

type token struct {
	kind byte
	value int64
}

// Lexer: 'n' is a number, punctuation is its own token, and 0 is EOF.
func lex(source string) []token {
	var tokens []token
	for i := 0; i < len(source); {
		c := source[i]
		if strings.ContainsRune(" \t\r\n", rune(c)) {
			i++
			continue
		}
		if c >= '0' && c <= '9' {
			start := i
			for i < len(source) && source[i] >= '0' && source[i] <= '9' {
				i++
			}
			value, err := strconv.ParseInt(source[start:i], 10, 64)
			if err != nil {
				panic("integer literal out of range")
			}
			tokens = append(tokens, token{'n', value})
			continue
		}
		if !strings.ContainsRune("+-*/()", rune(c)) {
			panic(fmt.Sprintf("unexpected character %q", c))
		}
		tokens = append(tokens, token{kind: c})
		i++
	}
	return append(tokens, token{})
}

type node struct {
	op byte
	value int64
	left, right *node
}

type parser struct {
	tokens []token
	pos int
}

func precedence(op byte) int {
	switch op {
	case '+', '-':
		return 1
	case '*', '/':
		return 2
	}
	return 0
}

// Parser: climbing precedence makes operators left-associative.
func (p *parser) expression(min int) *node {
	t := p.tokens[p.pos]
	p.pos++
	var left *node
	switch t.kind {
	case 'n':
		left = &node{value: t.value}
	case '(':
		left = p.expression(1)
		if p.tokens[p.pos].kind != ')' {
			panic("expected closing parenthesis")
		}
		p.pos++
	default:
		panic("expected number or opening parenthesis")
	}
	for precedence(p.tokens[p.pos].kind) >= min {
		op := p.tokens[p.pos].kind
		p.pos++
		left = &node{op: op, left: left, right: p.expression(precedence(op) + 1)}
	}
	return left
}

func parse(tokens []token) *node {
	p := parser{tokens: tokens}
	tree := p.expression(1)
	if p.tokens[p.pos].kind != 0 {
		panic("unexpected trailing token")
	}
	return tree
}

// Codegen: each subtree leaves exactly one value on the machine stack.
func generate(out io.Writer, n *node) {
	if n.op == 0 {
		fmt.Fprintf(out, "  movabsq $%d, %%rax; pushq %%rax\n", n.value)
		return
	}
	generate(out, n.left)
	generate(out, n.right)
	fmt.Fprintln(out, "  popq %rcx; popq %rax")
	switch n.op {
	case '+':
		fmt.Fprintln(out, "  addq %rcx, %rax; pushq %rax")
	case '-':
		fmt.Fprintln(out, "  subq %rcx, %rax; pushq %rax")
	case '*':
		fmt.Fprintln(out, "  imulq %rcx, %rax; pushq %rax")
	case '/':
		fmt.Fprintln(out, "  cqto; idivq %rcx; pushq %rax")
	}
}

func main() {
	defer func() {
		if err := recover(); err != nil {
			fmt.Fprintln(os.Stderr, "exprc:", err)
			os.Exit(1)
		}
	}()
	if len(os.Args) != 2 {
		panic("usage: exprc 'EXPRESSION' > program.s")
	}
	tree := parse(lex(os.Args[1]))
	var assembly strings.Builder
	fmt.Fprintln(&assembly, ".text\n.globl compute\ncompute:")
	generate(&assembly, tree)
	fmt.Fprintln(&assembly, "  popq %rax\n  ret\n.section .note.GNU-stack,\"\",@progbits")
	if _, err := io.WriteString(os.Stdout, assembly.String()); err != nil {
		panic(err)
	}
}
