"""Tipos de error y reporte centralizado del scanner."""

from __future__ import annotations

from dataclasses import dataclass


class LoxError(Exception):
    """Raiz de todos los errores propios de Lox."""


@dataclass
class ScanError(LoxError):
    line: int
    message: str

    def __str__(self) -> str:  # pragma: no cover - formato
        return f"[linea {self.line}] Error lexico: {self.message}"


class ErrorReporter:
    """Acumula errores y decide si la corrida fue exitosa."""

    def __init__(self) -> None:
        self.had_error = False

    def report(self, error: LoxError) -> None:
        print(str(error))
        self.had_error = True

    def reset(self) -> None:
        self.had_error = False
