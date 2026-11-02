from __future__ import annotations
from .op_code import OpCode
from typing import Any


# instrucciones que tienen un operando (un indice al pool de constantes)
WITH_CONST_OPERAND = {
    OpCode.OP_CONSTANT,
    # en globales guardamos indice al nombre de la variable
    OpCode.OP_DEFINE_GLOBAL,
    OpCode.OP_GET_GLOBAL,
    OpCode.OP_SET_GLOBAL,
}

# posiciones en el stack del valor de las variables locales
WITH_SLOT_OPERAND = {       
    OpCode.OP_GET_LOCAL,
    OpCode.OP_SET_LOCAL,
}
# un offset (cuantos bytes mover el ip)
WITH_JUMP_OPERAND = {           
    OpCode.OP_JUMP,
    OpCode.OP_JUMP_IF_FALSE,
    OpCode.OP_LOOP,
}

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
                print(f"{i:04d}  {op.name:<16} {idx}  ({self.consts[idx]!r})")
                i += 2 # salta dos bytes, el opcode y su operando
            elif op in WITH_SLOT_OPERAND:
                print(f"{i:04d}  {op.name:<16} @{self.code[i + 1]}")
                i += 2
            elif op in WITH_JUMP_OPERAND:
                offset = (self.code[i + 1] << 8) | self.code[i + 2]
                target = i + 3 - offset if op == OpCode.OP_LOOP else i + 3 + offset
                print(f"{i:04d}  {op.name:<16} -> {target:04d}")
                i += 3  #salta el opcode y 2 bytes de operando
            else:
                print(f"{i:04d}  {op.name}")
                i += 1
        print(f"consts: {self.consts}")