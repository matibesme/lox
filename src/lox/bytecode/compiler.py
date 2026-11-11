from __future__ import annotations
from functools import singledispatchmethod
from .chunk import Chunk, OpCode
from lox.frontend.errors import CompileError
from lox.frontend.expr import (
    AssignExpr, BinaryExpr, CallExpr, Expr, GetExpr, GroupingExpr, LiteralExpr, LogicalExpr,
    SetExpr, SuperExpr, ThisExpr, UnaryExpr, VariableExpr,
)
from lox.frontend.statement import (
    BlockStmt, BreakStmt, ClassStmt, ContinueStmt, ExpressionStmt, FunctionStmt, IfStmt, PrintStmt,
    ReturnStmt, Stmt, VarStmt, WhileStmt,
)
from lox.frontend.tokens import Token, TokenKind
from .compiler_state import ClassInfo, Local, Loop, UpvalueRef
from .functions.function import Function

#Dejamos como tupla de opcodes para hacer desugaring de operadores 
_BINARY_OPS: dict[TokenKind, tuple[OpCode, ...]] = {
    TokenKind.PLUS: (OpCode.OP_ADD,),
    TokenKind.MINUS: (OpCode.OP_SUBTRACT,),
    TokenKind.STAR: (OpCode.OP_MULTIPLY,),
    TokenKind.SLASH: (OpCode.OP_DIVIDE,),
    TokenKind.PERCENT: (OpCode.OP_MODULO,),
    TokenKind.EQUAL_EQUAL: (OpCode.OP_EQUAL,),
    TokenKind.BANG_EQUAL: (OpCode.OP_EQUAL, OpCode.OP_NOT),
    TokenKind.GREATER: (OpCode.OP_GREATER,),
    TokenKind.GREATER_EQUAL: (OpCode.OP_LESS, OpCode.OP_NOT),
    TokenKind.LESS: (OpCode.OP_LESS,),
    TokenKind.LESS_EQUAL: (OpCode.OP_GREATER, OpCode.OP_NOT),
}

# Tipos de funcion que se pueden estar compilando. Cambian que hay en el slot 0
# y que devuelve la funcion al terminar.
SCRIPT = "script"
FUNCTION = "function"
METHOD = "method"
INITIALIZER = "initializer"

# stack effect
#   -  las expresiones dejan exactamente 1 valor en el stack  
#   -   todo STATEMENT deja el stack como estaba   

