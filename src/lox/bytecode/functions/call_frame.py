from __future__ import annotations

from .closure import Closure


# Ventana de ejecucion de una funcion
# Guarda que closure se esta ejecutando, por donde va (ip propio) y donde empieza su ventana (base)
class CallFrame:
    __slots__ = ("closure", "ip", "base")

    def __init__(self, closure: Closure, base: int) -> None:
        self.closure = closure
        self.ip = 0
        self.base = base
