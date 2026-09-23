"""Pruebas de las banderas de fase (--scanning / --parsing) del entrypoint."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import lox


def run_stage(source: str, stage: str | None) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".lox", delete=False, encoding="utf-8") as f:
        f.write(source)
        path = f.name
    try:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            lox._run_file(path, stage)
        return buffer.getvalue()
    finally:
        os.remove(path)


class TestBanderaScanning(unittest.TestCase):
    def test_muestra_tokens_y_no_ejecuta(self):
        salida = run_stage('print "marcador";', "scanning")
        # No debe aparecer como linea propia (es decir, ejecutado por el print);
        # solo debe aparecer citado, como parte del token STRING.
        self.assertNotIn("marcador\n", salida)
        self.assertIn("STRING", salida)
        self.assertIn("'marcador'", salida)
        self.assertIn("PRINT", salida)
        self.assertIn("EOF", salida)

    def test_un_token_por_linea(self):
        salida = run_stage("1 + 2", "scanning")
        self.assertEqual(len(salida.splitlines()), 4)  # NUMBER PLUS NUMBER EOF


class TestBanderaParsing(unittest.TestCase):
    def test_muestra_arbol_de_expresion_con_precedencia(self):
        salida = run_stage("1 + 2 + 3;", "parsing")
        self.assertEqual(salida.strip(), "((<1.0> PLUS <2.0>) PLUS <3.0>)")

    def test_no_ejecuta_el_programa(self):
        salida = run_stage('print "marcador";', "parsing")
        # Se muestra el AST del statement, no la salida de ejecutarlo.
        self.assertNotIn("marcador\n", salida)
        self.assertIn("PrintStmt", salida)


class TestSinBandera(unittest.TestCase):
    def test_ejecuta_normalmente(self):
        salida = run_stage('print "hola";', None)
        self.assertEqual(salida.strip(), "hola")


class TestParseoDeArgumentos(unittest.TestCase):
    def test_bandera_desconocida_sale_con_codigo_64(self):
        with self.assertRaises(SystemExit) as ctx:
            lox._parse_args(["--nope", "script.lox"])
        self.assertEqual(ctx.exception.code, 64)

    def test_bandera_valida_y_script(self):
        stage, script = lox._parse_args(["--scanning", "script.lox"])
        self.assertEqual(stage, "scanning")
        self.assertEqual(script, "script.lox")

    def test_sin_argumentos(self):
        stage, script = lox._parse_args([])
        self.assertIsNone(stage)
        self.assertIsNone(script)


if __name__ == "__main__":
    unittest.main()
