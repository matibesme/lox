"""Pruebas del scanner de Lox."""

from __future__ import annotations

import os
import sys
import unittest

# Permite correr los tests con `python -m unittest` sin instalar el paquete.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lox.errors import ErrorReporter
from lox.scanner import Scanner
from lox.tokens import TokenKind


def scan(source: str) -> list:
    """Devuelve los tokens de `source` (usando un reporter descartable)."""
    return Scanner(source, ErrorReporter()).scan_tokens()


def kinds(source: str) -> list[TokenKind]:
    """Solo los tipos de token, para comparar comodo."""
    return [t.kind for t in scan(source)]


class TestTokensBasicos(unittest.TestCase):
    def test_fuente_vacio_solo_eof(self):
        toks = scan("")
        self.assertEqual(len(toks), 1)
        self.assertEqual(toks[0].kind, TokenKind.EOF)

    def test_simbolos_de_un_caracter(self):
        self.assertEqual(
            kinds("(){},.-+;*"),
            [
                TokenKind.LEFT_PAREN,
                TokenKind.RIGHT_PAREN,
                TokenKind.LEFT_BRACE,
                TokenKind.RIGHT_BRACE,
                TokenKind.COMMA,
                TokenKind.DOT,
                TokenKind.MINUS,
                TokenKind.PLUS,
                TokenKind.SEMICOLON,
                TokenKind.STAR,
                TokenKind.EOF,
            ],
        )

    def test_operadores_de_dos_caracteres(self):
        self.assertEqual(
            kinds("! != = == < <= > >="),
            [
                TokenKind.BANG,
                TokenKind.BANG_EQUAL,
                TokenKind.EQUAL,
                TokenKind.EQUAL_EQUAL,
                TokenKind.LESS,
                TokenKind.LESS_EQUAL,
                TokenKind.GREATER,
                TokenKind.GREATER_EQUAL,
                TokenKind.EOF,
            ],
        )

    def test_slash_suelto_es_division(self):
        self.assertEqual(kinds("8 / 2"), [TokenKind.NUMBER, TokenKind.SLASH, TokenKind.NUMBER, TokenKind.EOF])


class TestLiterales(unittest.TestCase):
    def test_numero_entero_y_decimal(self):
        toks = scan("42 3.14")
        self.assertEqual(toks[0].kind, TokenKind.NUMBER)
        self.assertEqual(toks[0].literal, 42.0)
        self.assertEqual(toks[1].literal, 3.14)

    def test_punto_final_no_forma_parte_del_numero(self):
        # "123." debe ser NUMBER seguido de DOT, no un decimal.
        self.assertEqual(kinds("123."), [TokenKind.NUMBER, TokenKind.DOT, TokenKind.EOF])

    def test_string_guarda_valor_sin_comillas(self):
        toks = scan('"hola mundo"')
        self.assertEqual(toks[0].kind, TokenKind.STRING)
        self.assertEqual(toks[0].literal, "hola mundo")

    def test_string_multilinea_cuenta_lineas(self):
        toks = scan('"a\nb"\n+')
        self.assertEqual(toks[0].literal, "a\nb")
        # El '+' esta en la linea 2 (el salto dentro del string ya conto).
        mas = toks[1]
        self.assertEqual(mas.kind, TokenKind.PLUS)
        self.assertEqual(mas.line, 3)


class TestIdentificadoresYKeywords(unittest.TestCase):
    def test_identificador_simple(self):
        toks = scan("promedio")
        self.assertEqual(toks[0].kind, TokenKind.IDENTIFIER)
        self.assertEqual(toks[0].lexeme, "promedio")

    def test_todas_las_keywords(self):
        fuente = "and class else false for fun if nil or print return super this true var while"
        esperado = [
            TokenKind.AND, TokenKind.CLASS, TokenKind.ELSE, TokenKind.FALSE,
            TokenKind.FOR, TokenKind.FUN, TokenKind.IF, TokenKind.NIL,
            TokenKind.OR, TokenKind.PRINT, TokenKind.RETURN, TokenKind.SUPER,
            TokenKind.THIS, TokenKind.TRUE, TokenKind.VAR, TokenKind.WHILE,
            TokenKind.EOF,
        ]
        self.assertEqual(kinds(fuente), esperado)

    def test_keyword_como_prefijo_es_identificador(self):
        # "orden" empieza con "or" pero es un identificador.
        toks = scan("orden ifx classe")
        self.assertTrue(all(t.kind == TokenKind.IDENTIFIER for t in toks[:3]))

    def test_identificador_con_guion_bajo_y_digitos(self):
        toks = scan("_x1 var2")
        self.assertEqual(toks[0].kind, TokenKind.IDENTIFIER)
        self.assertEqual(toks[1].kind, TokenKind.IDENTIFIER)


class TestComentarios(unittest.TestCase):
    def test_comentario_de_linea_se_ignora(self):
        self.assertEqual(kinds("1 // esto no cuenta\n2"), [TokenKind.NUMBER, TokenKind.NUMBER, TokenKind.EOF])

    def test_comentario_de_bloque(self):
        self.assertEqual(kinds("1 /* nota */ 2"), [TokenKind.NUMBER, TokenKind.NUMBER, TokenKind.EOF])

    def test_comentario_de_bloque_anidado(self):
        self.assertEqual(kinds("1 /* a /* b */ c */ 2"), [TokenKind.NUMBER, TokenKind.NUMBER, TokenKind.EOF])


class TestLineas(unittest.TestCase):
    def test_numero_de_linea_avanza_con_saltos(self):
        toks = scan("a\nb\n\nc")
        self.assertEqual(toks[0].line, 1)
        self.assertEqual(toks[1].line, 2)
        self.assertEqual(toks[2].line, 4)


class TestErrores(unittest.TestCase):
    def test_string_sin_cerrar_reporta_error(self):
        rep = ErrorReporter()
        Scanner('"sin cerrar', rep).scan_tokens()
        self.assertTrue(rep.had_error)

    def test_caracter_invalido_reporta_error(self):
        rep = ErrorReporter()
        Scanner("@", rep).scan_tokens()
        self.assertTrue(rep.had_error)

    def test_comentario_de_bloque_sin_cerrar_reporta_error(self):
        rep = ErrorReporter()
        Scanner("/* abierto", rep).scan_tokens()
        self.assertTrue(rep.had_error)

    def test_fuente_valido_no_reporta_error(self):
        rep = ErrorReporter()
        Scanner('var x = 1 + "ok";', rep).scan_tokens()
        self.assertFalse(rep.had_error)

    def test_scanner_continua_tras_error(self):
        # Un caracter invalido no debe frenar el resto del escaneo.
        toks = scan("@ 1")
        self.assertIn(TokenKind.NUMBER, [t.kind for t in toks])


if __name__ == "__main__":
    unittest.main()
