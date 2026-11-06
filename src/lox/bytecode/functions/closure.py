from __future__ import annotations

from .function import Function
from .upvalue import Upvalue


# una funcion mas las variables de afuera que capturo al crearse.
# Dos closures de la misma Function pueden tener upvalues distintos 
# Esto es lo que se guarda en el stack y en las variables, y llamamos con OP_CALL. La VM crea un CallFrame con la Function y los Upvalues de este Closure.
class Closure:
    def __init__(self, function: Function) -> None:
        self.function = function
        self.upvalues: list[Upvalue] = []

    def __str__(self) -> str:
        return str(self.function)
