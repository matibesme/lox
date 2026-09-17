from lox.tokens import Token
from dataclasses import dataclass
class Expr:
    pass

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
