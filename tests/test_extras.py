"""Pruebas de las funcionalidades extra: asignacion compuesta y break/continue."""

from __future__ import annotations

import unittest

from lox_helpers import parse, parse_expression, run
from lox.errors import ErrorReporter
from lox.expr import AssignExpr, SetExpr
from lox.scanner import Scanner
from lox.statement import BreakStmt, ContinueStmt, WhileStmt
from lox.tokens import TokenKind


def _kinds(source: str) -> list[TokenKind]:
    return [t.kind for t in Scanner(source).scan_tokens()]


class TestScannerExtras(unittest.TestCase):
    def test_operadores_compuestos(self):
        self.assertEqual(
            _kinds("+= -= *= /= %="),
            [
                TokenKind.PLUS_EQUAL,
                TokenKind.MINUS_EQUAL,
                TokenKind.STAR_EQUAL,
                TokenKind.SLASH_EQUAL,
                TokenKind.PERCENT_EQUAL,
                TokenKind.EOF,
            ],
        )

    def test_operadores_simples_siguen_funcionando(self):
        self.assertEqual(
            _kinds("+ - * / %"),
            [TokenKind.PLUS, TokenKind.MINUS, TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT, TokenKind.EOF],
        )

    def test_slash_igual_no_rompe_comentarios(self):
        self.assertEqual(_kinds("a /= 2; // comentario /= raro"), _kinds("a /= 2;"))

    def test_break_y_continue_son_palabras_clave(self):
        self.assertEqual(_kinds("break continue"), [TokenKind.BREAK, TokenKind.CONTINUE, TokenKind.EOF])


class TestParserExtras(unittest.TestCase):
    def test_asignacion_compuesta_a_variable(self):
        expr = parse_expression("x += 1")
        self.assertIsInstance(expr, AssignExpr)
        self.assertEqual(expr.operator.kind, TokenKind.PLUS)

    def test_asignacion_compuesta_a_campo(self):
        expr = parse_expression("a.b *= 2")
        self.assertIsInstance(expr, SetExpr)
        self.assertEqual(expr.operator.kind, TokenKind.STAR)

    def test_asignacion_compuesta_es_asociativa_a_derecha(self):
        expr = parse_expression("a += b -= 1")
        self.assertIsInstance(expr, AssignExpr)
        self.assertIsInstance(expr.value, AssignExpr)
        self.assertEqual(expr.value.operator.kind, TokenKind.MINUS)

    def test_asignacion_compuesta_a_objetivo_invalido(self):
        reporter = ErrorReporter()
        parse("1 += 2;", reporter)
        self.assertTrue(reporter.had_error)

    def test_break_y_continue(self):
        (stmt,) = parse("while (true) { break; continue; }")
        self.assertIsInstance(stmt, WhileStmt)
        self.assertIsInstance(stmt.body.statements[0], BreakStmt)
        self.assertIsInstance(stmt.body.statements[1], ContinueStmt)

    def test_break_sin_punto_y_coma(self):
        reporter = ErrorReporter()
        parse("while (true) { break }", reporter)
        self.assertTrue(reporter.had_error)


