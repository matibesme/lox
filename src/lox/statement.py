from abc import ABC
from dataclasses import dataclass
from typing import Any
from lox.expr import Expr
from lox.tokens import Token


@dataclass(frozen=True)
class Stmt(ABC):
    pass


@dataclass(frozen=True,slots=True)
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass(frozen=True,slots=True)
class PrintStmt(Stmt):
    expression: Expr


@dataclass(frozen=True,slots=True)
class VarStmt(Stmt):
    name: Token
    initializer: Expr | None

@dataclass(frozen=True,slots=True)
class BlockStmt(Stmt):
    statements: list[Stmt]

@dataclass(frozen=True,slots=True)
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Stmt | None


@dataclass(frozen=True,slots=True)
class WhileStmt(Stmt):
    condition: Expr
    body: Stmt

@dataclass(frozen=True,slots=True)
class FunctionStmt(Stmt):
    name: Token
    params: list[Token]
    body: list[Stmt]

@dataclass(frozen=True,slots=True)
class ReturnStmt(Stmt):
    keyword: Token
    value: Expr | None
