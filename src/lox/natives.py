"""Funciones nativas que el interprete expone en el entorno global."""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from lox.callable import LoxCallable

if TYPE_CHECKING:
    from lox.interpreter import Interpreter


class ClockNative(LoxCallable):
    """Devuelve los segundos transcurridos desde epoch, util para benchmarks."""

    def arity(self) -> int:
        return 0

    def call(self, interpreter: "Interpreter", arguments: list[Any]) -> Any:
        return time.time()

    def __str__(self) -> str:
        return "<native fn>"
