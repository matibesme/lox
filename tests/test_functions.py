"""Pruebas de funciones, closures y funciones nativas."""

from __future__ import annotations

import unittest

from lox_helpers import run


class TestFuncionesBasicas(unittest.TestCase):
    def test_funcion_sin_return_devuelve_nil(self):
        self.assertEqual(run("fun f() {} print f();").lines, ["nil"])

    def test_funcion_con_return(self):
        self.assertEqual(run("fun suma(a, b) { return a + b; } print suma(2, 3);").lines, ["5"])

    def test_return_temprano_corta_ejecucion(self):
        source = """
        fun f() {
          print "antes";
          return 1;
          print "despues";
        }
        f();
        """
        self.assertEqual(run(source).lines, ["antes"])

    def test_funcion_se_imprime_como_fn(self):
        self.assertEqual(run("fun f() {} print f;").lines, ["<fn f>"])

    def test_recursion(self):
        source = """
        fun factorial(n) {
          if (n <= 1) return 1;
          return n * factorial(n - 1);
        }
        print factorial(5);
        """
        self.assertEqual(run(source).lines, ["120"])


class TestClosures(unittest.TestCase):
    def test_closure_captura_variable_por_referencia(self):
        source = """
        fun makeCounter() {
          var count = 0;
          fun increment() {
            count = count + 1;
            return count;
          }
          return increment;
        }
        var counter = makeCounter();
        print counter();
        print counter();
        print counter();
        """
        self.assertEqual(run(source).lines, ["1", "2", "3"])

    def test_dos_closures_del_mismo_generador_no_comparten_estado(self):
        source = """
        fun makeCounter() {
          var count = 0;
          fun increment() { count = count + 1; return count; }
          return increment;
        }
        var a = makeCounter();
        var b = makeCounter();
        a();
        a();
        print a();
        print b();
        """
        self.assertEqual(run(source).lines, ["3", "1"])


class TestErroresDeLlamadas(unittest.TestCase):
    def test_llamar_algo_que_no_es_invocable_es_error(self):
        resultado = run('var x = 1; x();')
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_cantidad_incorrecta_de_argumentos_es_error(self):
        resultado = run("fun f(a, b) { return a + b; } f(1);")
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_llamar_variable_no_definida_es_error(self):
        resultado = run("noExiste();")
        self.assertTrue(resultado.reporter.had_runtime_error)


class TestNativas(unittest.TestCase):
    def test_clock_no_recibe_argumentos_y_devuelve_numero(self):
        resultado = run("print clock() >= 0;")
        self.assertFalse(resultado.reporter.had_runtime_error)
        self.assertEqual(resultado.lines, ["true"])

    def test_clock_con_argumentos_es_error(self):
        resultado = run("clock(1);")
        self.assertTrue(resultado.reporter.had_runtime_error)


if __name__ == "__main__":
    unittest.main()
