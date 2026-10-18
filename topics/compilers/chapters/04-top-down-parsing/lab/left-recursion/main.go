package main

import (
    "fmt"
    "os"
    "strconv"
    "strings"
)

var tokens = strings.Fields("10 - 4 - 3 * 2")
var pos int

type Node struct { text string; left, right *Node }

// The first recursive call has consumed no token.
func naiveExpr() *Node {
    left := naiveExpr()
    if take("-") { return &Node{"-", left, parseTerm()} }
    return parseTerm()
}
func parseExpr() *Node {
    left := parseTerm()
    for take("-") { left = &Node{"-", left, parseTerm()} }
    return left
}
func parseTerm() *Node {
    left := parseFactor()
    for take("*") { left = &Node{"*", left, parseFactor()} }
    return left
}

func take(token string) bool {
    if pos < len(tokens) && tokens[pos] == token { pos++; return true }
    return false
}
func parseFactor() *Node {
    if take("(") {
        tree := parseExpr()
        if !take(")") { panic("expected )") }
        return tree
    }
    if pos == len(tokens) { panic("expected number") }
    text := tokens[pos]; pos++
    if _, err := strconv.Atoi(text); err != nil { panic("expected number") }
    return &Node{text: text}
}
func (n *Node) String() string {
    if n.left == nil { return n.text }
    return fmt.Sprintf("(%s %s %s)", n.left, n.text, n.right)
}
func (n *Node) value() int {
    if n.left == nil { v, _ := strconv.Atoi(n.text); return v }
    if n.text == "-" { return n.left.value() - n.right.value() }
    return n.left.value() * n.right.value()
}
func main() {
    if len(os.Args) > 1 && os.Args[1] == "naive" { fmt.Println(naiveExpr()); return }
    tree := parseExpr()
    if pos != len(tokens) { panic("unconsumed token") }
    fmt.Printf("tree: %s\nvalue: %d\n", tree, tree.value())
}
