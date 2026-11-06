from __future__ import annotations

from typing import Any


# Mientras la variable sigue viva en el stack el upvalue esta ABIERTO y solo recuerda en que posicion del stack esta
# Antes de que esa variable salga del stack, la VM cierra el upvalue y copia el valor en closed. 
# asi el closure puede seguir usandolo aunque el stack ya no lo tenga.
class Upvalue:
    def __init__(self, index: int) -> None:
        self.index = index # posicion en el stack de la variable que esta capturando
        self.closed: Any = None
        self.is_open = True
