"""Corre los tests oficiales de la catedra (tests/catedra/real-tests, bajados de
https://github.com/FdelMazo/plox/tree/main/real-tests) contra nuestro interprete.

Los .lox de esa carpeta no se tocan: son los archivos originales de la catedra.
El criterio de exito es el mismo que usa su script.py: correr cada archivo y
verificar que la salida no contenga la palabra "ERROR" (los .lox tienen su
propio helper `assert` que imprime "OK" o "ERROR" por cada caso).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from lox_helpers import run

_REAL_TESTS_DIR = Path(__file__).parent / "catedra" / "real-tests"


def _cases() -> list[Path]:
    return sorted(_REAL_TESTS_DIR.glob("*.lox"))


class TestCatedra(unittest.TestCase):
    pass


def _make_test(path: Path):
    def test(self: TestCatedra) -> None:
        source = path.read_text(encoding="utf-8")
        resultado = run(source)
        self.assertFalse(resultado.reporter.had_error, resultado.output)
        self.assertFalse(resultado.reporter.had_runtime_error, resultado.output)
        self.assertNotIn("ERROR", resultado.output, resultado.output)

    return test


for _path in _cases():
    setattr(TestCatedra, f"test_{_path.stem.replace('-', '_')}", _make_test(_path))


if __name__ == "__main__":
    unittest.main()
