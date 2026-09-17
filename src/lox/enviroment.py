from __future__ import annotations
from typing import Any
from lox.tokens import Token
from lox.errors import LoxRuntimeError


class Environment:
    def __init__(self, enclosing: Environment | None = None) -> None:
        self.values: dict[str, Any] = {}
        self.enclosing = enclosing  #env padre

    def define(self, name: str, value: Any) -> None:
        """Crea o actualiza una variable en el scope actual."""
        self.values[name] = value

    def get(self, name: Token) -> Any:
        """Busca una variable desde el scope actual hacia los padres."""
        curr = self
        while curr is not None:
            if name.lexeme in curr.values:
                return curr.values[name.lexeme]
            curr = curr.enclosing
        raise LoxRuntimeError(name, f"Variable no definida '{name.lexeme}'.")
        
    def assign(self, name: Token, value: Any) -> None:
        """Reasigna el valor de una variable existente recorriendo hacia arriba los enviroments."""
        curr = self
        while curr is not None:
            if name.lexeme in curr.values:
                curr.values[name.lexeme] = value
                return
            curr = curr.enclosing
        raise LoxRuntimeError(name, f"Variable no definida '{name.lexeme}'.")
