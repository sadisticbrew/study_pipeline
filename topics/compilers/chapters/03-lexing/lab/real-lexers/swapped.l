%option noyywrap nodefault
%{
#include <stdio.h>
%}
%%
[a-z][a-z0-9]*     { printf("IDENT(%s) ", yytext); }
if                 { printf("IF(%s) ", yytext); }
[0-9]+             { printf("INT(%s) ", yytext); }
"<="               { printf("LE(%s) ", yytext); }
"<"                { printf("LT(%s) ", yytext); }
"//"[^\n]*         { /* discard line comment */ }
[ \t\r\n]+         { /* discard whitespace */ }
[{}=*/+();,>-]     { printf("PUNCT(%s) ", yytext); }
.                  { printf("ERROR(%s) ", yytext); }
%%
int main(void) { yylex(); putchar('\n'); return 0; }
