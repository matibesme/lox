"""Analisis semantico: pasada previa a la ejecucion que resuelve el scope estatico.

Recorre el AST con el mismo estilo de single dispatch que el interprete, pero
en vez de calcular valores calcula, para cada uso de una variable local, a
cuantos enviroments (`enclosing`) hay que subir para encontrarla. Esa
distancia se le entrega al interprete via `interpreter.resolve(...)` para que
la busqueda en runtime no dependa de la mutabilidad de los dicts de scope.
"""

from __future__ import annotations

from enum import Enum, auto
from functools import singledispatchmethod

from lox.errors import ErrorReporter, ResolverError
from lox.expr import (
    AssignExpr,
    BinaryExpr,
    CallExpr,
    Expr,
    GroupingExpr,
    LiteralExpr,
    LogicalExpr,
    UnaryExpr,
    VariableExpr,
)
from lox.interpreter import Interpreter
from lox.statement import (
    BlockStmt,
    ExpressionStmt,
    FunctionStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    Stmt,
    VarStmt,
    WhileStmt,
)
from lox.tokens import Token


class _FunctionKind(Enum):
    NONE = auto()
    FUNCTION = auto()


class Resolver:
    def __init__(self, interpreter: Interpreter, reporter: ErrorReporter | None = None) -> None:
        self._interpreter = interpreter
        self._reporter = reporter or ErrorReporter()
        self._scopes: list[dict[str, bool]] = []
        self._current_function = _FunctionKind.NONE

    def resolve(self, statements: list[Stmt]) -> None:
        for stmt in statements:
            self._resolve(stmt)

    @singledispatchmethod
    def _resolve(self, node) -> None:
        raise NotImplementedError(f"Nodo no soportado por el resolver: {type(node)}")

## Statements
    @_resolve.register
    def _(self, stmt: ExpressionStmt) -> None:
        self._resolve(stmt.expression)

    @_resolve.register
    def _(self, stmt: PrintStmt) -> None:
        self._resolve(stmt.expression)

    @_resolve.register
    def _(self, stmt: VarStmt) -> None:
        self._declare(stmt.name)
        if stmt.initializer is not None:
            self._resolve(stmt.initializer)
        self._define(stmt.name)

    @_resolve.register
    def _(self, stmt: BlockStmt) -> None:
        self._begin_scope()
        self.resolve(stmt.statements)
        self._end_scope()

    @_resolve.register
    def _(self, stmt: IfStmt) -> None:
        self._resolve(stmt.condition)
        self._resolve(stmt.then_branch)
        if stmt.else_branch is not None:
            self._resolve(stmt.else_branch)

    @_resolve.register
    def _(self, stmt: WhileStmt) -> None:
        self._resolve(stmt.condition)
        self._resolve(stmt.body)

    @_resolve.register
    def _(self, stmt: FunctionStmt) -> None:
        # declarar y definir el nombre antes del cuerpo permite la recursion.
        self._declare(stmt.name)
        self._define(stmt.name)
        self._resolve_function(stmt, _FunctionKind.FUNCTION)

    @_resolve.register
    def _(self, stmt: ReturnStmt) -> None:
        if self._current_function is _FunctionKind.NONE:
            self._report(stmt.keyword, "No se puede retornar desde fuera de una funcion.")
        if stmt.value is not None:
            self._resolve(stmt.value)

## Expresiones
    @_resolve.register
    def _(self, expr: VariableExpr) -> None:
        if self._scopes and self._scopes[-1].get(expr.name.lexeme) is False:
            self._report(expr.name, "No se puede leer una variable local en su propio inicializador.")
        self._resolve_local(expr, expr.name)

    @_resolve.register
    def _(self, expr: AssignExpr) -> None:
        self._resolve(expr.value)
        self._resolve_local(expr, expr.name)

    @_resolve.register
    def _(self, expr: BinaryExpr) -> None:
        self._resolve(expr.left)
        self._resolve(expr.right)

    @_resolve.register
    def _(self, expr: LogicalExpr) -> None:
        self._resolve(expr.left)
        self._resolve(expr.right)

    @_resolve.register
    def _(self, expr: UnaryExpr) -> None:
        self._resolve(expr.right)

    @_resolve.register
    def _(self, expr: GroupingExpr) -> None:
        self._resolve(expr.expression)

    @_resolve.register
    def _(self, expr: LiteralExpr) -> None:
        return

    @_resolve.register
    def _(self, expr: CallExpr) -> None:
        self._resolve(expr.callee)
        for argument in expr.arguments:
            self._resolve(argument)

## Helpers
    def _resolve_function(self, stmt: FunctionStmt, kind: _FunctionKind) -> None:
        enclosing_function = self._current_function
        self._current_function = kind

        self._begin_scope()
        for param in stmt.params:
            self._declare(param)
            self._define(param)
        self.resolve(stmt.body)
        self._end_scope()

        self._current_function = enclosing_function

    def _begin_scope(self) -> None:
        self._scopes.append({})

    def _end_scope(self) -> None:
        self._scopes.pop()

    def _declare(self, name: Token) -> None:
        if not self._scopes:
            return
        scope = self._scopes[-1]
        if name.lexeme in scope:
            self._report(name, "Ya existe una variable con este nombre en este scope.")
        scope[name.lexeme] = False

    def _define(self, name: Token) -> None:
        if not self._scopes:
            return
        self._scopes[-1][name.lexeme] = True

    def _resolve_local(self, expr: Expr, name: Token) -> None:
        for depth, scope in enumerate(reversed(self._scopes)):
            if name.lexeme in scope:
                self._interpreter.resolve(expr, depth)
                return
        # no esta en ningun scope local: se resuelve dinamicamente contra self.globals

    def _report(self, token: Token, message: str) -> None:
        self._reporter.report(ResolverError(token, message))
