
from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lox.frontend import ErrorReporter, Parser, Scanner
from lox.frontend.expr import Expr
from lox.frontend.statement import ExpressionStmt, Stmt
import lox
from lox.bytecode import VM
from lox.interpreter import Interpreter


def parse(source: str, reporter: ErrorReporter | None = None) -> list[Stmt]:
    """Escanea y parsea `source`, devolviendo la lista de statements."""
    reporter = reporter or ErrorReporter()
    tokens = Scanner(source, reporter).scan_tokens()
    return Parser(tokens, reporter).parse()


def parse_expression(source: str, reporter: ErrorReporter | None = None) -> Expr:
    """Parsea `source` como una unica expresion (envuelta en un statement)."""
    statements = parse(source + ";", reporter)
    assert len(statements) == 1 and isinstance(statements[0], ExpressionStmt)
    return statements[0].expression


@dataclass
class RunResult:
    output: str
    reporter: ErrorReporter

    @property
    def lines(self) -> list[str]:
        return self.output.splitlines()


# Backends de ejecucion: "interpreter" (tree-walk) y "vm" (bytecode).
BACKENDS = ("interpreter", "vm")
_backend = "interpreter"


def run(source: str, backend: str | None = None) -> RunResult:
    """Corre el pipeline completo de la CLI con el backend indicado y captura stdout.

    Sin backend explicito usa el del test actual (ver `for_each_backend`).
    """
    backend = backend or _backend
    reporter = ErrorReporter()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        if backend == "interpreter":
            lox._run(source, reporter, Interpreter(reporter), stage="interpreter")
        else:
            lox._run(source, reporter, Interpreter(reporter), stage=None, vm=VM())
    return RunResult(buffer.getvalue(), reporter)


def _set_backend(backend: str) -> None:
    global _backend
    _backend = backend


def for_each_backend(cls: type[unittest.TestCase]) -> type[unittest.TestCase]:
    """Decorador de TestCase: la clase original corre con el tree-walk y se agrega
    al modulo una copia `<Clase>VM` que corre los mismos tests sobre la VM."""

    def setUp(self: unittest.TestCase) -> None:
        self.addCleanup(_set_backend, _backend)
        _set_backend("vm")
        cls.setUp(self)

    name = f"{cls.__name__}VM"
    variant = type(name, (cls,), {"setUp": setUp, "__module__": cls.__module__, "__qualname__": name})
    setattr(sys.modules[cls.__module__], name, variant)
    return cls
