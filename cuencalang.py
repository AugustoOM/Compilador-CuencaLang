#!/usr/bin/env python3
"""
CuencaLang Compiler + CuencaVM
Trabajo Practico Integrador - Teoria de la Computacion

Este archivo implementa un compilador propio para CuencaLang.
El compilador NO genera Python como lenguaje destino. Genera bytecode propio
(.cbc) y lo ejecuta con una maquina virtual propia basada en pila.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple


# =============================
# Errores y tokens
# =============================

class CompileError(Exception):
    pass


@dataclass(frozen=True)
class Token:
    type: str
    value: Any
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.type}({self.value!r})@{self.line}:{self.column}"


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
    ("LE", r"<="),
    ("GE", r">="),
    ("EQEQ", r"=="),
    ("NE", r"!="),
    ("ASSIGN", r"="),
    ("LT", r"<"),
    ("GT", r">"),
    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("STAR", r"\*"),
    ("SLASH", r"/"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("SEMI", r";"),
    ("ID", r"[A-Za-z_ÁÉÍÓÚáéíóúÑñ][A-Za-z0-9_ÁÉÍÓÚáéíóúÑñ]*"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
]
MASTER_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


class Lexer:
    def __init__(self, source: str):
        self.source = source

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        pos = 0
        line = 1
        col = 1
        n = len(self.source)

        while pos < n:
            match = MASTER_RE.match(self.source, pos)
            if not match:
                if self.source[pos] == '"':
                    raise CompileError(f"Error lexico en linea {line}, columna {col}: cadena de texto sin cerrar")
                fragment = self.source[pos:pos+20].split("\n")[0]
                raise CompileError(f"Error lexico en linea {line}, columna {col}: simbolo inesperado cerca de {fragment!r}")

            kind = match.lastgroup or ""
            raw = match.group(kind)
            start_col = col
            pos = match.end()

            if kind == "NEWLINE":
                line += 1
                col = 1
                continue
            if kind in {"SKIP", "COMMENT"}:
                col += len(raw)
                continue
            if kind == "ID" and raw in KEYWORDS:
                kind = KEYWORDS[raw]
                value: Any = raw
            elif kind == "NUMBER":
                value = float(raw) if "." in raw else int(raw)
            elif kind == "STRING":
                try:
                    value = bytes(raw[1:-1], "utf-8").decode("unicode_escape")
                except UnicodeDecodeError as exc:
                    raise CompileError(f"Cadena invalida en linea {line}, columna {start_col}: {exc}")
            else:
                value = raw

            tokens.append(Token(kind, value, line, start_col))
            col += len(raw)

        tokens.append(Token("EOF", "", line, col))
        return tokens


# =============================
# AST
# =============================

class Node:
    pass

@dataclass
class Program(Node):
    name: str
    body: List[Node]

@dataclass
class VarDecl(Node):
    var_type: str
    name: str
    expr: Optional[Node]

@dataclass
class Assign(Node):
    name: str
    expr: Node

@dataclass
class Print(Node):
    expr: Node

@dataclass
class If(Node):
    condition: Node
    then_body: List[Node]
    else_body: List[Node]

@dataclass
class While(Node):
    condition: Node
    body: List[Node]

@dataclass
class Literal(Node):
    value: Any
    type_name: str

@dataclass
class Variable(Node):
    name: str

@dataclass
class Unary(Node):
    op: str
    expr: Node

@dataclass
class Binary(Node):
    left: Node
    op: str
    right: Node


class Parser:
    def __init__(self, tokens: Sequence[Token]):
        self.tokens = list(tokens)
        self.current = 0

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def is_at_end(self) -> bool:
        return self.peek().type == "EOF"

    def check(self, *types: str) -> bool:
        return self.peek().type in types

    def lookahead(self, offset: int) -> Token:
        index = self.current + offset
        if index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[index]

    def match(self, *types: str) -> bool:
        if self.check(*types):
            self.current += 1
            return True
        return False

    def expect(self, type_: str, message: str) -> Token:
        if self.check(type_):
            self.current += 1
            return self.previous()
        tok = self.peek()
        if type_ == "SEMI":
            raise CompileError(f"Error sintactico en linea {tok.line}, columna {tok.column}: {message}; posible ';' faltante antes de {tok.type}({tok.value!r})")
        raise CompileError(f"Error sintactico en linea {tok.line}, columna {tok.column}: {message}. Se encontro {tok.type}({tok.value!r})")

    def parse(self) -> Program:
        self.expect("PROGRAMA", "se esperaba la palabra reservada 'programa'")
        name = self.expect("ID", "se esperaba el nombre del programa").value
        body = self.block()
        self.expect("EOF", "no debe haber tokens despues del cierre del programa")
        return Program(name, body)

    def block(self) -> List[Node]:
        self.expect("LBRACE", "se esperaba '{' para abrir el bloque")
        body: List[Node] = []
        while not self.check("RBRACE") and not self.is_at_end():
            body.append(self.statement())
        self.expect("RBRACE", "se esperaba '}' para cerrar el bloque")
        return body

    def statement(self) -> Node:
        if self.match("NUMERO_TIPO", "TEXTO_TIPO", "BOOLEANO_TIPO"):
            return self.var_decl(self.previous())
        if self.match("IMPRIMIR"):
            expr = self.expression()
            self.expect("SEMI", "se esperaba ';' despues de imprimir")
            return Print(expr)
        if self.match("SI"):
            return self.if_stmt()
        if self.match("MIENTRAS"):
            return self.while_stmt()
        if self.check("ID"):
            if self.lookahead(1).type == "ID":
                tok = self.peek()
                raise CompileError(f"Error semantico en linea {tok.line}, columna {tok.column}: tipo de variable desconocido '{tok.value}'. Tipos validos: numero, texto, booleano")
            name = self.expect("ID", "se esperaba identificador").value
            self.expect("ASSIGN", "se esperaba '=' en la asignacion")
            expr = self.expression()
            self.expect("SEMI", "se esperaba ';' despues de la asignacion")
            return Assign(name, expr)
        tok = self.peek()
        raise CompileError(f"Error sintactico en linea {tok.line}, columna {tok.column}: sentencia no reconocida")

    def var_decl(self, type_token: Token) -> VarDecl:
        type_map = {"NUMERO_TIPO": "numero", "TEXTO_TIPO": "texto", "BOOLEANO_TIPO": "booleano"}
        var_type = type_map[type_token.type]
        name = self.expect("ID", "se esperaba el nombre de la variable").value
        expr: Optional[Node] = None
        if self.match("ASSIGN"):
            expr = self.expression()
        self.expect("SEMI", "se esperaba ';' despues de la declaracion")
        return VarDecl(var_type, name, expr)

    def if_stmt(self) -> If:
        self.expect("LPAREN", "se esperaba '(' despues de 'si'")
        condition = self.expression()
        self.expect("RPAREN", "se esperaba ')' despues de la condicion")
        then_body = self.block()
        else_body: List[Node] = []
        if self.match("SINO"):
            else_body = self.block()
        return If(condition, then_body, else_body)

    def while_stmt(self) -> While:
        self.expect("LPAREN", "se esperaba '(' despues de 'mientras'")
        condition = self.expression()
        self.expect("RPAREN", "se esperaba ')' despues de la condicion")
        body = self.block()
        return While(condition, body)

    # Precedencia de expresiones
    def expression(self) -> Node:
        return self.or_expr()

    def or_expr(self) -> Node:
        node = self.and_expr()
        while self.match("O"):
            node = Binary(node, "o", self.and_expr())
        return node

    def and_expr(self) -> Node:
        node = self.equality()
        while self.match("Y"):
            node = Binary(node, "y", self.equality())
        return node

    def equality(self) -> Node:
        node = self.comparison()
        while self.match("EQEQ", "NE"):
            op = "==" if self.previous().type == "EQEQ" else "!="
            node = Binary(node, op, self.comparison())
        return node

    def comparison(self) -> Node:
        node = self.term()
        while self.match("LT", "GT", "LE", "GE"):
            op_map = {"LT": "<", "GT": ">", "LE": "<=", "GE": ">="}
            node = Binary(node, op_map[self.previous().type], self.term())
        return node

    def term(self) -> Node:
        node = self.factor()
        while self.match("PLUS", "MINUS"):
            op = "+" if self.previous().type == "PLUS" else "-"
            node = Binary(node, op, self.factor())
        return node

    def factor(self) -> Node:
        node = self.unary()
        while self.match("STAR", "SLASH"):
            op = "*" if self.previous().type == "STAR" else "/"
            node = Binary(node, op, self.unary())
        return node

    def unary(self) -> Node:
        if self.match("MINUS"):
            return Unary("-", self.unary())
        if self.match("NO"):
            return Unary("no", self.unary())
        return self.primary()

    def primary(self) -> Node:
        if self.match("NUMBER"):
            return Literal(self.previous().value, "numero")
        if self.match("STRING"):
            return Literal(self.previous().value, "texto")
        if self.match("VERDADERO"):
            return Literal(True, "booleano")
        if self.match("FALSO"):
            return Literal(False, "booleano")
        if self.match("ID"):
            return Variable(self.previous().value)
        if self.match("LPAREN"):
            expr = self.expression()
            self.expect("RPAREN", "se esperaba ')' despues de la expresion")
            return expr
        tok = self.peek()
        raise CompileError(f"Error sintactico en linea {tok.line}, columna {tok.column}: se esperaba una expresion")


# =============================
# Analisis semantico
# =============================

class SemanticAnalyzer:
    def __init__(self):
        self.symbols: Dict[str, str] = {}

    def analyze(self, program: Program) -> Dict[str, str]:
        self.check_block(program.body)
        return dict(self.symbols)

    def check_block(self, body: List[Node]) -> None:
        # Alcance global simple para mantener el proyecto didactico y defendible.
        for stmt in body:
            self.check_stmt(stmt)

    def check_stmt(self, stmt: Node) -> None:
        if isinstance(stmt, VarDecl):
            if stmt.name in self.symbols:
                raise CompileError(f"Error semantico: variable redeclarada: {stmt.name}")
            self.symbols[stmt.name] = stmt.var_type
            if stmt.expr is not None:
                got = self.expr_type(stmt.expr)
                if got != stmt.var_type:
                    raise CompileError(f"Error semantico: declaracion incompatible en '{stmt.name}': se esperaba {stmt.var_type} y se obtuvo {got}")
        elif isinstance(stmt, Assign):
            if stmt.name not in self.symbols:
                raise CompileError(f"Error semantico: variable no declarada: {stmt.name}")
            got = self.expr_type(stmt.expr)
            expected = self.symbols[stmt.name]
            if got != expected:
                raise CompileError(f"Error semantico: asignacion incompatible en '{stmt.name}': se esperaba {expected} y se obtuvo {got}")
        elif isinstance(stmt, Print):
            self.expr_type(stmt.expr)
        elif isinstance(stmt, If):
            cond = self.expr_type(stmt.condition)
            if cond != "booleano":
                raise CompileError("Error semantico: la condicion de 'si' debe ser booleana")
            self.check_block(stmt.then_body)
            self.check_block(stmt.else_body)
        elif isinstance(stmt, While):
            cond = self.expr_type(stmt.condition)
            if cond != "booleano":
                raise CompileError("Error semantico: la condicion de 'mientras' debe ser booleana")
            self.check_block(stmt.body)
        else:
            raise CompileError(f"Error interno: nodo no soportado {type(stmt).__name__}")

    def expr_type(self, expr: Node) -> str:
        if isinstance(expr, Literal):
            return expr.type_name
        if isinstance(expr, Variable):
            if expr.name not in self.symbols:
                raise CompileError(f"Error semantico: variable no declarada: {expr.name}")
            return self.symbols[expr.name]
        if isinstance(expr, Unary):
            t = self.expr_type(expr.expr)
            if expr.op == "-":
                if t != "numero":
                    raise CompileError("Error semantico: el operador '-' unario requiere numero")
                return "numero"
            if expr.op == "no":
                if t != "booleano":
                    raise CompileError("Error semantico: el operador 'no' requiere booleano")
                return "booleano"
        if isinstance(expr, Binary):
            left = self.expr_type(expr.left)
            right = self.expr_type(expr.right)
            if expr.op in {"+", "-", "*", "/"}:
                if left == right == "numero":
                    return "numero"
                if expr.op == "+" and left == right == "texto":
                    return "texto"
                raise CompileError(f"Error semantico: operador aritmetico '{expr.op}' requiere numeros; '+' tambien admite texto+texto")
            if expr.op in {"<", ">", "<=", ">="}:
                if left == right == "numero":
                    return "booleano"
                raise CompileError(f"Error semantico: operador relacional '{expr.op}' requiere numeros")
            if expr.op in {"==", "!="}:
                if left == right:
                    return "booleano"
                raise CompileError(f"Error semantico: comparacion incompatible entre {left} y {right}")
            if expr.op in {"y", "o"}:
                if left == right == "booleano":
                    return "booleano"
                raise CompileError(f"Error semantico: operador logico '{expr.op}' requiere booleanos")
        raise CompileError(f"Error interno: expresion no soportada {type(expr).__name__}")


# =============================
# Bytecode propio y generador
# =============================

@dataclass
class Instruction:
    op: str
    arg: Any = None

    def to_json(self) -> Dict[str, Any]:
        return {"op": self.op, "arg": self.arg}

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "Instruction":
        return Instruction(data["op"], data.get("arg"))


@dataclass
class BytecodeProgram:
    format: str
    version: int
    program: str
    instructions: List[Instruction]

    def to_json_text(self) -> str:
        payload = {
            "format": self.format,
            "version": self.version,
            "program": self.program,
            "instructions": [ins.to_json() for ins in self.instructions],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def from_json_text(text: str) -> "BytecodeProgram":
        data = json.loads(text)
        if data.get("format") != "CuencaBytecode":
            raise CompileError("Archivo de bytecode invalido: formato no reconocido")
        return BytecodeProgram(
            format=data["format"],
            version=int(data["version"]),
            program=data["program"],
            instructions=[Instruction.from_json(x) for x in data["instructions"]],
        )


class BytecodeGenerator:
    def __init__(self):
        self.instructions: List[Instruction] = []

    def emit(self, op: str, arg: Any = None) -> int:
        self.instructions.append(Instruction(op, arg))
        return len(self.instructions) - 1

    def patch(self, index: int, arg: Any) -> None:
        self.instructions[index].arg = arg

    def generate(self, program: Program) -> BytecodeProgram:
        for stmt in program.body:
            self.gen_stmt(stmt)
        self.emit("HALT")
        return BytecodeProgram("CuencaBytecode", 1, program.name, self.instructions)

    def gen_stmt(self, stmt: Node) -> None:
        if isinstance(stmt, VarDecl):
            self.emit("DECLARE", {"name": stmt.name, "type": stmt.var_type})
            if stmt.expr is None:
                defaults = {"numero": 0, "texto": "", "booleano": False}
                self.emit("PUSH", defaults[stmt.var_type])
            else:
                self.gen_expr(stmt.expr)
            self.emit("STORE", stmt.name)
        elif isinstance(stmt, Assign):
            self.gen_expr(stmt.expr)
            self.emit("STORE", stmt.name)
        elif isinstance(stmt, Print):
            self.gen_expr(stmt.expr)
            self.emit("PRINT")
        elif isinstance(stmt, If):
            self.gen_expr(stmt.condition)
            jump_false = self.emit("JMP_IF_FALSE", None)
            for s in stmt.then_body:
                self.gen_stmt(s)
            jump_end = self.emit("JMP", None)
            else_start = len(self.instructions)
            self.patch(jump_false, else_start)
            for s in stmt.else_body:
                self.gen_stmt(s)
            end = len(self.instructions)
            self.patch(jump_end, end)
        elif isinstance(stmt, While):
            loop_start = len(self.instructions)
            self.gen_expr(stmt.condition)
            exit_jump = self.emit("JMP_IF_FALSE", None)
            for s in stmt.body:
                self.gen_stmt(s)
            self.emit("JMP", loop_start)
            self.patch(exit_jump, len(self.instructions))
        else:
            raise CompileError(f"Generador: sentencia no soportada {type(stmt).__name__}")

    def gen_expr(self, expr: Node) -> None:
        if isinstance(expr, Literal):
            self.emit("PUSH", expr.value)
        elif isinstance(expr, Variable):
            self.emit("LOAD", expr.name)
        elif isinstance(expr, Unary):
            self.gen_expr(expr.expr)
            if expr.op == "-":
                self.emit("NEG")
            elif expr.op == "no":
                self.emit("NOT")
            else:
                raise CompileError(f"Generador: operador unario no soportado {expr.op}")
        elif isinstance(expr, Binary):
            self.gen_expr(expr.left)
            self.gen_expr(expr.right)
            op_map = {
                "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
                "<": "LT", ">": "GT", "<=": "LE", ">=": "GE",
                "==": "EQ", "!=": "NE", "y": "AND", "o": "OR",
            }
            self.emit(op_map[expr.op])
        else:
            raise CompileError(f"Generador: expresion no soportada {type(expr).__name__}")


def disassemble(bytecode: BytecodeProgram) -> str:
    lines = [f"; CuencaBytecode v{bytecode.version} - programa {bytecode.program}"]
    for idx, ins in enumerate(bytecode.instructions):
        arg = "" if ins.arg is None else f" {json.dumps(ins.arg, ensure_ascii=False)}"
        lines.append(f"{idx:04d}: {ins.op}{arg}")
    return "\n".join(lines)


# =============================
# Maquina virtual propia
# =============================

class CuencaVM:
    def __init__(self, bytecode: BytecodeProgram, *, max_steps: int = 100000):
        self.bytecode = bytecode
        self.instructions = bytecode.instructions
        self.ip = 0
        self.stack: List[Any] = []
        self.memory: Dict[str, Any] = {}
        self.types: Dict[str, str] = {}
        self.output: List[str] = []
        self.max_steps = max_steps

    def pop(self) -> Any:
        if not self.stack:
            raise RuntimeError("Error VM: pila vacia")
        return self.stack.pop()

    def run(self) -> List[str]:
        steps = 0
        while self.ip < len(self.instructions):
            if steps >= self.max_steps:
                raise RuntimeError("Error VM: se supero el limite de pasos; posible ciclo infinito")
            steps += 1
            ins = self.instructions[self.ip]
            self.ip += 1
            op, arg = ins.op, ins.arg

            if op == "PUSH":
                self.stack.append(arg)
            elif op == "DECLARE":
                name = arg["name"]
                typ = arg["type"]
                self.types[name] = typ
                self.memory.setdefault(name, None)
            elif op == "STORE":
                self.memory[arg] = self.pop()
            elif op == "LOAD":
                if arg not in self.memory:
                    raise RuntimeError(f"Error VM: variable no inicializada: {arg}")
                self.stack.append(self.memory[arg])
            elif op == "PRINT":
                value = self.pop()
                text = self.format_value(value)
                self.output.append(text)
                print(text)
            elif op == "NEG":
                self.stack.append(-self.pop())
            elif op == "NOT":
                self.stack.append(not bool(self.pop()))
            elif op in {"ADD", "SUB", "MUL", "DIV", "LT", "GT", "LE", "GE", "EQ", "NE", "AND", "OR"}:
                b = self.pop()
                a = self.pop()
                self.stack.append(self.apply_binary(op, a, b))
            elif op == "JMP":
                self.ip = int(arg)
            elif op == "JMP_IF_FALSE":
                cond = self.pop()
                if not bool(cond):
                    self.ip = int(arg)
            elif op == "HALT":
                break
            else:
                raise RuntimeError(f"Error VM: instruccion desconocida {op}")
        return self.output

    @staticmethod
    def format_value(value: Any) -> str:
        if isinstance(value, bool):
            return "verdadero" if value else "falso"
        return str(value)

    @staticmethod
    def apply_binary(op: str, a: Any, b: Any) -> Any:
        if op == "ADD": return a + b
        if op == "SUB": return a - b
        if op == "MUL": return a * b
        if op == "DIV": return a / b
        if op == "LT": return a < b
        if op == "GT": return a > b
        if op == "LE": return a <= b
        if op == "GE": return a >= b
        if op == "EQ": return a == b
        if op == "NE": return a != b
        if op == "AND": return bool(a) and bool(b)
        if op == "OR": return bool(a) or bool(b)
        raise RuntimeError(f"Operacion VM no soportada: {op}")


# =============================
# API publica y CLI
# =============================

def compile_source_to_bytecode(source: str) -> BytecodeProgram:
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer().analyze(ast)
    return BytecodeGenerator().generate(ast)


def ast_to_dict(node: Any) -> Any:
    if isinstance(node, list):
        return [ast_to_dict(x) for x in node]
    if isinstance(node, Node):
        data = {"node": type(node).__name__}
        data.update({k: ast_to_dict(v) for k, v in node.__dict__.items()})
        return data
    return node


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compilador CuencaLang a CuencaBytecode + CuencaVM")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="compila .clg a bytecode .cbc")
    p_compile.add_argument("source", help="archivo fuente .clg")
    p_compile.add_argument("-o", "--output", help="archivo destino .cbc")
    p_compile.add_argument("--tokens", action="store_true", help="muestra tokens")
    p_compile.add_argument("--ast", action="store_true", help="muestra AST")
    p_compile.add_argument("--dis", action="store_true", help="muestra bytecode legible")

    p_run = sub.add_parser("run", help="ejecuta un .clg o un .cbc")
    p_run.add_argument("source", help="archivo .clg o .cbc")
    p_run.add_argument("--max-steps", type=int, default=100000, help="limite de pasos de la VM")

    p_dis = sub.add_parser("dis", help="desensambla un .cbc")
    p_dis.add_argument("bytecode", help="archivo .cbc")

    args = parser.parse_args(argv)

    try:
        if args.command == "compile":
            source = open(args.source, "r", encoding="utf-8").read()
            tokens = Lexer(source).tokenize()
            if args.tokens:
                for token in tokens:
                    print(token)
            ast = Parser(tokens).parse()
            if args.ast:
                print(json.dumps(ast_to_dict(ast), ensure_ascii=False, indent=2))
            SemanticAnalyzer().analyze(ast)
            bytecode = BytecodeGenerator().generate(ast)
            if args.dis:
                print(disassemble(bytecode))
            output = args.output or re.sub(r"\.clg$", "", args.source) + ".cbc"
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(bytecode.to_json_text())
            print(f"Compilacion correcta: {args.source} -> {output}")
            return 0

        if args.command == "run":
            if args.source.endswith(".cbc"):
                bytecode = BytecodeProgram.from_json_text(open(args.source, "r", encoding="utf-8").read())
            else:
                source = open(args.source, "r", encoding="utf-8").read()
                bytecode = compile_source_to_bytecode(source)
            CuencaVM(bytecode, max_steps=args.max_steps).run()
            return 0

        if args.command == "dis":
            bytecode = BytecodeProgram.from_json_text(open(args.bytecode, "r", encoding="utf-8").read())
            print(disassemble(bytecode))
            return 0

    except (CompileError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
