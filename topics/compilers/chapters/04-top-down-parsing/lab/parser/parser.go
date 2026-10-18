package main

import (
    "fmt"
    "strings"
)

type Node struct { tag string; children []*Node }
func node(tag string, children ...*Node) *Node { return &Node{tag, children} }
func (n *Node) String() string {
    if len(n.children) == 0 { return n.tag }
    parts := []string{n.tag}
    for _, child := range n.children { parts = append(parts, child.String()) }
    return "(" + strings.Join(parts, " ") + ")"
}
type syntaxError struct { message string }
type Parser struct {
    lexer *Lexer
    token Token
    trace, decisions bool
    calls int
}
func newParser(source string) *Parser {
    p := &Parser{lexer: NewLexer(source)}
    p.next()
    return p
}
func (p *Parser) next() { p.token = p.lexer.Next() }
func (p *Parser) fail(expected string) {
    panic(syntaxError{fmt.Sprintf("%d:%d: expected %s; found %s %q", p.token.Line, p.token.Col, expected, p.token.Kind, p.token.Text)})
}
func (p *Parser) want(kind string) string {
    if p.token.Kind != kind { p.fail(kind) }
    text := p.token.Text; p.next(); return text
}
func (p *Parser) take(kind string) bool {
    if p.token.Kind != kind { return false }
    p.next(); return true
}
func (p *Parser) choice(function, production string) {
    if p.decisions { fmt.Printf("%s: lookahead %s -> %s\n", function, p.token.Kind, production) }
}

func (p *Parser) parseStmt() *Node {
    switch p.token.Kind {
    case "var":
        p.choice("parseStmt", `"var" IDENT "=" Expr ";"`)
        p.next(); name := p.want("IDENT"); p.want("=")
        value := p.parseExpr(1); p.want(";"); return node("var", node(name), value)
    case "IDENT":
        p.choice("parseStmt", `IDENT "=" Expr ";"`)
        name := p.want("IDENT"); p.want("=")
        value := p.parseExpr(1); p.want(";"); return node("=", node(name), value)
    case "if":
        p.choice("parseStmt", "IfStmt"); return p.parseIf()
    case "return":
        p.choice("parseStmt", `"return" Expr ";"`)
        p.next(); value := p.parseExpr(1); p.want(";"); return node("return", value)
    case "{":
        p.choice("parseStmt", "Block"); return p.parseBlock()
    default:
        p.fail("var, IDENT, if, return, {")
    }
    return nil
}

var bindingPower = map[string]int{
    "==": 3, "!=": 3, "<": 3, "<=": 3, ">": 3, ">=": 3,
    "+": 4, "-": 4, "*": 5, "/": 5,
}
func (p *Parser) parseExpr(min int) *Node {
    p.calls++; call := p.calls
    left := p.primary()
    p.event(call, min, left, "", 0, "operand")
    for {
        op, power := p.token.Kind, bindingPower[p.token.Kind]
        if power < min {
            p.event(call, min, nil, op, power, "return")
            return left
        }
        p.event(call, min, nil, op, power, "absorb")
        p.next()
        right := p.parseExpr(power + 1)
        left = node(op, left, right)
    }
}

func (p *Parser) event(call, min int, operand *Node, op string, power int, action string) {
    if !p.trace { return }
    if operand != nil {
        fmt.Printf("call %d min=%d: operand %s\n", call, min, operand)
    } else {
        fmt.Printf("call %d min=%d: see %s bp=%d %s\n", call, min, op, power, action)
    }
}
func (p *Parser) primary() *Node {
    switch p.token.Kind {
    case "-":
        p.next(); return node("neg", p.parseExpr(6))
    case "INT":
        text := p.token.Text; p.next(); return node(text)
    case "IDENT":
        name := p.token.Text; p.next()
        if !p.take("(") { return node(name) }
        args := []*Node{node(name)}
        if p.token.Kind != ")" {
            args = append(args, p.parseExpr(1))
            for p.take(",") { args = append(args, p.parseExpr(1)) }
        }
        p.want(")"); return node("call", args...)
    case "(":
        p.next(); value := p.parseExpr(1); p.want(")"); return value
    default:
        p.fail("INT, IDENT, (, -")
    }
    return nil
}
func (p *Parser) parseBlock() *Node {
    p.choice("parseBlock", `"{" { Stmt } "}"`); p.want("{")
    statements := []*Node{}
    for p.token.Kind != "}" {
        p.choice("parseBlock", "Stmt"); statements = append(statements, p.parseStmt())
    }
    p.choice("parseBlock", `"}"`); p.want("}")
    return node("block", statements...)
}
func (p *Parser) parseIf() *Node {
    p.want("if"); condition := p.parseExpr(1)
    branches := []*Node{condition, p.parseBlock()}
    if p.token.Kind == "else" {
        p.choice("parseIf", `"else" (Block | IfStmt)`); p.next()
        if p.token.Kind == "if" {
            p.choice("parseIf", "IfStmt"); branches = append(branches, p.parseIf())
        } else {
            p.choice("parseIf", "Block"); branches = append(branches, p.parseBlock())
        }
    } else { p.choice("parseIf", "ε") }
    return node("if", branches...)
}
func (p *Parser) parseFunc() *Node {
    p.want("func"); name := p.want("IDENT"); p.want("(")
    params := []*Node{}
    if p.token.Kind != ")" {
        params = append(params, node(p.want("IDENT")))
        for p.take(",") { params = append(params, node(p.want("IDENT"))) }
    }
    p.want(")")
    return node("func", node(name), node("params", params...), p.parseBlock())
}
func (p *Parser) program() *Node {
    items := []*Node{}
    for p.token.Kind != "EOF" {
        if p.token.Kind == "func" {
            p.choice("program", "FuncDecl"); items = append(items, p.parseFunc())
        } else {
            p.choice("program", "Stmt"); items = append(items, p.parseStmt())
        }
    }
    return node("program", items...)
}
func expression(source string, trace bool) *Node {
    p := newParser(source); p.trace = trace
    tree := p.parseExpr(1); p.want("EOF"); return tree
}
func parseProgram(source string, decisions bool) *Node {
    p := newParser(source); p.decisions = decisions; return p.program()
}
func diagnostic(source string) (message string) {
    defer func() {
        if problem := recover(); problem != nil {
            if err, ok := problem.(syntaxError); ok { message = err.message } else { panic(problem) }
        }
    }()
    parseProgram(source, false)
    return "accepted"
}