class TestAsignacionCompuesta(unittest.TestCase):
    def test_todos_los_operadores(self):
        source = """
        var x = 10;
        x += 5;  print x;
        x -= 3;  print x;
        x *= 2;  print x;
        x /= 4;  print x;
        x %= 4;  print x;
        """
        self.assertEqual(run(source).lines, ["15", "12", "24", "6", "2"])

    def test_concatenacion_de_strings(self):
        self.assertEqual(run('var s = "ho"; s += "la"; print s;').lines, ["hola"])

    def test_devuelve_el_nuevo_valor(self):
        self.assertEqual(run("var x = 1; print x += 2;").lines, ["3"])

    def test_variable_local_y_closure(self):
        source = """
        fun contador() {
          var n = 0;
          fun inc() { n += 1; return n; }
          return inc;
        }
        var c = contador();
        c();
        c();
        print c();
        """
        self.assertEqual(run(source).lines, ["3"])

    def test_sobre_campos(self):
        source = """
        class Cuenta {
          init() { this.saldo = 0; }
          depositar(m) { this.saldo += m; return this; }
        }
        var c = Cuenta();
        c.depositar(100).depositar(50);
        c.saldo -= 30;
        print c.saldo;
        """
        self.assertEqual(run(source).lines, ["120"])

    def test_el_objeto_se_evalua_una_sola_vez(self):
        source = """
        class Caja { init() { this.v = 1; } }
        var llamadas = 0;
        var caja = Caja();
        fun obtener() { llamadas += 1; return caja; }
        obtener().v += 10;
        print caja.v;
        print llamadas;
        """
        self.assertEqual(run(source).lines, ["11", "1"])

    def test_tipos_incompatibles_es_error(self):
        resultado = run('var x = 1; x += "a";')
        self.assertTrue(resultado.reporter.had_runtime_error)
        self.assertIn("Los operandos deben ser dos numeros o dos cadenas", resultado.output)

    def test_division_por_cero(self):
        resultado = run("var x = 1; x /= 0;")
        self.assertTrue(resultado.reporter.had_runtime_error)
        self.assertIn("Division por cero", resultado.output)

    def test_variable_no_definida(self):
        resultado = run("noExiste += 1;")
        self.assertTrue(resultado.reporter.had_runtime_error)
        self.assertIn("Variable no definida 'noExiste'", resultado.output)

    def test_campo_no_definido(self):
        resultado = run("class A {} var a = A(); a.x += 1;")
        self.assertTrue(resultado.reporter.had_runtime_error)
        self.assertIn("Propiedad no definida 'x'", resultado.output)


class TestBreakContinue(unittest.TestCase):
    def test_break_en_while(self):
        source = """
        var i = 0;
        while (true) {
          if (i == 3) break;
          print i;
          i += 1;
        }
        print "fin";
        """
        self.assertEqual(run(source).lines, ["0", "1", "2", "fin"])

    def test_break_en_for(self):
        source = """
        for (var i = 0; i < 10; i += 1) {
          if (i == 2) break;
          print i;
        }
        """
        self.assertEqual(run(source).lines, ["0", "1"])

    def test_continue_en_for_ejecuta_el_incremento(self):
        source = """
        for (var i = 0; i < 6; i += 1) {
          if (i % 2 == 0) continue;
          print i;
        }
        """
        self.assertEqual(run(source).lines, ["1", "3", "5"])

    def test_continue_en_while(self):
        source = """
        var i = 0;
        while (i < 5) {
          i += 1;
          if (i == 3) continue;
          print i;
        }
        """
        self.assertEqual(run(source).lines, ["1", "2", "4", "5"])

    def test_break_solo_sale_del_bucle_interno(self):
        source = """
        for (var i = 0; i < 3; i += 1) {
          for (var j = 0; j < 3; j += 1) {
            if (j == 1) break;
            print i * 10 + j;
          }
        }
        """
        self.assertEqual(run(source).lines, ["0", "10", "20"])

    def test_break_dentro_de_bloques_anidados_restaura_el_entorno(self):
        source = """
        var x = "global";
        while (true) {
          var x = "loop";
          {
            var x = "bloque";
            break;
          }
        }
        print x;
        """
        self.assertEqual(run(source).lines, ["global"])

    def test_continue_saltea_la_vuelta_en_un_acumulador(self):
        source = """
        var total = 0;
        for (var i = 0; i < 5; i += 1) {
          if (i == 2) continue;
          total += i;
        }
        print total;
        """
        self.assertEqual(run(source).lines, ["8"])

    def test_break_dentro_de_metodo(self):
        source = """
        class Buscador {
          primerMultiplo(n, desde) {
            var i = desde;
            while (true) {
              if (i % n == 0) break;
              i += 1;
            }
            return i;
          }
        }
        print Buscador().primerMultiplo(7, 30);
        """
        self.assertEqual(run(source).lines, ["35"])

    def test_break_fuera_de_bucle(self):
        resultado = run("break;")
        self.assertTrue(resultado.reporter.had_error)
        self.assertIn("No se puede usar 'break' fuera de un bucle", resultado.output)

    def test_continue_fuera_de_bucle(self):
        resultado = run("if (true) continue;")
        self.assertTrue(resultado.reporter.had_error)
        self.assertIn("No se puede usar 'continue' fuera de un bucle", resultado.output)

    def test_break_no_cruza_funciones(self):
        resultado = run("while (true) { fun f() { break; } }")
        self.assertTrue(resultado.reporter.had_error)
        self.assertIn("No se puede usar 'break' fuera de un bucle", resultado.output)


if __name__ == "__main__":
    unittest.main()
