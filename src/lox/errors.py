"""Tipos de error y reporte centralizado del scanner."""

from __future__ import annotations

from dataclasses import dataclass
from .tokens import Token, TokenKind


class LoxError(Exception):
    """Raiz de todos los errores propios de Lox."""


@dataclass
class ScanError(LoxError):
    line: int
    message: str

    def __str__(self) -> str:  
        return f"[linea {self.line}] Error lexico: {self.message}"


class ErrorReporter:
    """Acumula errores y decide si la corrida fue exitosa."""

    def __init__(self) -> None:
        self.had_error = False
        self.had_runtime_error = False

    def report(self, error: LoxError) -> None:
        print(str(error))
        if isinstance(error, LoxRuntimeError):
            self.had_runtime_error = True
        else:
            self.had_error = True

    def reset(self) -> None:
        self.had_error = False
        self.had_runtime_error = False

@dataclass
class ParseError(LoxError):
    token: Token
    message: str
    def __str__(self) -> str:
        if self.token.kind == TokenKind.EOF:
            return f"[linea {self.token.line}] Error sintactico al final: {self.message}"
        return f"[linea {self.token.line}] Error sintactico en '{self.token.lexeme}': {self.message}"

@dataclass
class LoxRuntimeError(LoxError):
    token: Token
    message: str
    def __str__(self) -> str:
        return f"[linea {self.token.line}] Error en tiempo de ejecucion: {self.message}"
