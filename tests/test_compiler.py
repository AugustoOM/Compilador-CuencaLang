import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPILER = ROOT / "cuencalang_compiler.py"
EXAMPLE = ROOT / "examples" / "oferta_demanda.clg"

def test_compiles_valid_example(tmp_path):
    out = tmp_path / "salida.py"
    result = subprocess.run([sys.executable, str(COMPILER), str(EXAMPLE), "-o", str(out)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.exists()
    run = subprocess.run([sys.executable, str(out)], capture_output=True, text=True)
    assert "Analisis de oferta y demanda" in run.stdout
    assert "Oferta mayor que demanda" in run.stdout


def test_rejects_undeclared_variable():
    bad = ROOT / "examples" / "error_variable_no_declarada.clg"
    result = subprocess.run([sys.executable, str(COMPILER), str(bad)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Variable no declarada" in result.stderr


def test_rejects_missing_semicolon(tmp_path):
    bad = tmp_path / "sin_punto_y_coma.clg"
    bad.write_text("programa X { numero x = 10 imprimir x; }", encoding="utf-8")
    result = subprocess.run([sys.executable, str(COMPILER), str(bad)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "faltante" in result.stderr


def test_rejects_unclosed_string(tmp_path):
    bad = tmp_path / "cadena_sin_cerrar.clg"
    bad.write_text('programa X { texto saludo = "hola; }', encoding="utf-8")
    result = subprocess.run([sys.executable, str(COMPILER), str(bad)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "sin cerrar" in result.stderr


def test_rejects_unknown_variable_type(tmp_path):
    bad = tmp_path / "tipo_desconocido.clg"
    bad.write_text("programa X { decimal precio = 10; }", encoding="utf-8")
    result = subprocess.run([sys.executable, str(COMPILER), str(bad)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Tipo de variable desconocido" in result.stderr
