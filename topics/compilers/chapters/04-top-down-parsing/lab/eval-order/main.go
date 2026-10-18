package main

import "fmt"

func f() int { fmt.Println("f"); return 10 }
func g() int { fmt.Println("g"); return 3 }
func h() int { fmt.Println("h"); return 2 }

func main() {
    fmt.Println("== f() - g() * h() ==")
    fmt.Println("value:", f() - g() * h())
}
