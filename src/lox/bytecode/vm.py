from __future__ import annotations
from typing import Any
from .chunk import Chunk, OpCode
from lox.frontend.errors import VMError
from .functions import CallFrame, Closure, Function, Upvalue
from .classes import BoundMethod, Class, Instance

# Limitacion de implementacion
FRAMES_MAX = 10_000


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
        # guarda los valores de las variables globales. Se resuelven en runtime (late-bound) porque el compilador no puede saber si una global va a existir cuando se ejecute esa linea.
        self.globals: dict[str, Any] = {}
        # upvalues que todavia apuntan a una variable viva del stack
        self.open_upvalues: dict[int, Upvalue] = {}

    # Devuelve el upvalue de la variable que esta en esa posicion del stack
    def capture_upvalue(self, index: int) -> Upvalue:
        upvalue = self.open_upvalues.get(index)
        if upvalue is None:
            upvalue = Upvalue(index)
            self.open_upvalues[index] = upvalue
        return upvalue

    # Cierra todos los upvalues abiertos de esa posicion del stack para arriba y los copia a closed
    def close_upvalues(self, last: int) -> None:
        for index in [i for i in self.open_upvalues if i >= last]:
            upvalue = self.open_upvalues.pop(index)
            upvalue.closed = self.stack[index]
            upvalue.is_open = False

    def execute(self, chunk: Chunk) -> None:
        stack = self.stack
        globals_ = self.globals
        # empezamos con stack vacia por si hay  un error en ejecucion anterior
        stack.clear()
        self.open_upvalues.clear()
        script = Function(None)
        script.chunk = chunk
        stack.append(Closure(script))
        frames = [CallFrame(stack[0], 0)]
        frame = frames[0]
        code, consts, base = chunk.code, chunk.consts, 0
        # instruction pointer, indice de proxima instruccion a ejecutar en code
        ip = 0

        def fail(msg: str) -> VMError:
            return VMError(frame.closure.function.chunk.lines[ip - 1], msg)

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

                # variables globales el operando es el indice en el pool donde esta el nombre de la variable
                # sacamos el valor del stack, tiene que derjarlo como estaba. 
                case OpCode.OP_DEFINE_GLOBAL:
                    name = consts[code[ip]]
                    ip += 1
                    globals_[name] = stack.pop()
                # busacamos el nombre en pool de constantes
                # luego buscamos en la tabla de globales de la VM
                # pusheamos su valor al stack
                case OpCode.OP_GET_GLOBAL:
                    name = consts[code[ip]]
                    ip += 1
                    if name not in globals_:
                        raise fail(f"Variable no definida '{name}'.")
                    stack.append(globals_[name])
                # asignar no saca el valor del stack, solo lo pisa en la tabla de globales. No hay pop porque es expresion. 
                case OpCode.OP_SET_GLOBAL:
                    name = consts[code[ip]]
                    ip += 1
                    if name not in globals_:
                        raise fail(f"Variable no definida '{name}'.")
                    globals_[name] = stack[-1]

                # variables locales, operando es la posicion exacta del valor de la variable en el stack, que ya calculo el compilador. 
                # Copia el valor de la variable local al tope del stack.
                # (con funciones base + slot)
                case OpCode.OP_GET_LOCAL:
                    stack.append(stack[base + code[ip]])
                    ip += 1
                # Pisa el indice del stack con el valor del tope. 
                case OpCode.OP_SET_LOCAL:
                    stack[base + code[ip]] = stack[-1]
                    ip += 1

                # Salta siempre. Lo usa el if para saltear el else, `or` para
                # saltear el lado derecho, y break/continue.
                case OpCode.OP_JUMP:
                    offset = (code[ip] << 8) | code[ip + 1]
                    ip += 2
                    ip += offset
                # Salta solo si el tope es falsey. Usa peek, NO pop: la condicion
                # sigue en el stack y cada camino la descarta con su propio POP.
                case OpCode.OP_JUMP_IF_FALSE:
                    offset = (code[ip] << 8) | code[ip + 1]
                    ip += 2
                    if not _truthy(stack[-1]):
                        ip += offset
                # Salto hacia atras: es lo que convierte una secuencia lineal de
                # bytes en un bucle. Resta en lugar de sumar.
                case OpCode.OP_LOOP:
                    offset = (code[ip] << 8) | code[ip + 1]
                    ip += 2
                    ip -= offset

                # ---- funciones y closures ----

                # Convierte la funcion del pool en un closure
                case OpCode.OP_CLOSURE:
                    function = consts[code[ip]]
                    ip += 1
                    closure = Closure(function)
                    for _ in range(function.upvalue_count):
                        is_local, index = code[ip], code[ip + 1]
                        ip += 2
                        if is_local:
                            closure.upvalues.append(self.capture_upvalue(base + index))
                        else:
                            closure.upvalues.append(frame.closure.upvalues[index])
                    stack.append(closure)

                case OpCode.OP_CALL:
                    argc = code[ip]
                    ip += 1
                    callee = stack[-1 - argc]
                    if isinstance(callee, BoundMethod):
                        stack[-1 - argc] = callee.receiver
                        callee = callee.method
                    elif isinstance(callee, Class):
                        stack[-1 - argc] = Instance(callee)
                        initializer = callee.methods.get("init")
                        if initializer is None:
                            if argc != 0:
                                raise fail(f"Se esperaban 0 argumentos pero se recibieron {argc}.")
                            continue
                        callee = initializer
                    elif not isinstance(callee, Closure):
                        raise fail("Solo se pueden invocar funciones y clases.")
                    if argc != callee.function.arity:
                        raise fail(f"Se esperaban {callee.function.arity} argumentos pero se recibieron {argc}.")
                    if len(frames) >= FRAMES_MAX:
                        raise fail("Desbordamiento de pila: demasiadas llamadas anidadas.")
                    frame.ip = ip
                    frame = CallFrame(callee, len(stack) - argc - 1)
                    frames.append(frame)
                    code = callee.function.chunk.code
                    consts = callee.function.chunk.consts
                    base = frame.base
                    ip = 0

                case OpCode.OP_GET_UPVALUE:
                    upvalue = frame.closure.upvalues[code[ip]]
                    ip += 1
                    stack.append(stack[upvalue.index] if upvalue.is_open else upvalue.closed)
                case OpCode.OP_SET_UPVALUE:
                    upvalue = frame.closure.upvalues[code[ip]]
                    ip += 1
                    if upvalue.is_open:
                        stack[upvalue.index] = stack[-1]
                    else:
                        upvalue.closed = stack[-1]

                case OpCode.OP_CLOSE_UPVALUE:
                    self.close_upvalues(len(stack) - 1)
                    stack.pop()

                # ---- clases ----

                case OpCode.OP_CLASS:
                    stack.append(Class(consts[code[ip]]))
                    ip += 1

                case OpCode.OP_INHERIT:
                    superclass = stack[-2]
                    if not isinstance(superclass, Class):
                        raise fail("La superclase debe ser una clase.")
                    stack.pop().methods.update(superclass.methods)

                # [clase, closure]: los metodos propios pisan a los heredados.
                case OpCode.OP_METHOD:
                    name = consts[code[ip]]
                    ip += 1
                    method = stack.pop()
                    stack[-1].methods[name] = method

                case OpCode.OP_GET_PROPERTY:
                    name = consts[code[ip]]
                    ip += 1
                    instance = stack[-1]
                    if not isinstance(instance, Instance):
                        raise fail("Solo las instancias tienen propiedades.")
                    if name in instance.fields:
                        stack[-1] = instance.fields[name]
                    elif name in instance.klass.methods:
                        stack[-1] = BoundMethod(instance, instance.klass.methods[name])
                    else:
                        raise fail(f"Propiedad no definida '{name}'.")

                case OpCode.OP_SET_PROPERTY:
                    name = consts[code[ip]]
                    ip += 1
                    value = stack.pop()
                    instance = stack[-1]
                    if not isinstance(instance, Instance):
                        raise fail("Solo las instancias tienen campos.")
                    instance.fields[name] = value
                    stack[-1] = value

                case OpCode.OP_GET_SUPER:
                    name = consts[code[ip]]
                    ip += 1
                    superclass = stack.pop()
                    method = superclass.methods.get(name)
                    if method is None:
                        raise fail(f"Propiedad no definida '{name}'.")
                    stack[-1] = BoundMethod(stack[-1], method)

                case OpCode.OP_DUP:
                    stack.append(stack[-1])

                case OpCode.OP_RETURN:
                    result = stack.pop()
                    self.close_upvalues(base)
                    frames.pop()
                    del stack[base:]
                    if not frames:
                        return
                    stack.append(result)
                    frame = frames[-1]
                    code = frame.closure.function.chunk.code
                    consts = frame.closure.function.chunk.consts
                    base = frame.base
                    ip = frame.ip
                case _:
                    raise fail(f"Opcode desconocido: {op}")