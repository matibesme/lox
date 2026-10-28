from dataclasses import dataclass

#La clase local es una variable local que el compilador necesita recordar para poder compilar correctamente las variables locales.
@dataclass
class Local:
    name: str
    # saber que locales hay que descartar cuando un bloque se cierra (end_scope) y para saber si una local esta inicializada antes de usarla.
    depth: int


# para poder compilar los break y continue, el compilador necesita recordar donde se declaro el bucle y que locales habia en ese momento.
@dataclass
class Loop:
    # Cuantas locales habia justo antes de entrar al cuerpo.
    locals_at_entry: int
    #estas listas guardan para cada break y continue que se compile, el offset del jump que hay que parchear cuando se termina el bucle
    break_jumps: list[int]
    continue_jumps: list[int]
