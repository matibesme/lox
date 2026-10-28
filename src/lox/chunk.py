from __future__ import annotations
from .op_code import OpCode
from typing import Any


# instrucciones que tienen un operando (un indice al pool de constantes)
WITH_CONST_OPERAND = {OpCode.OP_CONSTANT}


class Chunk:
    """Representacion intermedia en bytecode: instrucciones + pool de constantes."""
    def __init__(self) -> None:
        # tira de bytes(o opcode o indice de constante)
        self.code = bytearray()

        # Pool de constantes
        self.consts: list[Any] = []

        # para cada byte de code, la linea de Lox de donde vino.
        self.lines: list[int] = [] 

    # Agrega un byte al final y guarda la linea donde se genero
    def write(self, byte: int, line: int) -> None:
        self.code.append(byte)
        self.lines.append(line)

    # Guarda en el pool y devuelve su indice(para que el opcode pueda referenciarlo)
    def add_const(self, value: Any) -> int:
        self.consts.append(value)
        return len(self.consts) - 1

    # pasa tira de bytes a texto para debuggear
    def disassemble(self) -> None:
        i = 0
        while i < len(self.code):
            op = OpCode(self.code[i])
            if op in WITH_CONST_OPERAND:
                idx = self.code[i + 1]
                print(f"{i:04d}  {op.name:<12} {idx}  ({self.consts[idx]!r})")
                i += 2 # salta dos bytes, el opcode y su operando
            else:
                print(f"{i:04d}  {op.name}")
                i += 1
        print(f"consts: {self.consts}")