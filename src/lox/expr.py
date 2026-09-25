from lox.tokens import Token
from dataclasses import dataclass, field
from abc import ABC
import itertools


_expr_counter = itertools.count()

@dataclass(frozen=True, slots=True)
class Expr(ABC):
    id: int = field(default_factory=_expr_counter.__next__, init=False, compare=False, hash=False)

@dataclass(frozen=True, slots=True)
class LiteralExpr(Expr):
    value: object
    def __str__(self) -> str:
        if isinstance(self.value, str):
            return f'<"{self.value}">'
        elif isinstance(self.value, float):
            return f"<{self.value}>"
        elif isinstance(self.value, bool):
            return "<TRUE>" if self.value else "<FALSE>"
        elif self.value is None:
            return "<NIL>"
        return str(self.value)

@dataclass(frozen=True, slots=True)
class UnaryExpr(Expr):
    operator: Token
    right: Expr
    def __str__(self) -> str:
        return f"({self.operator.kind.name} {self.right})"

@dataclass(frozen=True, slots=True)
class BinaryExpr(Expr):
    left: Expr
    operator: Token
    right: Expr
    def __str__(self) -> str:
        return f"({self.left} {self.operator.kind.name} {self.right})"

@dataclass(frozen=True, slots=True)
class GroupingExpr(Expr):
    expression: Expr
    def __str__(self) -> str:
        return f"({self.expression})"

@dataclass(frozen=True, slots=True)
class VariableExpr(Expr):
    name: Token

@dataclass(frozen=True, slots=True)
class AssignExpr(Expr):
    name: Token
    value: Expr

@dataclass(frozen=True, slots=True)
class LogicalExpr(Expr):
    left: Expr
    operator: Token
    right: Expr

    def __str__(self) -> str:
        return f"({self.left} {self.operator.kind.name} {self.right})"

@dataclass(frozen=True, slots=True)
class CallExpr(Expr):
    callee: Expr
    paren: Token
    arguments: list[Expr]

    def __str__(self) -> str:
        args = ", ".join(str(arg) for arg in self.arguments)
        return f"{self.callee}({args})"
