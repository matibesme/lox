from enum import IntEnum, auto

class OpCode(IntEnum):
  
    OP_CONSTANT = auto()

    # pushean directo el valor al stack.
    OP_NIL = auto()
    OP_TRUE = auto()
    OP_FALSE = auto()

    # Unarias: sacan 1 valor del stack y dejan 1 (efecto neto 0).
    OP_NEGATE = auto()
    OP_NOT = auto()

    # Binarias: sacan 2 valores y dejan 1 (efecto neto -1).
    OP_ADD = auto()
    OP_SUBTRACT = auto()
    OP_MULTIPLY = auto()
    OP_DIVIDE = auto()
    OP_MODULO = auto()
    OP_EQUAL = auto()
    OP_GREATER = auto()
    OP_LESS = auto()
    # No hay OP_GREATER_EQUAL / OP_LESS_EQUAL / OP_NOT_EQUAL: el compilador los
    # arma combinando los de arriba con OP_NOT (ver _BINARY_OPS en compiler.py).

    OP_PRINT = auto()   # saca el tope y lo muestra (efecto -1)
    OP_POP = auto()     # descarta el tope: es el ';' de un expression statement
    OP_RETURN = auto()  # fin del programa