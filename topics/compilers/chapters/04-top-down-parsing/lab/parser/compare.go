package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"os"
)

func sexpr(expression ast.Expr) string {
	switch e := expression.(type) {
	case *ast.BasicLit:
		return e.Value
	case *ast.BinaryExpr:
		return "(" + e.Op.String() + " " + sexpr(e.X) + " " + sexpr(e.Y) + ")"
	default:
		panic(fmt.Sprintf("unexpected Go AST node %T", expression))
	}
}
func main() {
	fmt.Println("== go/parser.ParseExpr ==")
	tree, err := parser.ParseExpr("10 - 4 - 3 * 2")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("tree =", sexpr(tree))
}
