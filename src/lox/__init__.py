"""Punto de entrada de Lox."""

from __future__ import annotations

import sys
import readline
from .errors import ErrorReporter
from .scanner import Scanner
from .parser import Parser
from .interpreter import Interpreter
from .resolver import Resolver
from .statement import ExpressionStmt, Stmt

_STAGES = ("scanning", "parsing")


def _print_statement(stmt: Stmt) -> None:
    if isinstance(stmt, ExpressionStmt):
        print(stmt.expression)
    else:
        print(stmt)


def _run(source: str, reporter: ErrorReporter, interpreter: Interpreter, stage: str | None = None) -> None:
    tokens = Scanner(source, reporter).scan_tokens()
    if stage == "scanning":
        for token in tokens:
            print(token)
        return
    if reporter.had_error:
        return

    statements = Parser(tokens, reporter).parse()
    if stage == "parsing":
        for stmt in statements:
            _print_statement(stmt)
        return
    if reporter.had_error:
        return

    Resolver(interpreter, reporter).resolve(statements)
    if reporter.had_error:
        return
    interpreter.interpret(statements)


def _run_file(path: str, stage: str | None) -> int:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    reporter = ErrorReporter()
    interpreter = Interpreter(reporter)
    _run(source, reporter, interpreter, stage)
    if reporter.had_error:
        return 65
    if reporter.had_runtime_error:
        return 70
    return 0


def _run_prompt(stage: str | None) -> int:
    reporter = ErrorReporter()
    interpreter = Interpreter(reporter)
    while True:
        try:
            line = input("lox> ")
        except EOFError:
            print()
            break
        _run(line, reporter, interpreter, stage)
        reporter.reset()
    return 0


def _parse_args(args: list[str]) -> tuple[str | None, str | None]:
    """Separa la bandera de fase (--scanning/--parsing) del path del script."""
    stage: str | None = None
    script: str | None = None
    for arg in args:
        if arg.startswith("--"):
            name = arg[2:]
            if name not in _STAGES:
                print(f"Uso: lox [--scanning|--parsing] [script]")
                raise SystemExit(64)
            stage = name
        elif script is None:
            script = arg
        else:
            print("Uso: lox [--scanning|--parsing] [script]")
            raise SystemExit(64)
    return stage, script


def main() -> None:
    stage, script = _parse_args(sys.argv[1:])
    if script is not None:
        raise SystemExit(_run_file(script, stage))
    raise SystemExit(_run_prompt(stage))
