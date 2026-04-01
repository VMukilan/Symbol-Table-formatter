# Mini Compiler

A web-based **Mini Compiler** built with Flask that demonstrates the complete compilation process.

## Features

- **Lexical Analysis** (Tokenizer with support for int, float, identifiers, operators)
- **Syntax Analysis** (Parser supporting declarations, assignments, blocks `{ }`, and `if-else` statements)
- **Semantic Analysis** with **Scope Handling** (Global and Local variables)
- **Intermediate Code Generation** (Three-Address Code - TAC)
- **Binary Tree Visualization** for Parse Tree and Annotated Tree
- **Full Post-Order Traversal** of the entire AST
- **Symbol Table** with scope information (Global / Local)
- **Export Symbol Table** as JSON and CSV
- Clean and responsive web interface

### Supported Language Features (MiniLang)
- Variable declarations: `int x = 10;`, `float y = 2.5;`
- Assignments: `x = x + 5;`
- Block scoping using `{ }`
- `if-else` statements with comparison operators (`>`, `<`, `==`)
- Basic arithmetic expressions (`+`, `-`, `*`, `/`)

### Example Code

```c
int x = 10;

if (x > 5) {
    int y = 20;
    x = x + y;
} else {
    int z = 5;
    x = x - z;
}

int result = x;
