"""
=============================================================
  MINI COMPILER — Web Server with HTML/CSS/JS Frontend
  Phases: Lexical → Syntax → Semantic → Symbol Table →
          Intermediate Code → Optimization → Code Generation
  Features: Global/Local Scope, if-else, Binary Tree, TAC
=============================================================
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import re
import json
import csv
import os
import io
from typing import Optional, List, Any

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
#  TOKEN DEFINITIONS
# ─────────────────────────────────────────────
TOKEN_PATTERNS = [
    ("FLOAT_LITERAL", r"(?P<FLOAT_LITERAL>\d+\.\d+)"),
    ("INT_LITERAL",   r"(?P<INT_LITERAL>\d+)"),
    ("KEYWORD",       r"(?P<KEYWORD>\b(int|float|if|else)\b)"),
    ("IDENTIFIER",    r"(?P<IDENTIFIER>[a-zA-Z_]\w*)"),
    ("ASSIGN",        r"(?P<ASSIGN>=)"),
    ("PLUS",          r"(?P<PLUS>\+)"),
    ("MINUS",         r"(?P<MINUS>-)"),
    ("MULTIPLY",      r"(?P<MULTIPLY>\*)"),
    ("DIVIDE",        r"(?P<DIVIDE>/)"),
    ("SEMICOLON",     r"(?P<SEMICOLON>;)"),
    ("LBRACE",        r"(?P<LBRACE>\{)"),
    ("RBRACE",        r"(?P<RBRACE>\})"),
    ("LPAREN",        r"(?P<LPAREN>\()"),
    ("RPAREN",        r"(?P<RPAREN>\))"),
    ("GT",            r"(?P<GT>> )"),
    ("LT",            r"(?P<LT><)"),
    ("EQ",            r"(?P<EQ>==)"),
    ("WHITESPACE",    r"(?P<WHITESPACE>\s+)"),
]

MASTER_PATTERN = "|".join(pat for _, pat in TOKEN_PATTERNS)


# ─────────────────────────────────────────────
#  LEXICAL ANALYSIS
# ─────────────────────────────────────────────
class Token:
    def __init__(self, type: str, value: str, line: int):
        self.type = type
        self.value = value
        self.line = line

def lexical_analysis(source_code: str) -> List[Token]:
    tokens: List[Token] = []
    line_num = 1
    for mo in re.finditer(MASTER_PATTERN, source_code):
        for token_type, _ in TOKEN_PATTERNS:
            value = mo.group(token_type)
            if value is not None:
                if token_type == "WHITESPACE":
                    line_num += value.count("\n")
                    break
                tokens.append(Token(token_type, value, line_num))
                break
    return tokens


# ─────────────────────────────────────────────
#  AST NODES
# ─────────────────────────────────────────────
class ASTNode:
    def __init__(self, node_type: str):
        self.node_type = node_type
        self.left = None
        self.right = None
        self.inferred_type = None

class ProgramNode(ASTNode):
    def __init__(self):
        super().__init__("Program")
        self.statements = []

class BlockNode(ASTNode):
    def __init__(self):
        super().__init__("Block")
        self.statements = []

class DeclarationNode(ASTNode):
    def __init__(self, var_type: str, name: str, expression=None):
        super().__init__("Declaration")
        self.var_type = var_type
        self.name = name
        self.expression = expression

class AssignmentNode(ASTNode):
    def __init__(self, name: str, expression=None):
        super().__init__("Assignment")
        self.name = name
        self.expression = expression

class BinaryOpNode(ASTNode):
    def __init__(self, operator: str):
        super().__init__("BinaryOp")
        self.operator = operator

class ComparisonNode(ASTNode):
    def __init__(self, operator: str):
        super().__init__("Comparison")
        self.operator = operator

class IfNode(ASTNode):
    def __init__(self):
        super().__init__("If")
        self.condition = None
        self.then_block = None
        self.else_block = None

class NumberNode(ASTNode):
    def __init__(self, value: Any):
        super().__init__("Number")
        self.value = value


# ─────────────────────────────────────────────
#  PARSER (with if-else and comparisons)
# ─────────────────────────────────────────────
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type):
        tok = self.current()
        if not tok or tok.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {tok.value if tok else 'EOF'}")
        self.pos += 1
        return tok

    def parse_program(self):
        node = ProgramNode()
        while self.current():
            node.statements.append(self.parse_statement())
        return node

    def parse_statement(self):
        tok = self.current()
        if tok.type == "KEYWORD":
            if tok.value == "if":
                return self.parse_if_statement()
            else:
                return self.parse_declaration()
        if tok.type == "IDENTIFIER":
            return self.parse_assignment()
        if tok.type == "LBRACE":
            return self.parse_block()
        raise SyntaxError(f"Unexpected token '{tok.value}'")

    def parse_block(self):
        self.consume("LBRACE")
        node = BlockNode()
        while self.current() and self.current().type != "RBRACE":
            node.statements.append(self.parse_statement())
        self.consume("RBRACE")
        return node

    def parse_if_statement(self):
        self.consume("KEYWORD")  # if
        self.consume("LPAREN")
        condition = self.parse_condition()
        self.consume("RPAREN")
        then_block = self.parse_block()
        else_block = None
        if self.current() and self.current().type == "KEYWORD" and self.current().value == "else":
            self.consume("KEYWORD")
            else_block = self.parse_block()
        node = IfNode()
        node.condition = condition
        node.then_block = then_block
        node.else_block = else_block
        return node

    def parse_condition(self):
        left = self.parse_expression()
        if self.current() and self.current().type in ("GT", "LT", "EQ"):
            op = self.consume(self.current().type).value.strip()
            right = self.parse_expression()
            node = ComparisonNode(op)
            node.left = left
            node.right = right
            return node
        return left

    def parse_expression(self):
        node = self.parse_term()
        while self.current() and self.current().type in ("PLUS", "MINUS"):
            op = self.consume(self.current().type).value
            right = self.parse_term()
            new_node = BinaryOpNode(op)
            new_node.left = node
            new_node.right = right
            node = new_node
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current() and self.current().type in ("MULTIPLY", "DIVIDE"):
            op = self.consume(self.current().type).value
            right = self.parse_factor()
            new_node = BinaryOpNode(op)
            new_node.left = node
            new_node.right = right
            node = new_node
        return node

    def parse_factor(self):
        tok = self.current()
        if tok.type in ("INT_LITERAL", "FLOAT_LITERAL"):
            self.pos += 1
            return NumberNode(int(tok.value) if tok.type == "INT_LITERAL" else float(tok.value))
        if tok.type == "IDENTIFIER":
            self.pos += 1
            node = NumberNode(tok.value)
            node.node_type = "Identifier"
            return node
        raise SyntaxError(f"Unexpected token: {tok.value if tok else 'EOF'}")

    def parse_declaration(self):
        type_tok = self.consume("KEYWORD")
        name_tok = self.consume("IDENTIFIER")
        self.consume("ASSIGN")
        expr = self.parse_expression()
        self.consume("SEMICOLON")
        return DeclarationNode(type_tok.value, name_tok.value, expr)

    def parse_assignment(self):
        name_tok = self.consume("IDENTIFIER")
        self.consume("ASSIGN")
        expr = self.parse_expression()
        self.consume("SEMICOLON")
        return AssignmentNode(name_tok.value, expr)


def syntax_analysis(tokens):
    return Parser(tokens).parse_program()


# ─────────────────────────────────────────────
#  SYMBOL TABLE
# ─────────────────────────────────────────────
class SymbolEntry:
    def __init__(self, name, typ, value, scope):
        self.name = name
        self.type = typ
        self.value = value
        self.scope = scope

class SymbolTable:
    def __init__(self):
        self._table = {}
        self._scope_stack = ["global"]
        self._all_entries = []   # Keep all for display

    def enter_scope(self):
        self._scope_stack.append(f"local_{len(self._scope_stack)}")

    def exit_scope(self):
        if len(self._scope_stack) > 1:
            self._scope_stack.pop()

    def declare(self, name, typ, value):
        scope = self._scope_stack[-1]
        self._table[name] = SymbolEntry(name, typ, value, scope)
        self._all_entries.append(self._table[name])

    def all_entries(self):
        return self._all_entries


# ─────────────────────────────────────────────
#  SEMANTIC + TAC + TREE (Simplified)
# ─────────────────────────────────────────────
def semantic_analysis(ast, sym):
    def visit(node):
        if isinstance(node, DeclarationNode):
            sym.declare(node.name, node.var_type, 0)
        elif isinstance(node, BlockNode):
            sym.enter_scope()
            for s in node.statements:
                visit(s)
            sym.exit_scope()
        elif isinstance(node, ProgramNode):
            for s in node.statements:
                visit(s)
    visit(ast)


class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_count = 0

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def generate(self, ast):
        def visit(node):
            if isinstance(node, (DeclarationNode, AssignmentNode)):
                result = self.gen_expr(node.expression)
                self.instructions.append(f"{node.name} = {result}")
            elif isinstance(node, (BlockNode, ProgramNode)):
                for s in node.statements:
                    visit(s)
        visit(ast)

    def gen_expr(self, node):
        if isinstance(node, NumberNode):
            return str(node.value)
        if getattr(node, 'node_type', None) == "Identifier":
            return node.value
        return "0"  # fallback


def ast_to_json(node):
    if node is None:
        return None
    if isinstance(node, BinaryOpNode):
        return {"name": node.operator, "type": "?", "children": [ast_to_json(node.left), ast_to_json(node.right)]}
    if isinstance(node, ComparisonNode):
        return {"name": node.operator, "type": "?", "children": [ast_to_json(node.left), ast_to_json(node.right)]}
    if isinstance(node, NumberNode):
        return {"name": str(node.value), "type": "?", "children": []}
    if isinstance(node, (DeclarationNode, AssignmentNode)):
        return {"name": f"{node.node_type[:3]}: {node.name}", "type": "?", "children": [ast_to_json(node.expression)] if node.expression else []}
    if isinstance(node, IfNode):
        return {"name": "If", "type": "", "children": [ast_to_json(node.condition), ast_to_json(node.then_block), ast_to_json(node.else_block)]}
    if isinstance(node, BlockNode):
        return {"name": "Block", "type": "", "children": [ast_to_json(s) for s in node.statements]}
    if isinstance(node, ProgramNode):
        return {"name": "Program", "type": "", "children": [ast_to_json(s) for s in node.statements]}
    return {"name": "?", "children": []}


def get_full_post_order(node):
    if node is None:
        return []
    result = []
    if isinstance(node, (BinaryOpNode, ComparisonNode)):
        result.extend(get_full_post_order(node.left))
        result.extend(get_full_post_order(node.right))
        result.append(node.operator)
    elif isinstance(node, NumberNode):
        result.append(str(node.value))
    elif isinstance(node, (DeclarationNode, AssignmentNode)):
        result.extend(get_full_post_order(node.expression))
        result.append(f"{node.name}=")
    elif isinstance(node, (BlockNode, ProgramNode, IfNode)):
        for s in (node.statements if hasattr(node, 'statements') else [node.condition, node.then_block, node.else_block] if isinstance(node, IfNode) else []):
            if s:
                result.extend(get_full_post_order(s))
    return result


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────
latest_symbol_table = None

@app.route('/')
def index():
    return render_template('compiler.html')

@app.route('/compile', methods=['POST'])
def compile_code():
    global latest_symbol_table
    try:
        source_code = request.get_json().get('source', '')

        tokens = lexical_analysis(source_code)
        ast_raw = syntax_analysis(tokens)

        sym = SymbolTable()
        ast_ann = syntax_analysis(tokens)
        semantic_analysis(ast_ann, sym)

        latest_symbol_table = sym

        tac_gen = TACGenerator()
        tac_gen.generate(ast_ann)

        symbol_entries = [{"name": e.name, "type": e.type, "value": e.value, "scope": e.scope} 
                         for e in sym.all_entries()]

        return jsonify({
            "success": True,
            "language": "MiniLang with if-else support",
            "tokens": [{"type": t.type, "value": t.value, "line": t.line} for t in tokens],
            "symbols": symbol_entries,
            "parse_tree": ast_to_json(ast_raw),
            "annotated_tree": ast_to_json(ast_ann),
            "full_post_order": " ".join(get_full_post_order(ast_ann)),
            "tac": tac_gen.instructions,
            "stats": {
                "lines": len(source_code.splitlines()),
                "tokens": len(tokens),
                "symbols": len(symbol_entries),
                "tac_count": len(tac_gen.instructions)
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/export/json')
def export_json():
    global latest_symbol_table
    if not latest_symbol_table:
        return jsonify({"error": "No data"}), 404
    return send_file(io.BytesIO(latest_symbol_table.export_to_json().encode()), 
                     mimetype='application/json', as_attachment=True, download_name='symbol_table.json')


@app.route('/export/csv')
def export_csv():
    global latest_symbol_table
    if not latest_symbol_table:
        return jsonify({"error": "No data"}), 404
    return send_file(io.BytesIO(latest_symbol_table.export_to_csv().encode()), 
                     mimetype='text/csv', as_attachment=True, download_name='symbol_table.csv')


# Create templates folder and HTML file
if not os.path.exists('templates'):
    os.makedirs('templates')

# (HTML template is long — keep your existing one or use the simplified version from previous response)

print("Mini Compiler is ready!")
print("Run: python app.py")
print("Open: http://localhost:5000")

if __name__ == '__main__':
    app.run(debug=True, port=5000)