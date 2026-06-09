#!/usr/bin/env python3
"""Compilador didactico de CuencaLang a Python.

Fases implementadas:
1) Analisis lexico
2) Analisis sintactico
3) Analisis semantico
4) Generacion de codigo Python

Uso:
  python cuencalang_compiler.py examples/oferta_demanda.clg -o oferta_demanda_generado.py
  python oferta_demanda_generado.py
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import argparse
import re
import sys

# ============================================================
# 1. ANALIZADOR LEXICO
# ============================================================
@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    col: int

KEYWORDS = {
    "programa": "PROGRAMA",
    "numero": "NUMERO_TIPO",
    "texto": "TEXTO_TIPO",
    "booleano": "BOOLEANO_TIPO",
    "imprimir": "IMPRIMIR",
    "si": "SI",
    "sino": "SINO",
    "mientras": "MIENTRAS",
    "verdadero": "VERDADERO",
    "falso": "FALSO",
    "y": "Y",
    "o": "O",
    "no": "NO",
}

TOKEN_SPEC = [
    ("COMMENT", r"//[^\n]*"),
    ("STRING", r'"(?:\\.|[^"\\])*"'),
    ("NUMBER", r"\d+(?:\.\d+)?"),
    ("ID", r"[A-Za-z_ÁÉÍÓÚáéíóúÑñ][A-Za-z0-9_ÁÉÍÓÚáéíóúÑñ]*"),
    ("OP", r"==|!=|<=|>=|[+\-*/<>=]"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("SEMI", r";"),
    ("SKIP", r"[ \t\r]+"),
    ("NEWLINE", r"\n"),
    ("MISMATCH", r"."),
]
TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))

class CompileError(Exception):
    """Error controlado de compilacion."""

class Lexer:
    def __init__(self, source: str):
        self.source = source

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        line = 1
        col = 1
        for match in TOKEN_RE.finditer(self.source):
            kind = match.lastgroup or "MISMATCH"
            value = match.group()
            if kind == "NEWLINE":
                line += 1
                col = 1
                continue
            if kind in {"SKIP", "COMMENT"}:
                col += len(value)
                continue
            if kind == "MISMATCH":
                if value == '"':
                    raise CompileError(f"Cadena de texto sin cerrar en linea {line}, columna {col}")
                raise CompileError(f"Caracter inesperado {value!r} en linea {line}, columna {col}")
            if kind == "ID" and value in KEYWORDS:
                kind = KEYWORDS[value]
            tokens.append(Token(kind, value, line, col))
            col += len(value)
        tokens.append(Token("EOF", "", line, col))
        return tokens

# ============================================================
# 2. AST + ANALIZADOR SINTACTICO
# ============================================================
@dataclass
class Program:
    name: str
    body: list

@dataclass
class VarDecl:
    var_type: str
    name: str
    expr: Optional[Any]

@dataclass
class Assign:
    name: str
    expr: Any

@dataclass
class Print:
    expr: Any

@dataclass
class If:
    condition: Any
    then_body: list
    else_body: Optional[list]

@dataclass
class While:
    condition: Any
    body: list

@dataclass
class Literal:
    value: Any
    lit_type: str

@dataclass
class Var:
    name: str

@dataclass
class Unary:
    op: str
    expr: Any

@dataclass
class Binary:
    left: Any
    op: str
    right: Any

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def lookahead(self, offset: int) -> Token:
        index = self.pos + offset
        if index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[index]

    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok

    def match(self, *types: str) -> Optional[Token]:
        if self.current().type in types:
            return self.advance()
        return None

    def expect(self, typ: str, msg: str) -> Token:
        if self.current().type == typ:
            return self.advance()
        tok = self.current()
        if typ == "SEMI":
            raise CompileError(f"{msg}; posible ';' faltante antes de {tok.type} ({tok.value!r}) en linea {tok.line}, columna {tok.col}")
        raise CompileError(f"{msg}. Encontrado {tok.type} ({tok.value!r}) en linea {tok.line}, columna {tok.col}")

    def parse(self) -> Program:
        self.expect("PROGRAMA", "Se esperaba la palabra reservada 'programa'")
        name = self.expect("ID", "Se esperaba el nombre del programa").value
        body = self.block()
        self.expect("EOF", "No debe haber tokens despues del cierre del programa")
        return Program(name, body)

    def block(self) -> list:
        self.expect("LBRACE", "Se esperaba '{'")
        stmts = []
        while self.current().type not in {"RBRACE", "EOF"}:
            stmts.append(self.statement())
        self.expect("RBRACE", "Se esperaba '}'")
        return stmts

    def statement(self) -> Any:
        tok = self.current()
        if tok.type in {"NUMERO_TIPO", "TEXTO_TIPO", "BOOLEANO_TIPO"}:
            return self.var_decl()
        if tok.type == "ID":
            if self.lookahead(1).type == "ID":
                raise CompileError(f"Tipo de variable desconocido '{tok.value}' en linea {tok.line}, columna {tok.col}. Tipos validos: numero, texto, booleano")
            return self.assignment()
        if tok.type == "IMPRIMIR":
            return self.print_stmt()
        if tok.type == "SI":
            return self.if_stmt()
        if tok.type == "MIENTRAS":
            return self.while_stmt()
        raise CompileError(f"Sentencia inesperada {tok.value!r} en linea {tok.line}, columna {tok.col}")

    def var_decl(self) -> VarDecl:
        typ_tok = self.advance()
        typ = {"NUMERO_TIPO": "numero", "TEXTO_TIPO": "texto", "BOOLEANO_TIPO": "booleano"}[typ_tok.type]
        name = self.expect("ID", "Se esperaba identificador en declaracion").value
        expr = None
        if self.current().type == "OP":
            op = self.advance()
            if op.value != "=":
                raise CompileError("En una declaracion solo se permite el operador '='")
            expr = self.expression()
        self.expect("SEMI", "Se esperaba ';' al final de la declaracion")
        return VarDecl(typ, name, expr)

    def assignment(self) -> Assign:
        name = self.advance().value
        op = self.expect("OP", "Se esperaba '=' en asignacion")
        if op.value != "=":
            raise CompileError("En una asignacion solo se permite el operador '='")
        expr = self.expression()
        self.expect("SEMI", "Se esperaba ';' al final de la asignacion")
        return Assign(name, expr)

    def print_stmt(self) -> Print:
        self.advance()
        expr = self.expression()
        self.expect("SEMI", "Se esperaba ';' despues de imprimir")
        return Print(expr)

    def if_stmt(self) -> If:
        self.advance()
        self.expect("LPAREN", "Se esperaba '(' despues de si")
        cond = self.expression()
        self.expect("RPAREN", "Se esperaba ')' despues de la condicion")
        then_body = self.block()
        else_body = self.block() if self.match("SINO") else None
        return If(cond, then_body, else_body)

    def while_stmt(self) -> While:
        self.advance()
        self.expect("LPAREN", "Se esperaba '(' despues de mientras")
        cond = self.expression()
        self.expect("RPAREN", "Se esperaba ')' despues de la condicion")
        return While(cond, self.block())

    def expression(self) -> Any:
        return self.or_expr()

    def or_expr(self) -> Any:
        expr = self.and_expr()
        while self.match("O"):
            expr = Binary(expr, "o", self.and_expr())
        return expr

    def and_expr(self) -> Any:
        expr = self.equality()
        while self.match("Y"):
            expr = Binary(expr, "y", self.equality())
        return expr

    def equality(self) -> Any:
        expr = self.comparison()
        while self.current().type == "OP" and self.current().value in {"==", "!="}:
            op = self.advance().value
            expr = Binary(expr, op, self.comparison())
        return expr

    def comparison(self) -> Any:
        expr = self.term()
        while self.current().type == "OP" and self.current().value in {"<", ">", "<=", ">="}:
            op = self.advance().value
            expr = Binary(expr, op, self.term())
        return expr

    def term(self) -> Any:
        expr = self.factor()
        while self.current().type == "OP" and self.current().value in {"+", "-"}:
            op = self.advance().value
            expr = Binary(expr, op, self.factor())
        return expr

    def factor(self) -> Any:
        expr = self.unary()
        while self.current().type == "OP" and self.current().value in {"*", "/"}:
            op = self.advance().value
            expr = Binary(expr, op, self.unary())
        return expr

    def unary(self) -> Any:
        if self.current().type == "OP" and self.current().value == "-":
            self.advance()
            return Unary("-", self.unary())
        if self.match("NO"):
            return Unary("no", self.unary())
        return self.primary()

    def primary(self) -> Any:
        tok = self.current()
        if self.match("NUMBER"):
            return Literal(float(tok.value) if "." in tok.value else int(tok.value), "numero")
        if self.match("STRING"):
            return Literal(tok.value, "texto")
        if self.match("VERDADERO"):
            return Literal(True, "booleano")
        if self.match("FALSO"):
            return Literal(False, "booleano")
        if self.match("ID"):
            return Var(tok.value)
        if self.match("LPAREN"):
            expr = self.expression()
            self.expect("RPAREN", "Se esperaba ')' para cerrar expresion")
            return expr
        raise CompileError(f"Expresion inesperada {tok.value!r} en linea {tok.line}, columna {tok.col}")

# ============================================================
# 3. ANALIZADOR SEMANTICO
# ============================================================
class SemanticAnalyzer:
    def __init__(self):
        self.symbols: Dict[str, str] = {}

    def analyze(self, program: Program) -> Dict[str, str]:
        for stmt in program.body:
            self.check_stmt(stmt)
        return self.symbols

    def check_stmt(self, stmt: Any) -> None:
        if isinstance(stmt, VarDecl):
            if stmt.name in self.symbols:
                raise CompileError(f"Variable ya declarada: {stmt.name}")
            if stmt.expr is not None:
                expr_type = self.expr_type(stmt.expr)
                if expr_type != stmt.var_type:
                    raise CompileError(f"Tipo incompatible en '{stmt.name}': se esperaba {stmt.var_type} y se obtuvo {expr_type}")
            self.symbols[stmt.name] = stmt.var_type
        elif isinstance(stmt, Assign):
            if stmt.name not in self.symbols:
                raise CompileError(f"Variable no declarada: {stmt.name}")
            expr_type = self.expr_type(stmt.expr)
            if expr_type != self.symbols[stmt.name]:
                raise CompileError(f"Asignacion incompatible en '{stmt.name}': se esperaba {self.symbols[stmt.name]} y se obtuvo {expr_type}")
        elif isinstance(stmt, Print):
            self.expr_type(stmt.expr)
        elif isinstance(stmt, If):
            if self.expr_type(stmt.condition) != "booleano":
                raise CompileError("La condicion de 'si' debe ser booleana")
            for s in stmt.then_body:
                self.check_stmt(s)
            if stmt.else_body:
                for s in stmt.else_body:
                    self.check_stmt(s)
        elif isinstance(stmt, While):
            if self.expr_type(stmt.condition) != "booleano":
                raise CompileError("La condicion de 'mientras' debe ser booleana")
            for s in stmt.body:
                self.check_stmt(s)

    def expr_type(self, expr: Any) -> str:
        if isinstance(expr, Literal):
            return expr.lit_type
        if isinstance(expr, Var):
            if expr.name not in self.symbols:
                raise CompileError(f"Variable no declarada: {expr.name}")
            return self.symbols[expr.name]
        if isinstance(expr, Unary):
            t = self.expr_type(expr.expr)
            if expr.op == "-" and t == "numero":
                return "numero"
            if expr.op == "no" and t == "booleano":
                return "booleano"
            raise CompileError(f"Operador unario '{expr.op}' no aplicable a {t}")
        if isinstance(expr, Binary):
            lt = self.expr_type(expr.left)
            rt = self.expr_type(expr.right)
            if expr.op in {"+", "-", "*", "/"}:
                if lt == rt == "numero":
                    return "numero"
                raise CompileError(f"Operador aritmetico '{expr.op}' requiere numeros")
            if expr.op in {"<", ">", "<=", ">="}:
                if lt == rt == "numero":
                    return "booleano"
                raise CompileError(f"Operador relacional '{expr.op}' requiere numeros")
            if expr.op in {"==", "!="}:
                if lt == rt:
                    return "booleano"
                raise CompileError("La igualdad/desigualdad requiere operandos del mismo tipo")
            if expr.op in {"y", "o"}:
                if lt == rt == "booleano":
                    return "booleano"
                raise CompileError(f"Operador logico '{expr.op}' requiere booleanos")
        raise CompileError("Expresion no reconocida por el analizador semantico")

# ============================================================
# 4. GENERADOR DE CODIGO
# ============================================================
class CodeGenerator:
    def __init__(self):
        self.lines: List[str] = []
        self.indent = 0

    def emit(self, line: str = "") -> None:
        self.lines.append("    " * self.indent + line)

    def generate(self, program: Program) -> str:
        self.emit(f"# Codigo Python generado desde CuencaLang: {program.name}")
        self.emit("def main():")
        self.indent += 1
        if not program.body:
            self.emit("pass")
        for stmt in program.body:
            self.gen_stmt(stmt)
        self.indent -= 1
        self.emit("")
        self.emit("if __name__ == '__main__':")
        self.indent += 1
        self.emit("main()")
        self.indent -= 1
        return "\n".join(self.lines) + "\n"

    def gen_stmt(self, stmt: Any) -> None:
        if isinstance(stmt, VarDecl):
            default = {"numero": "0", "texto": "''", "booleano": "False"}[stmt.var_type]
            value = self.gen_expr(stmt.expr) if stmt.expr else default
            self.emit(f"{stmt.name} = {value}")
        elif isinstance(stmt, Assign):
            self.emit(f"{stmt.name} = {self.gen_expr(stmt.expr)}")
        elif isinstance(stmt, Print):
            self.emit(f"print({self.gen_expr(stmt.expr)})")
        elif isinstance(stmt, If):
            self.emit(f"if {self.gen_expr(stmt.condition)}:")
            self.indent += 1
            if stmt.then_body:
                for s in stmt.then_body:
                    self.gen_stmt(s)
            else:
                self.emit("pass")
            self.indent -= 1
            if stmt.else_body is not None:
                self.emit("else:")
                self.indent += 1
                if stmt.else_body:
                    for s in stmt.else_body:
                        self.gen_stmt(s)
                else:
                    self.emit("pass")
                self.indent -= 1
        elif isinstance(stmt, While):
            self.emit(f"while {self.gen_expr(stmt.condition)}:")
            self.indent += 1
            if stmt.body:
                for s in stmt.body:
                    self.gen_stmt(s)
            else:
                self.emit("pass")
            self.indent -= 1

    def gen_expr(self, expr: Any) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "texto":
                return expr.value
            if expr.lit_type == "booleano":
                return "True" if expr.value else "False"
            return str(expr.value)
        if isinstance(expr, Var):
            return expr.name
        if isinstance(expr, Unary):
            op = "not" if expr.op == "no" else expr.op
            return f"({op} {self.gen_expr(expr.expr)})"
        if isinstance(expr, Binary):
            op = {"y": "and", "o": "or"}.get(expr.op, expr.op)
            return f"({self.gen_expr(expr.left)} {op} {self.gen_expr(expr.right)})"
        raise CompileError("No se pudo generar codigo para la expresion")

def compile_source(source: str) -> str:
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer().analyze(ast)
    return CodeGenerator().generate(ast)

def main(argv: Optional[List[str]] = None) -> int:
    argp = argparse.ArgumentParser(description="Compilador de CuencaLang a Python")
    argp.add_argument("source", help="Archivo fuente .clg")
    argp.add_argument("-o", "--output", default="salida.py", help="Archivo Python generado")
    argp.add_argument("--tokens", action="store_true", help="Muestra la lista de tokens y no genera codigo")
    args = argp.parse_args(argv)
    try:
        with open(args.source, "r", encoding="utf-8") as f:
            source = f.read()
        if args.tokens:
            for token in Lexer(source).tokenize():
                print(token)
            return 0
        code = compile_source(source)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Compilacion correcta: {args.output}")
        return 0
    except CompileError as exc:
        print(f"Error de compilacion: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