class BytecodeCompiler:
    #Recorre el AST (post-order, primero compilando hijos para que las operaciones tengan sus operandos en el stack.) 
    # y emite bytecode en formato lineal.
    def __init__(
        self, enclosing: BytecodeCompiler | None = None, function: Function | None = None, kind: str = SCRIPT
    ) -> None:
        
        self.enclosing = enclosing
        self.kind = kind
        # si estamos en main es una funcion mas con none
        self.function = function if function is not None else Function(None)
        self.chunk = self.function.chunk
        self.line = 1
        # simula el stack de la VM con cant de variables locales y su orden
        self.locals: list[Local] = []
        # El slot 0 lo ocupa el callee. En los metodos es la instancia, asi que lo
        # nombramos `this` y leerlo es un OP_GET_LOCAL 0 como cualquier otra local.
        self.locals.append(Local("this" if kind in (METHOD, INITIALIZER) else "", 0))
        # profundidad de bloque vemos si es local o global
        self.scope_depth = 0
        # lista de bucles abiertos para poder compilar break/continue
        self.loops: list[Loop] = []
        # nombre de global -> indice en el pool
        self.name_consts: dict[str, int] = {}
        # lista de upvalues de la funcion
        self.upvalues: list[UpvalueRef] = []
        # clases que se estan compilando (compartida con los compiladores de funciones anidadas)
        self.classes: list[ClassInfo] = enclosing.classes if enclosing is not None else []

    
    def compile(self, statements: list[Stmt]) -> Chunk:
        for stmt in statements:
            self.gen_stmt(stmt)

        # op return al final del programa para que la VM sepa que termino.
        self.emit(OpCode.OP_NIL)
        self.emit(OpCode.OP_RETURN)
        return self.chunk

    # escribe operandos en el chunk 
    def emit(self, *ops: int) -> None:
        for op in ops:
            self.chunk.write(op, self.line)


    # guarda constante en el pool y emite OP_CONSTANT con indice
    def emit_const(self, value: object) -> None:
        idx = self.chunk.add_const(value)
        # maximo 256 constantes por chunk (1 byte de operando)
        if idx > 255:
            raise CompileError(self.line, "Demasiadas constantes en un chunk.")
        self.emit(OpCode.OP_CONSTANT, idx)

    # Los nombres de variables globales se guardan en el pool.
    # devuelve indice en el pool del nombre de una variable global.
    def name_const(self, name: str) -> int:
        if name not in self.name_consts:
            idx = self.chunk.add_const(name)
            if idx > 255:
                raise CompileError(self.line, "Demasiadas constantes en un chunk.")
            self.name_consts[name] = idx
        return self.name_consts[name]

    
    #   1. emit_jump escribir salto sin saber a donde.
    #   2. se compila el cuerpo normalmente.
    #   3. patch_jump ahora que se sabe donde hay que saltar, se reemplaza el operando del salto con la distancia correcta.

    # Devuelve la posicion del primer byte del operando 
    def emit_jump(self, op: OpCode) -> int:
        self.emit(op, 0xFF, 0xFF)
        return len(self.chunk.code) - 2


    # offset = (donde cae el salto) - (final de la instruccion de salto)
    def patch_jump(self, at: int) -> None:
        offset = len(self.chunk.code) - at - 2
        if offset > 0xFFFF:
            raise CompileError(self.line, "El salto es demasiado largo.")
  
        self.chunk.code[at] = (offset >> 8) & 0xFF
        self.chunk.code[at + 1] = offset & 0xFF

   
    def emit_loop(self, loop_start: int) -> None:
        offset = len(self.chunk.code) - loop_start + 3
        if offset > 0xFFFF:
            raise CompileError(self.line, "El cuerpo del bucle es demasiado largo.")
        self.emit(OpCode.OP_LOOP, (offset >> 8) & 0xFF, offset & 0xFF)

    # locales
    def begin_scope(self) -> None:
        self.scope_depth += 1

    # Al cerrar un bloque hay que descartar todas las locales que se declararon dentro de ese bloque.
    # para eso emitimos un OP_POP por cada local que se descarta hasta que la profundidad de bloque sea la misma que antes de abrir el bloque.
    def end_scope(self) -> None:
        self.scope_depth -= 1
        while self.locals and self.locals[-1].depth > self.scope_depth:
            # guardamos en upvalue si alguna funcion uso esta varible
            if self.locals[-1].is_captured:
                self.emit(OpCode.OP_CLOSE_UPVALUE)
            else:
                self.emit(OpCode.OP_POP)
            self.locals.pop()

    # guarda una variable local en el stack simulado
    def declare_local(self, name: Token) -> None:
    
        #verificamos que no haya otra variable con el mismo nombre en el mismo scope 
        for local in reversed(self.locals):
            if local.depth != -1 and local.depth < self.scope_depth:
                break
            if local.name == name.lexeme:
                raise CompileError(name.line, "Ya existe una variable con este nombre en este scope.")
        if len(self.locals) >= 256:
            raise CompileError(name.line, "Demasiadas variables locales.")
        self.locals.append(Local(name.lexeme, -1))

   # Devuelve el SLOT de la variable local en el stack simulado, o -1 si no es local
   # recorre de atras hacia adelante porque nos interesan las mas internas.
    def resolve_local(self, name: Token) -> int:
        for slot in range(len(self.locals) - 1, -1, -1):
            local = self.locals[slot]
            if local.name == name.lexeme:
                if local.depth == -1:
                    raise CompileError(name.line, "No se puede leer una variable local en su propio inicializador.")
                return slot
        return -1

    # Busca el nombre en las funciones de afuera (variables que no son locales de esta funcion pero tampoco globales)
    # Devuelve el indice del upvalue en self.upvalues, o -1 si no esta en ninguna(ahi seria global)
    def resolve_upvalue(self, name: Token) -> int:
        if self.enclosing is None:
            return -1
        slot = self.enclosing.resolve_local(name)
        if slot != -1:
            # si la encontramos, la marcamos como capturada
            self.enclosing.locals[slot].is_captured = True
            return self.add_upvalue(slot, True)
        # si esta mas afuera todavia, es un upvalue de la funcion contenedora
        upvalue = self.enclosing.resolve_upvalue(name)
        if upvalue != -1:
            return self.add_upvalue(upvalue, False)
        return -1

    # Registra un upvalue y devuelve su indice. Si ya lo habiamos registrado, reutiliza el indice
    def add_upvalue(self, index: int, is_local: bool) -> int:
        for i, existing in enumerate(self.upvalues):
            if existing.index == index and existing.is_local == is_local:
                return i
        if len(self.upvalues) >= 256:
            raise CompileError(self.line, "Demasiadas variables capturadas en una funcion.")
        self.upvalues.append(UpvalueRef(index, is_local))
        return len(self.upvalues) - 1

    # escriben operando para leer o escribir una variable local, upvalue o global
    # busqueda primero lo propio, despues lo de funciones de afuera, al final globales.
    def emit_get(self, name: Token) -> None:
        slot = self.resolve_local(name)
        if slot != -1:
            self.emit(OpCode.OP_GET_LOCAL, slot)
        else:
            upvalue = self.resolve_upvalue(name)
            if upvalue != -1:
                self.emit(OpCode.OP_GET_UPVALUE, upvalue)
            else:
                self.emit(OpCode.OP_GET_GLOBAL, self.name_const(name.lexeme))

    def emit_set(self, name: Token) -> None:
        slot = self.resolve_local(name)
        if slot != -1:
            self.emit(OpCode.OP_SET_LOCAL, slot)
        else:
            upvalue = self.resolve_upvalue(name)
            if upvalue != -1:
                self.emit(OpCode.OP_SET_UPVALUE, upvalue)
            else:
                self.emit(OpCode.OP_SET_GLOBAL, self.name_const(name.lexeme))

  # Cuando se sale de un bucle, hay que descartar todas las locales que se declararon dentro del bucle.
    def leave_loop_scope(self, keyword: Token, name: str) -> Loop:
        self.line = keyword.line
        if not self.loops:
            raise CompileError(keyword.line, f"No se puede usar '{name}' fuera de un bucle.")
        loop = self.loops[-1]
        # Cerramos upvalues de las locales que se descartan, o hacemos OP_POP si no son capturadas.
        for local in reversed(self.locals[loop.locals_at_entry:]):
            self.emit(OpCode.OP_CLOSE_UPVALUE if local.is_captured else OpCode.OP_POP)
        return loop

    # compila en un chunk nuevo y al terminar se vuelve a este compilador
    def compile_function(self, stmt: FunctionStmt, kind: str = FUNCTION) -> None:
        function = Function(stmt.name.lexeme)
        function.arity = len(stmt.params)
        sub = BytecodeCompiler(enclosing=self, function=function, kind=kind)
        sub.line = stmt.name.line
        sub.begin_scope()
        for param in stmt.params:
            sub.declare_local(param)
            sub.locals[-1].depth = sub.scope_depth
        for inner in stmt.body:
            sub.gen_stmt(inner)
        sub.emit_implicit_return()
        function.upvalue_count = len(sub.upvalues)

        idx = self.chunk.add_const(function)
        if idx > 255:
            raise CompileError(self.line, "Demasiadas constantes en un chunk.")
        self.emit(OpCode.OP_CLOSURE, idx)
    
        for upvalue in sub.upvalues:
            self.emit(1 if upvalue.is_local else 0, upvalue.index)

    # Un init siempre devuelve la instancia (slot 0); el resto de las funciones, nil.
    def emit_implicit_return(self) -> None:
        if self.kind == INITIALIZER:
            self.emit(OpCode.OP_GET_LOCAL, 0)
        else:
            self.emit(OpCode.OP_NIL)
        self.emit(OpCode.OP_RETURN)

    # statements deja el stack como estaba
    @singledispatchmethod
    def gen_stmt(self, stmt: Stmt) -> None:
        raise CompileError(self.line, f"Todavia no soportado: {type(stmt).__name__}")

    # la expresion deja un valor en el stack y con el OP_POP lo sacamos para dejar el stack como estaba
    @gen_stmt.register
    def _(self, stmt: ExpressionStmt) -> None:
        self.gen_expr(stmt.expression)
        self.emit(OpCode.OP_POP)

    # OP_PRINT consume el valor no hace falta el pop
    @gen_stmt.register
    def _(self, stmt: PrintStmt) -> None:
        self.gen_expr(stmt.expression)
        self.emit(OpCode.OP_PRINT)

 
    @gen_stmt.register
    def _(self, stmt: VarStmt) -> None:
        self.line = stmt.name.line
        is_local = self.scope_depth > 0
        if is_local:
            # Se declara antes de inicializar para poder usarla en su propio inicializador (var x = x + 1;)
            self.declare_local(stmt.name)
        if stmt.initializer is not None:
            self.gen_expr(stmt.initializer)
        else:
            self.emit(OpCode.OP_NIL)  # `var x;` vale nil
        if is_local:
            # Ahora si: el inicializador termino, la variable ya se puede leer.
            self.locals[-1].depth = self.scope_depth
        else:
            self.emit(OpCode.OP_DEFINE_GLOBAL, self.name_const(stmt.name.lexeme))


    @gen_stmt.register
    def _(self, stmt: BlockStmt) -> None:
        self.begin_scope()
        for inner in stmt.statements:
            self.gen_stmt(inner)
        self.end_scope()


    @gen_stmt.register
    def _(self, stmt: IfStmt) -> None:
        self.gen_expr(stmt.condition)
        then_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE)
        self.emit(OpCode.OP_POP)
        self.gen_stmt(stmt.then_branch)
        else_jump = self.emit_jump(OpCode.OP_JUMP)
        # Aca empieza el else: es el destino del salto condicional de arriba.
        self.patch_jump(then_jump)
        self.emit(OpCode.OP_POP)
        if stmt.else_branch is not None:
            self.gen_stmt(stmt.else_branch)
        # Y aca termina todo: destino del JUMP que saltea el else.
        self.patch_jump(else_jump)

   
    @gen_stmt.register
    def _(self, stmt: WhileStmt) -> None:
        # Posicion actual = donde empieza la condicion = destino de OP_LOOP.
        loop_start = len(self.chunk.code)
        self.gen_expr(stmt.condition)
        exit_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE)
        self.emit(OpCode.OP_POP)

        # boocle actual para poder compilar break/continue. Se guarda cuantas locales habia antes de entrar al bucle.
        loop = Loop(len(self.locals), [], [])
        self.loops.append(loop)
        self.gen_stmt(stmt.body)
        self.loops.pop()

        for jump in loop.continue_jumps:
            self.patch_jump(jump)
        if stmt.increment is not None:
            self.gen_expr(stmt.increment)
            self.emit(OpCode.OP_POP)  # el incremento es una expresion: hay que descartar su valor
        self.emit_loop(loop_start)

        self.patch_jump(exit_jump)
        self.emit(OpCode.OP_POP)
        for jump in loop.break_jumps:
            self.patch_jump(jump)

    # break; no tiene instruccion propia: es un OP_JUMP hacia adelante al final
    # del bucle. Como todavia no se sabe donde termina, queda sin parchear y se
    # anota en el Loop; el while lo parchea cuando termina de compilarse.
    @gen_stmt.register
    def _(self, stmt: BreakStmt) -> None:
        loop = self.leave_loop_scope(stmt.keyword, "break")
        loop.break_jumps.append(self.emit_jump(OpCode.OP_JUMP))

    # continue; igual que break, pero el destino es el incremento (o el final del
    # cuerpo si no hay), no la salida del bucle.
    @gen_stmt.register
    def _(self, stmt: ContinueStmt) -> None:
        loop = self.leave_loop_scope(stmt.keyword, "continue")
        loop.continue_jumps.append(self.emit_jump(OpCode.OP_JUMP))

    @gen_stmt.register
    def _(self, stmt: FunctionStmt) -> None:
        self.line = stmt.name.line
        is_local = self.scope_depth > 0
        if is_local:
            self.declare_local(stmt.name)
            self.locals[-1].depth = self.scope_depth
        self.compile_function(stmt)
        if not is_local:
            self.emit(OpCode.OP_DEFINE_GLOBAL, self.name_const(stmt.name.lexeme))

    @gen_stmt.register
    def _(self, stmt: ReturnStmt) -> None:
        self.line = stmt.keyword.line
        # en main no hay funcion que retorne
        if self.enclosing is None:
            raise CompileError(stmt.keyword.line, "No se puede retornar desde fuera de una funcion.")
        if stmt.value is None:
            self.emit_implicit_return()
            return
        if self.kind == INITIALIZER:
            raise CompileError(stmt.keyword.line, "No se puede retornar un valor desde un inicializador.")
        self.gen_expr(stmt.value)
        self.emit(OpCode.OP_RETURN)

    # Una clase se arma en runtime en tres pasos:
    #   1. OP_CLASS crea la clase vacia y se guarda en su variable.
    #   2. si hereda, OP_INHERIT copia los metodos de la superclase.
    #   3. cada metodo se compila como un closure y OP_METHOD lo agrega a la clase.
    @gen_stmt.register
    def _(self, stmt: ClassStmt) -> None:
        self.line = stmt.name.line
        name_idx = self.name_const(stmt.name.lexeme)
        is_local = self.scope_depth > 0
        if is_local:
            self.declare_local(stmt.name)
            self.locals[-1].depth = self.scope_depth
        self.emit(OpCode.OP_CLASS, name_idx)
        if not is_local:
            self.emit(OpCode.OP_DEFINE_GLOBAL, name_idx)

        info = ClassInfo()
        self.classes.append(info)

        if stmt.superclass is not None:
            if stmt.superclass.name.lexeme == stmt.name.lexeme:
                raise CompileError(stmt.superclass.name.line, "Una clase no puede heredar de si misma.")
            # La superclase queda en el stack como una local llamada `super` dentro
            # de un scope propio: los metodos la capturan como upvalue y asi
            # `super.metodo` sabe a que clase ir aunque la variable original cambie.
            self.gen_expr(stmt.superclass)
            self.begin_scope()
            self.locals.append(Local("super", self.scope_depth))
            self.emit_get(stmt.name)
            self.line = stmt.superclass.name.line
            self.emit(OpCode.OP_INHERIT)
            info.has_superclass = True

        # La clase queda en el tope mientras se le agregan los metodos.
        self.emit_get(stmt.name)
        for method in stmt.methods:
            self.line = method.name.line
            kind = INITIALIZER if method.name.lexeme == "init" else METHOD
            self.compile_function(method, kind)
            self.emit(OpCode.OP_METHOD, self.name_const(method.name.lexeme))
        self.emit(OpCode.OP_POP)

        if info.has_superclass:
            self.end_scope()
        self.classes.pop()

    # expresiones: dejan un valor en el stack (+1)
    @singledispatchmethod
    def gen_expr(self, expr: Expr) -> None:
        raise CompileError(self.line, f"Todavia no soportado: {type(expr).__name__}")

    
    @gen_expr.register
    def _(self, expr: LiteralExpr) -> None:
        if expr.value is None:
            self.emit(OpCode.OP_NIL)
        elif expr.value is True:
            self.emit(OpCode.OP_TRUE)
        elif expr.value is False:
            self.emit(OpCode.OP_FALSE)
        else:
            self.emit_const(expr.value)


    @gen_expr.register
    def _(self, expr: GroupingExpr) -> None:
        self.gen_expr(expr.expression)

    # En unarios primero guardamos el operando en el stack y despues operador 
    @gen_expr.register
    def _(self, expr: UnaryExpr) -> None:
        self.gen_expr(expr.right)
        self.line = expr.operator.line
        if expr.operator.kind == TokenKind.MINUS:
            self.emit(OpCode.OP_NEGATE)
        elif expr.operator.kind == TokenKind.BANG:
            self.emit(OpCode.OP_NOT)
        else:
            raise CompileError(self.line, f"Operador unario invalido: {expr.operator.lexeme}")

    # binarios izquierda, derecha, operador 
    @gen_expr.register
    def _(self, expr: BinaryExpr) -> None:
        self.gen_expr(expr.left)
        self.gen_expr(expr.right)
        self.line = expr.operator.line
        ops = _BINARY_OPS.get(expr.operator.kind)
        if ops is None:
            raise CompileError(self.line, f"Operador binario invalido: {expr.operator.lexeme}")
        self.emit(*ops)

    # Leer una variable es una expresion: deja su valor en el stack (+1).
    @gen_expr.register
    def _(self, expr: VariableExpr) -> None:
        self.line = expr.name.line
        self.emit_get(expr.name)

    # x = valor es una expresion, tiene que dejar su valor en el stack.
    # Por eso el set no saca el valor (usa peek). despues con el OP_POP del `;` se descarta si nadie lo usa.
    @gen_expr.register
    def _(self, expr: AssignExpr) -> None:
        self.line = expr.name.line
        if expr.operator is not None:
            self.emit_get(expr.name)
            self.gen_expr(expr.value)
            self.line = expr.operator.line
            self.emit(*_BINARY_OPS[expr.operator.kind])
        else:
            self.gen_expr(expr.value)
        self.line = expr.name.line
        self.emit_set(expr.name)


    @gen_expr.register
    def _(self, expr: LogicalExpr) -> None:
        self.gen_expr(expr.left)
        if expr.operator.kind == TokenKind.AND:
            end_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE)
            self.emit(OpCode.OP_POP)
            self.gen_expr(expr.right)
            self.patch_jump(end_jump)
        else:
            right_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE)
            end_jump = self.emit_jump(OpCode.OP_JUMP)
            self.patch_jump(right_jump)
            self.emit(OpCode.OP_POP)
            self.gen_expr(expr.right)
            self.patch_jump(end_jump)


    @gen_expr.register
    def _(self, expr: CallExpr) -> None:
        self.gen_expr(expr.callee)
        for argument in expr.arguments:
            self.gen_expr(argument)
        self.line = expr.paren.line
        # el operando mide 1 byte (el parser ya rechaza mas de 255 argumentos, esto es por las dudas)
        if len(expr.arguments) > 255:
            raise CompileError(self.line, "No se pueden tener mas de 255 argumentos.")
        self.emit(OpCode.OP_CALL, len(expr.arguments))

    @gen_expr.register
    def _(self, expr: GetExpr) -> None:
        self.gen_expr(expr.object)
        self.line = expr.name.line
        self.emit(OpCode.OP_GET_PROPERTY, self.name_const(expr.name.lexeme))

    # obj.campo = valor deja el valor en el stack (es una expresion, como la asignacion).
    # Con operador compuesto (obj.campo += x) se duplica la instancia: una copia la
    # consume el GET y la otra el SET, asi `obj` se evalua una sola vez.
    @gen_expr.register
    def _(self, expr: SetExpr) -> None:
        self.gen_expr(expr.object)
        name_idx = self.name_const(expr.name.lexeme)
        if expr.operator is not None:
            self.emit(OpCode.OP_DUP)
            self.line = expr.name.line
            self.emit(OpCode.OP_GET_PROPERTY, name_idx)
            self.gen_expr(expr.value)
            self.line = expr.operator.line
            self.emit(*_BINARY_OPS[expr.operator.kind])
        else:
            self.gen_expr(expr.value)
        self.line = expr.name.line
        self.emit(OpCode.OP_SET_PROPERTY, name_idx)

    # `this` es la local del slot 0 del metodo (o un upvalue si estamos en una
    # funcion anidada dentro del metodo).
    @gen_expr.register
    def _(self, expr: ThisExpr) -> None:
        self.line = expr.keyword.line
        if not self.classes:
            raise CompileError(expr.keyword.line, "No se puede usar 'this' fuera de una clase.")
        self.emit_get(expr.keyword)

    # super.metodo: se pushea la instancia y la superclase, y OP_GET_SUPER busca
    # el metodo en la superclase y lo liga a la instancia.
    @gen_expr.register
    def _(self, expr: SuperExpr) -> None:
        self.line = expr.keyword.line
        if not self.classes:
            raise CompileError(expr.keyword.line, "No se puede usar 'super' fuera de una clase.")
        if not self.classes[-1].has_superclass:
            raise CompileError(expr.keyword.line, "No se puede usar 'super' en una clase sin superclase.")
        self.emit_get(Token(TokenKind.THIS, "this", None, expr.keyword.line))
        self.emit_get(expr.keyword)
        self.line = expr.method.line
        self.emit(OpCode.OP_GET_SUPER, self.name_const(expr.method.lexeme))
