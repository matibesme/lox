"""Interfaz comun para todo lo que se puede invocar con `(...)` en Lox."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from lox.interpreter import Interpreter


class LoxCallable(ABC):
    @abstractmethod
    def arity(self) -> int:
        """Cantidad de argumentos que espera recibir."""

    @abstractmethod
    def call(self, interpreter: "Interpreter", arguments: list[Any]) -> Any:
        """Ejecuta la invocacion con los argumentos ya evaluados."""
