package main

import "unicode/utf8"

type Token struct {
	Kind, Text string
	Line, Col  int
}

type Lexer struct {
	Source         string
	pos, line, col int
}

var keywords = map[string]bool{
	"func": true, "var": true, "if": true, "else": true, "return": true,
}

func NewLexer(source string) *Lexer {
	return &Lexer{Source: source, line: 1, col: 1}
}
func letter(c byte) bool {
	return c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c == '_'
}
func digit(c byte) bool { return c >= '0' && c <= '9' }
func (l *Lexer) peek() byte {
	if l.pos == len(l.Source) {
		return 0
	}
	return l.Source[l.pos]
}
func (l *Lexer) advance() {
	r, size := utf8.DecodeRuneInString(l.Source[l.pos:])
	l.pos += size
	if r == '\n' {
		l.line++
		l.col = 1
	} else {
		l.col++
	}
}

func (l *Lexer) Next() Token {
	// Trivia is consumed before recording the next token's position.
	for l.pos < len(l.Source) {
		c := l.peek()
		if c == ' ' || c == '\t' || c == '\r' || c == '\n' {
			l.advance()
		} else if c == '/' && l.pos+1 < len(l.Source) && l.Source[l.pos+1] == '/' {
			for l.pos < len(l.Source) && l.peek() != '\n' {
				l.advance()
			}
		} else {
			break
		}
	}
	start, line, col := l.pos, l.line, l.col
	if start == len(l.Source) {
		return Token{"EOF", "", line, col}
	}
	c, kind := l.peek(), "ERROR"
	switch {
	case letter(c):
		for letter(l.peek()) || digit(l.peek()) {
			l.advance()
		}
		kind = "IDENT"
		if keywords[l.Source[start:l.pos]] {
			kind = l.Source[start:l.pos]
		}
	case digit(c):
		for digit(l.peek()) {
			l.advance()
		}
		kind = "INT"
	case c == '=' || c == '!' || c == '<' || c == '>':
		l.advance()
		if l.peek() == '=' {
			l.advance()
			kind = l.Source[start:l.pos]
		} else if c != '!' {
			kind = string(c)
		}
	case c == '+' || c == '-' || c == '*' || c == '/' || c == '(' || c == ')' || c == '{' || c == '}' || c == ',' || c == ';':
		l.advance()
		kind = string(c)
	default:
		l.advance()
	}
	return Token{kind, l.Source[start:l.pos], line, col}
}
