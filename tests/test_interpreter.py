"""Pruebas del interprete: evaluacion de expresiones, estado y control de flujo."""

from __future__ import annotations

import unittest

from lox_helpers import run


class TestAritmetica(unittest.TestCase):
    def test_precedencia_de_operadores(self):
        self.assertEqual(run("print 1 + 2 * 3;").lines, ["7"])

    def test_division(self):
        self.assertEqual(run("print 7 / 2;").lines, ["3.5"])

    def test_modulo(self):
        self.assertEqual(run("print 7 % 3;").lines, ["1"])

    def test_numeros_enteros_se_imprimen_sin_decimales(self):
        self.assertEqual(run("print 6 / 2;").lines, ["3"])

    def test_concatenacion_de_strings(self):
        self.assertEqual(run('print "foo" + "bar";').lines, ["foobar"])

    def test_negacion_unaria(self):
        self.assertEqual(run("print -(1 + 1);").lines, ["-2"])

    def test_division_por_cero_es_error_de_runtime(self):
        resultado = run("print 1 / 0;")
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_modulo_por_cero_es_error_de_runtime(self):
        resultado = run("print 1 % 0;")
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_sumar_numero_y_string_es_error_de_runtime(self):
        resultado = run('print 1 + "a";')
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_restar_strings_es_error_de_runtime(self):
        resultado = run('print "a" - "b";')
        self.assertTrue(resultado.reporter.had_runtime_error)


class TestComparacionesYVerdad(unittest.TestCase):
    def test_comparaciones_numericas(self):
        self.assertEqual(run("print 1 < 2; print 2 <= 2; print 3 > 2; print 2 >= 3;").lines,
                          ["true", "true", "true", "false"])

    def test_igualdad_entre_tipos_distintos_es_false(self):
        self.assertEqual(run('print 1 == "1"; print nil == false;').lines, ["false", "false"])

    def test_nil_y_false_son_falsy_el_resto_truthy(self):
        source = """
        if (nil) print "malo"; else print "nil falsy";
        if (false) print "malo"; else print "false falsy";
        if (0) print "0 truthy"; else print "malo";
        if ("") print "vacio truthy"; else print "malo";
        """
        self.assertEqual(
            run(source).lines,
            ["nil falsy", "false falsy", "0 truthy", "vacio truthy"],
        )


class TestEstadoYScopes(unittest.TestCase):
    def test_declarar_y_leer_variable(self):
        self.assertEqual(run("var x = 5; print x;").lines, ["5"])

    def test_variable_sin_inicializador_es_nil(self):
        self.assertEqual(run("var x; print x;").lines, ["nil"])

    def test_asignacion_reasigna_variable_existente(self):
        self.assertEqual(run("var x = 1; x = 2; print x;").lines, ["2"])

    def test_asignacion_a_variable_no_definida_es_error(self):
        resultado = run("x = 1;")
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_bloque_no_filtra_shadowing_hacia_afuera(self):
        source = 'var x = "afuera"; { var x = "adentro"; print x; } print x;'
        self.assertEqual(run(source).lines, ["adentro", "afuera"])

    def test_asignacion_dentro_de_bloque_modifica_variable_externa(self):
        source = "var x = 1; { x = 2; } print x;"
        self.assertEqual(run(source).lines, ["2"])


class TestControlDeFlujo(unittest.TestCase):
    def test_while(self):
        source = "var i = 0; while (i < 3) { print i; i = i + 1; }"
        self.assertEqual(run(source).lines, ["0", "1", "2"])

    def test_for(self):
        source = "for (var i = 0; i < 3; i = i + 1) print i;"
        self.assertEqual(run(source).lines, ["0", "1", "2"])

    def test_and_hace_cortocircuito(self):
        # Si hiciera cortocircuito mal, evaluaria el lado derecho igual.
        source = 'fun boom() { print "no deberia imprimirse"; return true; } print false and boom();'
        self.assertEqual(run(source).lines, ["false"])

    def test_or_hace_cortocircuito(self):
        source = 'fun boom() { print "no deberia imprimirse"; return true; } print true or boom();'
        self.assertEqual(run(source).lines, ["true"])

    def test_and_devuelve_el_operando_no_un_booleano(self):
        self.assertEqual(run('print "a" and "b";').lines, ["b"])


if __name__ == "__main__":
    unittest.main()
