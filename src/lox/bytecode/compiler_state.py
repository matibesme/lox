from dataclasses import dataclass

#La clase local es una variable local que el compilador necesita recordar para poder compilar correctamente las variables locales.
@dataclass
class Local:
    name: str
    # saber que locales hay que descartar cuando un bloque se cierra (end_scope) y para saber si una local esta inicializada antes de usarla.
    depth: int
    # True si alguna funcion anidada usa esta variable (la "captura"). Entonces al cerrar el bloque no alcanza con
    # descartarla con un OP_POP: hay que emitir OP_CLOSE_UPVALUE para que el closure no pierda el valor.
    is_captured: bool = False


# Permite referenciar a un upvalue de una funcion externa
@dataclass
class UpvalueRef:
    # si es local de la funcion externa, el indice es el slot de esa local en el stack
    # IS LOCAL = False # es el indice del upvalue de la funcion externa
    index: int
    is_local: bool


# para poder compilar los break y continue, el compilador necesita recordar donde se declaro el bucle y que locales habia en ese momento.
@dataclass
class Loop:
    # Cuantas locales habia justo antes de entrar al cuerpo.
    locals_at_entry: int
    #estas listas guardan para cada break y continue que se compile, el offset del jump que hay que parchear cuando se termina el bucle
    break_jumps: list[int]
    continue_jumps: list[int]
