package main

import "fmt"

func stream(source string) string {
	lexer := NewLexer(source)
	result := ""
	for {
		t := lexer.Next()
		if result != "" { result += " | " }
		result += fmt.Sprintf("%s(%q)@%d:%d", t.Kind, t.Text, t.Line, t.Col)
		if t.Kind == "EOF" { return result }
	}
}

func main() {
	fmt.Println("== Opening line ==")
	lexer := NewLexer("if x1 <= 10 { y = x1 * 2 } // done")
	for {
		t := lexer.Next()
		fmt.Printf("%d:%-2d %-5s %q\n", t.Line, t.Col, t.Kind, t.Text)
		if t.Kind == "EOF" { break }
	}
	fmt.Println("\n== Longest match, priority, trivia and errors ==")
	for _, source := range []string{"a<=b", "a< =b", "iffy if", "x==y=z", "10/2//c", "x @ y"} {
		fmt.Printf("%q: %s\n", source, stream(source))
	}
	fmt.Println("\n== Remaining token kinds and multiline positions ==")
	fmt.Println(stream("func var else return + - != > >= ( ) , ;"))
	fmt.Println(stream("x // comment\n  y"))
	fmt.Println(stream("! é\x00"))
}
