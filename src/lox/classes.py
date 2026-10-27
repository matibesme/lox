"""Representacion en runtime de las clases y sus instancias."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from lox.callable import LoxCallable
from lox.errors import LoxRuntimeError
from lox.functions import LoxFunction
from lox.tokens import Token

if TYPE_CHECKING:
    from lox.interpreter import Interpreter


class LoxClass(LoxCallable):
    """Una clase es invocable: llamarla crea una instancia y corre su `init`."""

    def __init__(self, name: str, superclass: LoxClass | None, methods: dict[str, LoxFunction]) -> None:
        self.name = name
        self.superclass = superclass
        self.methods = methods

    def find_method(self, name: str) -> LoxFunction | None:
        """Busca el metodo en la clase y, si no esta, sube por la cadena de herencia."""
        klass: LoxClass | None = self
        while klass is not None:
            if name in klass.methods:
                return klass.methods[name]
            klass = klass.superclass
        return None

    def arity(self) -> int:
        initializer = self.find_method("init")
        return 0 if initializer is None else initializer.arity()

    def call(self, interpreter: "Interpreter", arguments: list[Any]) -> Any:
        instance = LoxInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        return instance

    def __str__(self) -> str:
        return self.name


class LoxInstance:
    """Objeto creado a partir de una clase. Guarda sus propios campos."""

    def __init__(self, klass: LoxClass) -> None:
        self.klass = klass
        self.fields: dict[str, Any] = {}

    def get(self, name: Token) -> Any:

        if name.lexeme in self.fields:
            return self.fields[name.lexeme]
        method = self.klass.find_method(name.lexeme)
        if method is not None:
            return method.bind(self)
        raise LoxRuntimeError(name, f"Propiedad no definida '{name.lexeme}'.")

    def set(self, name: Token, value: Any) -> None:
        self.fields[name.lexeme] = value

    def __str__(self) -> str:
        return f"{self.klass.name} instance"
