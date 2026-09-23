"""Señales de control de flujo que viajan como excepciones pero no son errores."""

from __future__ import annotations

from typing import Any


class ReturnSignal(Exception):
    """Se lanza al ejecutar un `return` para cortar el cuerpo de la funcion y burbujear el valor."""

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value
