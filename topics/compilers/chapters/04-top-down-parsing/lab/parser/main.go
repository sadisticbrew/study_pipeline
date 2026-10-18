package main

import (
    "fmt"
    "go/ast"
    goparser "go/parser"
)

func goTree(expr ast.Expr) *Node {
    switch e := expr.(type) {
    case *ast.BasicLit: return node(e.Value)
    case *ast.Ident: return node(e.Name)
    case *ast.BinaryExpr: return node(e.Op.String(), goTree(e.X), goTree(e.Y))
    case *ast.ParenExpr: return goTree(e.X)
    default: panic(fmt.Sprintf("unexpected Go node %T", expr))
    }
}
func main() {
    const running = "10 - 4 - 3 * 2"
    fmt.Println("== Pratt trace ==")
    ours := expression(running, true)
    fmt.Println("== Expression trees ==")
    for _, source := range []string{running, "-2 * 3", "a < b == c", "f(1, 2 + 3) * 4", "10 - (4 - 3) * 2"} {
        fmt.Printf("%s => %s\n", source, expression(source, false))
    }
    fmt.Println("== Recursive-descent choices ==")
    statement := parseProgram("if x1 <= 10 { y = x1 * 2; }", true)
    fmt.Println("tree:", statement)
    fmt.Println("== Function tree ==")
    fmt.Println(parseProgram("func max(a, b) { if a > b { return a; } else { return b; } }", false))
    fmt.Println("== Positioned syntax errors ==")
    for _, source := range []string{"x = (1 + 2;", "if x { y = ; }"} {
        fmt.Printf("%s => %s\n", source, diagnostic(source))
    }
    fmt.Println("== go/parser comparison ==")
    standard, err := goparser.ParseExpr(running)
    if err != nil { panic(err) }
    fmt.Println("ours:     ", ours)
    fmt.Println("go/parser:", goTree(standard))
}
