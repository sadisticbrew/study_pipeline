package main

import (
	"fmt"
	"strings"
)

type Node struct {
	Tag      string
	Children []*Node
}

func atom(text string) *Node                     { return &Node{Tag: text} }
func branch(tag string, children ...*Node) *Node { return &Node{tag, children} }
func (n *Node) String() string {
	if len(n.Children) == 0 {
		return n.Tag
	}
	parts := []string{n.Tag}
	for _, child := range n.Children {
		parts = append(parts, child.String())
	}
	return "(" + strings.Join(parts, " ") + ")"
}

type Parser struct {
	lexer *Lexer
	token Token
	err   error
	trace bool
}

func newParser(source string) *Parser {
	p := &Parser{lexer: NewLexer(source)}
	p.advance()
	return p
}
func (p *Parser) advance() { p.token = p.lexer.Next() }
func (p *Parser) fail(expected string) {
	if p.err == nil {
		p.err = fmt.Errorf("%d:%d: expected %s, got %s %q", p.token.Line, p.token.Col, expected, p.token.Kind, p.token.Text)
	}
}
func (p *Parser) take(kind string) bool {
	if p.err != nil {
		return false
	}
	if p.token.Kind != kind {
		p.fail(kind)
		return false
	}
	p.advance()
	return true
}

// Go's comparison level, additive level, multiplicative level, then calls.
var binding = map[string]int{
	"==": 10, "!=": 10, "<": 10, "<=": 10, ">": 10, ">=": 10,
	"+": 20, "-": 20, "*": 30, "/": 30, "(": 50,
}

// A left-associative operator recurses with a strictly larger minimum.
func (p *Parser) expression(min int) *Node {
	left := p.prefix()
	for p.err == nil {
		op := p.token.Kind
		power, present := binding[op]
		if !present {
			break
		}
		action := "absorb"
		if power < min {
			action = "return"
		}
		if p.trace {
			fmt.Printf("op=%s bp=%d min=%d %s\n", op, power, min, action)
		}
		if power < min {
			break
		}
		p.advance()
		if op == "(" {
			left = p.call(left)
		} else {
			left = branch(op, left, p.expression(power+1))
		}
	}
	return left
}

func (p *Parser) prefix() *Node {
	token := p.token
	switch token.Kind {
	case "INT", "IDENT":
		p.advance()
		return atom(token.Text)
	case "-":
		p.advance()
		return branch("neg", p.expression(40))
	case "(":
		p.advance()
		result := p.expression(0)
		p.take(")")
		return result
	default:
		p.fail("expression (integer, identifier, '-', or '(')")
		return nil
	}
}
func (p *Parser) call(callee *Node) *Node {
	args := []*Node{callee}
	if p.token.Kind != ")" {
		for p.err == nil {
			args = append(args, p.expression(0))
			if p.token.Kind != "," {
				break
			}
			p.advance()
		}
	}
	p.take(")")
	return branch("call", args...)
}

func (p *Parser) block() *Node {
	p.take("{")
	statements := p.statements("}")
	p.take("}")
	return branch("block", statements...)
}
func (p *Parser) statements(end string) []*Node {
	var result []*Node
	for p.err == nil && p.token.Kind != end && p.token.Kind != "EOF" {
		if p.token.Kind == ";" {
			p.advance()
			continue
		}
		statement := p.statement()
		result = append(result, statement)
		if p.err != nil {
			break
		}
		if p.token.Kind == ";" {
			p.advance()
			continue
		}
		if p.token.Kind == end || p.token.Kind == "EOF" {
			break
		}
		// Braced statements are self-delimiting; other statements need ';'.
		if statement.Tag != "if" && statement.Tag != "func" && statement.Tag != "block" {
			p.fail("';' or " + end)
		}
	}
	return result
}
func (p *Parser) statement() *Node {
	switch p.token.Kind {
	case "{":
		return p.block()
	case "func":
		return p.function()
	case "var":
		p.advance()
		name := atom(p.token.Text)
		p.take("IDENT")
		if p.token.Kind != "=" {
			return branch("var", name)
		}
		p.advance()
		return branch("var", name, p.expression(0))
	case "if":
		p.advance()
		condition := p.expression(0)
		body := p.block()
		parts := []*Node{condition, body}
		if p.token.Kind == "else" {
			p.advance()
			parts = append(parts, p.block())
		}
		return branch("if", parts...)
	case "return":
		p.advance()
		if p.token.Kind == ";" || p.token.Kind == "}" || p.token.Kind == "EOF" {
			return branch("return")
		}
		return branch("return", p.expression(0))
	default:
		left := p.expression(0)
		if p.err == nil && p.token.Kind == "=" {
			if len(left.Children) != 0 || !letter(left.Tag[0]) {
				p.fail("identifier assignment target")
				return nil
			}
			p.advance()
			return branch("=", left, p.expression(0))
		}
		return branch("expr", left)
	}
}
func (p *Parser) function() *Node {
	p.take("func")
	name := atom(p.token.Text)
	p.take("IDENT")
	p.take("(")
	var params []*Node
	if p.token.Kind != ")" {
		for p.err == nil {
			params = append(params, atom(p.token.Text))
			p.take("IDENT")
			if p.token.Kind != "," {
				break
			}
			p.advance()
		}
	}
	p.take(")")
	return branch("func", name, branch("params", params...), p.block())
}
func parseExpression(source string, trace bool) (*Node, error) {
	p := newParser(source)
	p.trace = trace
	tree := p.expression(0)
	p.take("EOF")
	return tree, p.err
}
func parseProgram(source string) (*Node, error) {
	p := newParser(source)
	tree := branch("program", p.statements("EOF")...)
	p.take("EOF")
	return tree, p.err
}
