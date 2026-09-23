"""Pruebas del resolver (analisis semantico / scope estatico)."""

from __future__ import annotations

import unittest

from lox_helpers import run


class TestErroresDeResolucion(unittest.TestCase):
    def test_leer_variable_local_en_su_propio_inicializador(self):
        resultado = run("var a = 1; { var a = a; }")
        self.assertTrue(resultado.reporter.had_error)

    def test_redeclarar_variable_en_mismo_scope(self):
        resultado = run("{ var a = 1; var a = 2; }")
        self.assertTrue(resultado.reporter.had_error)

    def test_redeclarar_en_scopes_distintos_esta_permitido(self):
        resultado = run('var a = "global"; { var a = "local"; print a; }')
        self.assertFalse(resultado.reporter.had_error)
        self.assertEqual(resultado.lines, ["local"])

    def test_return_fuera_de_funcion(self):
        resultado = run("return 1;")
        self.assertTrue(resultado.reporter.had_error)

    def test_return_dentro_de_funcion_esta_permitido(self):
        resultado = run("fun f() { return 1; } print f();")
        self.assertFalse(resultado.reporter.had_error)


class TestScopeEstatico(unittest.TestCase):
    def test_closure_resuelve_contra_el_scope_de_declaracion(self):
        # Ejemplo clasico: la funcion debe seguir viendo la 'a' global aunque
        # despues se declare una 'a' local en el mismo bloque.
        source = """
        var a = "global";
        {
          fun showA() { print a; }
          showA();
          var a = "block";
          showA();
        }
        """
        resultado = run(source)
        self.assertFalse(resultado.reporter.had_error)
        self.assertEqual(resultado.lines, ["global", "global"])

    def test_variable_global_no_declarada_falla_recien_en_runtime(self):
        resultado = run("print noExiste;")
        self.assertFalse(resultado.reporter.had_error)  # el resolver no la conoce, es global
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_shadowing_dentro_de_la_misma_funcion(self):
        source = """
        var x = "afuera";
        fun f() {
          var x = "adentro";
          print x;
        }
        f();
        print x;
        """
        resultado = run(source)
        self.assertEqual(resultado.lines, ["adentro", "afuera"])


if __name__ == "__main__":
    unittest.main()
