from __future__ import annotations
from typing import Any
from lox.chunk import Chunk, OpCode
from lox.errors import VMError


# Respetamos contrato del lenguaje
def show(value: Any) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        text = str(value)
        return text[:-2] if text.endswith(".0") else text
    return str(value)


def _truthy(value: Any) -> bool:
    return not (value is None or value is False)


class VM:
    def __init__(self) -> None:
        # pila de operandos
        self.stack: list[Any] = []

    def execute(self, chunk: Chunk) -> None:
        code, consts, stack = chunk.code, chunk.consts, self.stack
        # instruction pointer, indice de proxima instruccion a ejecutar en code
        ip = 0

        def fail(msg: str) -> VMError:
            return VMError(chunk.lines[ip - 1], msg)

        # el compilador no sabe si los operandos son numeros o strings, entonces chequeamos en tiempo de ejecucion.
        def numbers(a: Any, b: Any) -> None:
            if not (isinstance(a, float) and isinstance(b, float)):
                raise fail("Los operandos deben ser dos numeros.")

        # leer un opcode y decidir que es, ejecutarlo. Termina con OP_RETURN.
        while True:
            op = code[ip]
            ip += 1
            match op:
                # busca la constante en el pool y la pushea. 
                case OpCode.OP_CONSTANT:
                    stack.append(consts[code[ip]])
                    ip += 1

                case OpCode.OP_NIL:
                    stack.append(None)
                case OpCode.OP_TRUE:
                    stack.append(True)
                case OpCode.OP_FALSE:
                    stack.append(False)

                # unarias miran el tope, lo reemplazan con resultado
                case OpCode.OP_NEGATE:
                    if not isinstance(stack[-1], float):
                        raise fail("El operando debe ser un numero.")
                    stack.append(-stack.pop())
                case OpCode.OP_NOT:
                    stack.append(not _truthy(stack.pop()))

                # binarias el ORDEN de los pop es al reves del push.
                # El compiador pusheo a y despues b, entonces b esta arriba. Sacamos b y despues a, y hacemos `a op b`.
                case OpCode.OP_ADD:
                    b, a = stack.pop(), stack.pop()
                    if (isinstance(a, float) and isinstance(b, float)) or (
                        isinstance(a, str) and isinstance(b, str)
                    ):
                        stack.append(a + b)
                    else:
                        raise fail("Los operandos deben ser dos numeros o dos cadenas de texto.")
                case OpCode.OP_SUBTRACT:
                    b, a = stack.pop(), stack.pop()
                    numbers(a, b)
                    stack.append(a - b)
                case OpCode.OP_MULTIPLY:
                    b, a = stack.pop(), stack.pop()
                    numbers(a, b)
                    stack.append(a * b)
                case OpCode.OP_DIVIDE:
                    b, a = stack.pop(), stack.pop()
                    numbers(a, b)
                    if b == 0:
                        raise fail("Division por cero.")
                    stack.append(a / b)
                case OpCode.OP_MODULO:
                    b, a = stack.pop(), stack.pop()
                    numbers(a, b)
                    if b == 0:
                        raise fail("Modulo por cero.")
                    stack.append(float(int(a) % int(b)))

                # las comparaciones dejan un booleano en el stack. 
                case OpCode.OP_EQUAL:
                    b, a = stack.pop(), stack.pop()
                    stack.append(a == b)
                case OpCode.OP_GREATER:
                    b, a = stack.pop(), stack.pop()
                    numbers(a, b)
                    stack.append(a > b)
                case OpCode.OP_LESS:
                    b, a = stack.pop(), stack.pop()
                    numbers(a, b)
                    stack.append(a < b)

                # print consume el valor (no hacemos pop despues)
                case OpCode.OP_PRINT:
                    print(show(stack.pop()))

                case OpCode.OP_POP:
                    stack.pop()

                case OpCode.OP_RETURN:
                    return
                case _:
                    raise fail(f"Opcode desconocido: {op}")