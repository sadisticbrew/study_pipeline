package main

import (
	"fmt"
	"go/scanner"
	"go/token"
)

func main() {
	const source = "x := 1\nx++\nf(x)\n"
	files := token.NewFileSet()
	file := files.AddFile("snippet.go", -1, len(source))
	var lexer scanner.Scanner
	lexer.Init(file, []byte(source), nil, 0)
	fmt.Printf("source=%q\n", source)
	for {
		pos, kind, literal := lexer.Scan()
		p := files.Position(pos)
		fmt.Printf("%d:%d %-5s %q\n", p.Line, p.Column, kind, literal)
		if kind == token.EOF { break }
	}
}
