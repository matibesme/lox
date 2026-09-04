"""Punto de entrada de Lox. Por ahora solo expone el scanner."""

from __future__ import annotations

import sys

from .errors import ErrorReporter
from .scanner import Scanner
from .parser import Parser


def _run(source: str, reporter: ErrorReporter) -> None:
    tokens = Scanner(source, reporter).scan_tokens()
    expr = Parser(tokens, reporter).parse()

    print(expr)


def _run_file(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    reporter = ErrorReporter()
    _run(source, reporter)
    if reporter.had_error:
        return 65
    return 0


def _run_prompt() -> int:
    reporter = ErrorReporter()
    while True:
        try:
            line = input("lox> ")
        except EOFError:
            print()
            break
        _run(line, reporter)
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
