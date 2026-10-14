package main

import (
	"fmt"
	"os"
)

func show(source string, expression bool) {
	var tree *Node
	var err error
	if expression {
		tree, err = parseExpression(source, false)
	} else {
		tree, err = parseProgram(source)
	}
	if err != nil {
		fmt.Printf("%s => %v\n", source, err)
		return
	}
	fmt.Printf("%s => %s\n", source, tree)
}
func main() {
	fmt.Println("== Pratt trace: 10 - 4 - 3 * 2 ==")
	tree, err := parseExpression("10 - 4 - 3 * 2", true)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("tree =", tree)
	fmt.Println("\n== Expression trees ==")
	for _, source := range []string{"10 - 4 - 3 * 2", "-2 * 3", "a < b == c", "f(1, 2 + 3) * 4"} {
		show(source, true)
	}
	fmt.Println("\n== Statement trees ==")
	show("if x1 <= 10 { y = x1 * 2 }", false)
	show("func choose(x, y) { if x < y { return x } else { return y } }", false)
	fmt.Println("\n== Remaining operators and statement forms ==")
	show("a != b > c >= d <= e / (f + g)", true)
	show("var x; var y = 2; x = y; f(x); { return; }", false)
	fmt.Println("\n== Positioned parse errors ==")
	show("x = (1 + 2", false)
	show("if x { y = }", false)
}
