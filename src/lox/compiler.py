

from __future__ import annotations
from functools import singledispatchmethod
from lox.chunk import Chunk, OpCode
from lox.errors import CompileError
from lox.expr import BinaryExpr, Expr, GroupingExpr, LiteralExpr, UnaryExpr
from lox.statement import ExpressionStmt, PrintStmt, Stmt
from lox.tokens import TokenKind

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