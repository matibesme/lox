
from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lox.errors import ErrorReporter
from lox.expr import Expr
from lox.interpreter import Interpreter
from lox.parser import Parser
from lox.resolver import Resolver
from lox.scanner import Scanner
from lox.statement import ExpressionStmt, Stmt


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


def run(source: str) -> RunResult:
    """Corre el pipeline completo (scan -> parse -> resolve -> interpret) y captura stdout."""
    reporter = ErrorReporter()
    interpreter = Interpreter(reporter)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        statements = parse(source, reporter)
        if not reporter.had_error:
            Resolver(interpreter, reporter).resolve(statements)
        if not reporter.had_error:
            interpreter.interpret(statements)
    return RunResult(buffer.getvalue(), reporter)
