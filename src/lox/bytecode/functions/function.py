from __future__ import annotations

from lox.bytecode.chunk import Chunk


# Una funcion tiene su propio Chunk
# Se guarda en el POOL de constantes del chunk que la declara.
class Function:
    def __init__(self, name: str | None) -> None:
        self.name = name
        self.arity = 0   # cantidad de parametros
        self.upvalue_count = 0 # cuantas variables de afuera captura
        self.chunk = Chunk()

    def __str__(self) -> str:
        return "<script>" if self.name is None else f"<fn {self.name}>"

    __repr__ = __str__
