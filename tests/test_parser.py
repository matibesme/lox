"""Pruebas del parser de Lox."""

from __future__ import annotations

import unittest

from lox_helpers import parse, parse_expression
from lox.errors import ErrorReporter
from lox.expr import AssignExpr, BinaryExpr, CallExpr, LiteralExpr, LogicalExpr, UnaryExpr, VariableExpr
from lox.statement import (
    BlockStmt,
    ExpressionStmt,
    FunctionStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    VarStmt,
    WhileStmt,
)
from lox.tokens import TokenKind


class TestPrecedencia(unittest.TestCase):
    def test_multiplicacion_ata_mas_fuerte_que_suma(self):
        expr = parse_expression("1 + 2 * 3")
        self.assertIsInstance(expr, BinaryExpr)
        self.assertEqual(expr.operator.kind, TokenKind.PLUS)
        self.assertIsInstance(expr.left, LiteralExpr)
        self.assertIsInstance(expr.right, BinaryExpr)
        self.assertEqual(expr.right.operator.kind, TokenKind.STAR)

    def test_parentesis_cambia_precedencia(self):
        expr = parse_expression("(1 + 2) * 3")
        self.assertIsInstance(expr, BinaryExpr)
        self.assertEqual(expr.operator.kind, TokenKind.STAR)
        self.assertEqual(expr.left.__class__.__name__, "GroupingExpr")

    def test_unario_mas_fuerte_que_binario(self):
        expr = parse_expression("-1 + 2")
        self.assertIsInstance(expr, BinaryExpr)
        self.assertIsInstance(expr.left, UnaryExpr)

    def test_comparaciones_encadenadas_asocian_izquierda(self):
        expr = parse_expression("1 < 2 < 3")
        self.assertIsInstance(expr, BinaryExpr)
        self.assertEqual(expr.operator.kind, TokenKind.LESS)
        self.assertIsInstance(expr.left, BinaryExpr)

    def test_and_ata_mas_fuerte_que_or(self):
        expr = parse_expression("true or false and false")
        self.assertIsInstance(expr, LogicalExpr)
        self.assertEqual(expr.operator.kind, TokenKind.OR)
        self.assertIsInstance(expr.right, LogicalExpr)
        self.assertEqual(expr.right.operator.kind, TokenKind.AND)

    def test_asignacion_asocia_derecha(self):
        expr = parse_expression("a = b = 3")
        self.assertIsInstance(expr, AssignExpr)
        self.assertEqual(expr.name.lexeme, "a")
        self.assertIsInstance(expr.value, AssignExpr)

    def test_llamada_encadenada(self):
        expr = parse_expression("f(1)(2)")
        self.assertIsInstance(expr, CallExpr)
        self.assertIsInstance(expr.callee, CallExpr)


class TestDeclaraciones(unittest.TestCase):
    def test_var_sin_inicializador(self):
        (stmt,) = parse("var x;")
        self.assertIsInstance(stmt, VarStmt)
        self.assertIsNone(stmt.initializer)

    def test_var_con_inicializador(self):
        (stmt,) = parse("var x = 1;")
        self.assertIsInstance(stmt, VarStmt)
        self.assertIsInstance(stmt.initializer, LiteralExpr)

    def test_bloque_anidado(self):
        (stmt,) = parse("{ var x = 1; { print x; } }")
        self.assertIsInstance(stmt, BlockStmt)
        self.assertIsInstance(stmt.statements[0], VarStmt)
        self.assertIsInstance(stmt.statements[1], BlockStmt)

    def test_funcion_con_parametros_y_cuerpo(self):
        (stmt,) = parse("fun suma(a, b) { return a + b; }")
        self.assertIsInstance(stmt, FunctionStmt)
        self.assertEqual([p.lexeme for p in stmt.params], ["a", "b"])
        self.assertIsInstance(stmt.body[0], ReturnStmt)

    def test_funcion_sin_parametros(self):
        (stmt,) = parse("fun f() { print 1; }")
        self.assertEqual(stmt.params, [])


class TestControlDeFlujo(unittest.TestCase):
    def test_if_sin_else(self):
        (stmt,) = parse("if (true) print 1;")
        self.assertIsInstance(stmt, IfStmt)
        self.assertIsNone(stmt.else_branch)

    def test_if_con_else(self):
        (stmt,) = parse("if (true) print 1; else print 2;")
        self.assertIsInstance(stmt, IfStmt)
        self.assertIsNotNone(stmt.else_branch)

    def test_while(self):
        (stmt,) = parse("while (true) print 1;")
        self.assertIsInstance(stmt, WhileStmt)

    def test_for_desazucara_en_bloque_con_while(self):
        # for (var i = 0; i < 3; i = i + 1) print i;
        # debe quedar como: { var i = 0; while (i < 3) { print i; i = i + 1; } }
        (stmt,) = parse("for (var i = 0; i < 3; i = i + 1) print i;")
        self.assertIsInstance(stmt, BlockStmt)
        self.assertIsInstance(stmt.statements[0], VarStmt)
        while_stmt = stmt.statements[1]
        self.assertIsInstance(while_stmt, WhileStmt)
        self.assertIsInstance(while_stmt.body, BlockStmt)
        self.assertIsInstance(while_stmt.body.statements[0], PrintStmt)
        self.assertIsInstance(while_stmt.body.statements[1], ExpressionStmt)

    def test_for_sin_condicion_usa_true_literal(self):
        (stmt,) = parse("for (;;) print 1;")
        self.assertIsInstance(stmt.condition, LiteralExpr)
        self.assertTrue(stmt.condition.value)


class TestErroresSintacticos(unittest.TestCase):
    def test_falta_punto_y_coma_reporta_error(self):
        rep = ErrorReporter()
        parse("var x = 1", rep)
        self.assertTrue(rep.had_error)

    def test_asignacion_a_algo_invalido_reporta_error(self):
        rep = ErrorReporter()
        parse("1 = 2;", rep)
        self.assertTrue(rep.had_error)

    def test_parser_continua_tras_error(self):
        # El primer statement esta roto, pero el segundo debe parsearse igual.
        rep = ErrorReporter()
        statements = parse("var ;\nprint 1;", rep)
        self.assertTrue(rep.had_error)
        self.assertTrue(any(isinstance(s, PrintStmt) for s in statements))

    def test_expresion_vacia_reporta_error(self):
        rep = ErrorReporter()
        parse(");", rep)
        self.assertTrue(rep.had_error)


if __name__ == "__main__":
    unittest.main()
