from enum import IntEnum, auto

class OpCode(IntEnum):
  
    OP_CONSTANT = auto()

    # pushean directo el valor al stack.
    OP_NIL = auto()
    OP_TRUE = auto()
    OP_FALSE = auto()

    # Unarias: sacan 1 valor del stack y dejan 1 (efecto  0).
    OP_NEGATE = auto()
    OP_NOT = auto()

    # Binarias: sacan 2 valores y dejan 1 (efecto  -1).
    OP_ADD = auto()
    OP_SUBTRACT = auto()
    OP_MULTIPLY = auto()
    OP_DIVIDE = auto()
    OP_MODULO = auto()
    OP_EQUAL = auto()
    OP_GREATER = auto()
    OP_LESS = auto()

    #globales con indice al pool de constantes donde esta el nombre de la variable.
    OP_DEFINE_GLOBAL = auto()  #efecto -1, pop del valor -> globals[nombre] 
    OP_GET_GLOBAL = auto()     #efecto +1, push de globals[nombre] 
    OP_SET_GLOBAL = auto()    #efecto 0, peek del valor y lo pisa en globals[nombre]

    # locales con indice al stack donde esta el valor de la variable.
    OP_GET_LOCAL = auto()      #efecto +1, push de stack[slot]
    OP_SET_LOCAL = auto()     #efecto 0, peek del tope y lo pisa en stack[slot]

   # saltos: el operando es un offset (cuantos bytes mover el ip)
    OP_JUMP = auto() # efecto 0, salta incondicionalmente
    OP_JUMP_IF_FALSE = auto()  # efecto 0, si el tope es falsey, salta
    OP_LOOP = auto()        # efecto 0, salta hacia atras (para bucles)

    OP_PRINT = auto()   # saca el tope y lo muestra (efecto -1)
    OP_POP = auto()     # descarta el tope: es el ';' de un expression statement
    OP_RETURN = auto()  # fin del programa