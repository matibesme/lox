from __future__ import annotations
from functools import singledispatchmethod
from lox.chunk import Chunk, OpCode
from lox.errors import CompileError
from lox.expr import (
    AssignExpr, BinaryExpr, Expr, GroupingExpr, LiteralExpr, LogicalExpr,
    UnaryExpr, VariableExpr,
)
from lox.statement import (
    BlockStmt, BreakStmt, ContinueStmt, ExpressionStmt, IfStmt, PrintStmt,
    Stmt, VarStmt, WhileStmt,
)
from lox.tokens import Token, TokenKind
from lox.compiler_state import Local, Loop

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

# stack effect
#   -  las expresiones dejan exactamente 1 valor en el stack  
#   -   todo STATEMENT deja el stack como estaba   

class BytecodeCompiler:
    #Recorre el AST (post-order, primero compilando hijos para que las operaciones tengan sus operandos en el stack.) 
    # y emite bytecode en formato lineal.
    def __init__(self) -> None:
        self.chunk = Chunk()
        self.line = 1
        # simula el stack de la VM con cant de variables locales y su orden
        self.locals: list[Local] = []
        # profundidad de bloque vemos si es local o global
        self.scope_depth = 0
        # lista de bucles abiertos para poder compilar break/continue
        self.loops: list[Loop] = []
        # nombre de global -> indice en el pool
        self.name_consts: dict[str, int] = {}

    
    def compile(self, statements: list[Stmt]) -> Chunk:
        for stmt in statements:
            self.gen_stmt(stmt)

        # op return al final del programa para que la VM sepa que termino.
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

    # escriben operando para leer o escribir una variable local o global
    def emit_get(self, name: Token) -> None:
        slot = self.resolve_local(name)
        if slot != -1:
            self.emit(OpCode.OP_GET_LOCAL, slot)
        else:
            self.emit(OpCode.OP_GET_GLOBAL, self.name_const(name.lexeme))

    def emit_set(self, name: Token) -> None:
        slot = self.resolve_local(name)
        if slot != -1:
            self.emit(OpCode.OP_SET_LOCAL, slot)
        else:
            self.emit(OpCode.OP_SET_GLOBAL, self.name_const(name.lexeme))

  # Cuando se sale de un bucle, hay que descartar todas las locales que se declararon dentro del bucle.
    def leave_loop_scope(self, keyword: Token, name: str) -> Loop:
        self.line = keyword.line
        if not self.loops:
            raise CompileError(keyword.line, f"No se puede usar '{name}' fuera de un bucle.")
        loop = self.loops[-1]
        for _ in self.locals[loop.locals_at_entry:]:
            self.emit(OpCode.OP_POP)
        return loop

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