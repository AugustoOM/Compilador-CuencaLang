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
