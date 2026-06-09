import io
import os
import sys
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from cuencalang import CompileError, CuencaVM, Lexer, Parser, SemanticAnalyzer, BytecodeGenerator, compile_source_to_bytecode, disassemble


def compile_and_capture(source: str):
    bytecode = compile_source_to_bytecode(source)
    buf = io.StringIO()
    with redirect_stdout(buf):
        out = CuencaVM(bytecode).run()
    return bytecode, out, buf.getvalue()


class CuencaLangTests(unittest.TestCase):
    def test_programa_valido_oferta_demanda(self):
        path = os.path.join(ROOT, "examples", "oferta_demanda.clg")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        bytecode, output, text = compile_and_capture(source)
        self.assertEqual(bytecode.format, "CuencaBytecode")
        self.assertIn("Analisis de oferta y demanda", output)
        self.assertIn("120", output)
        self.assertTrue(output[-1] == "120")
        self.assertIn("JMP_IF_FALSE", disassemble(bytecode))

    def test_programa_valido_ahorro(self):
        with open(os.path.join(ROOT, "examples", "ahorro_simple.clg"), encoding="utf-8") as f:
            source = f.read()
        _, output, _ = compile_and_capture(source)
        self.assertEqual(output, ["1050", "1100", "1150"])

    def test_tokens(self):
        tokens = Lexer('programa X { numero a = 1; imprimir a; }').tokenize()
        self.assertEqual(tokens[0].type, "PROGRAMA")
        self.assertTrue(any(t.type == "IMPRIMIR" for t in tokens))

    def test_error_variable_no_declarada(self):
        source = 'programa X { imprimir total; }'
        with self.assertRaises(CompileError):
            compile_source_to_bytecode(source)

    def test_error_tipo_incompatible(self):
        source = 'programa X { numero x = "hola"; }'
        with self.assertRaises(CompileError):
            compile_source_to_bytecode(source)

    def test_error_condicion_no_booleana(self):
        source = 'programa X { si (5) { imprimir 1; } }'
        with self.assertRaises(CompileError):
            compile_source_to_bytecode(source)

    def test_serializacion_bytecode(self):
        bc = compile_source_to_bytecode('programa X { numero x = 2 + 3; imprimir x; }')
        text = bc.to_json_text()
        self.assertIn('CuencaBytecode', text)


if __name__ == "__main__":
    unittest.main()
