"""Punto de entrada de Lox. Por ahora solo expone el scanner."""

from __future__ import annotations

import sys

from .errors import ErrorReporter
from .scanner import Scanner
from .parser import Parser
from .interpreter import Interpreter
from .resolver import Resolver


def _run(source: str, reporter: ErrorReporter, interpreter: Interpreter) -> None:
    tokens = Scanner(source, reporter).scan_tokens()
    if reporter.had_error:
        return
    statements = Parser(tokens, reporter).parse()
    if reporter.had_error:
        return
    Resolver(interpreter, reporter).resolve(statements)
    if reporter.had_error:
        return
    interpreter.interpret(statements)


def _run_file(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    reporter = ErrorReporter()
    interpreter = Interpreter(reporter)
    _run(source, reporter, interpreter)
    if reporter.had_error:
        return 65
    if reporter.had_runtime_error:
        return 70
    return 0


def _run_prompt() -> int:
    reporter = ErrorReporter()
    interpreter = Interpreter(reporter)  # <-- Se crea una sola vez para toda la sesión
    while True:
        try:
            line = input("lox> ")
        except EOFError:
            print()
            break
        _run(line, reporter, interpreter)
        reporter.reset()  # un error no debe matar la sesion interactiva
    return 0


def main() -> None:
    args = sys.argv[1:]
    if len(args) > 1:
        print("Uso: lox [script]")
        raise SystemExit(64)
    if len(args) == 1:
        raise SystemExit(_run_file(args[0]))
    raise SystemExit(_run_prompt())
