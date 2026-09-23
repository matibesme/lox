"""Representacion en runtime de las funciones declaradas por el usuario."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from lox.callable import LoxCallable
from lox.enviroment import Environment
from lox.signals import ReturnSignal
from lox.statement import FunctionStmt

if TYPE_CHECKING:
    from lox.interpreter import Interpreter


class LoxFunction(LoxCallable):
    """Une la declaracion parseada con el entorno donde fue declarada (su closure)."""

    def __init__(self, declaration: FunctionStmt, closure: Environment) -> None:
        self.declaration = declaration
        self.closure = closure

    def arity(self) -> int:
        return len(self.declaration.params)

    def call(self, interpreter: "Interpreter", arguments: list[Any]) -> Any:
        environment = Environment(enclosing=self.closure)
        for param, argument in zip(self.declaration.params, arguments):
            environment.define(param.lexeme, argument)

        try:
            interpreter.run_block(self.declaration.body, environment)
        except ReturnSignal as signal:
            return signal.value
        return None

    def __str__(self) -> str:
        return f"<fn {self.declaration.name.lexeme}>"
