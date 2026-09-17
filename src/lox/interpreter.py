from typing import Any
from lox.tokens import Token, TokenKind
from lox.errors import LoxRuntimeError, ErrorReporter
from functools import singledispatchmethod
from lox.expr import BinaryExpr, Expr, GroupingExpr, LiteralExpr, UnaryExpr, AssignExpr, VariableExpr
from lox.enviroment import Environment
from lox.statement import Stmt, PrintStmt, ExpressionStmt, VarStmt, BlockStmt

class Interpreter:

    def __init__(self, reporter: ErrorReporter | None = None) -> None:
        self._reporter = reporter or ErrorReporter()
        self.environment = Environment()

    def interpret(self, statements: list[Stmt]) -> None:
        try:
            for stmt in statements:
                self.run(stmt)
        except LoxRuntimeError as error:
            self._reporter.report(error)

## Ejecutar Statements
    @singledispatchmethod
    def run(self, stmt: Stmt) -> None:
        raise NotImplementedError(f"Tipo de statement no soportado: {type(stmt)}")

    @run.register
    def _(self, stmt: PrintStmt) -> None:
        value = self.evaluate(stmt.expression)
        print(self._stringify(value))

    @run.register
    def _(self, stmt: ExpressionStmt) -> None:
        self.evaluate(stmt.expression)

    @run.register
    def _(self, stmt: VarStmt) -> None:
        value = None
        if stmt.initializer is not None:
            value = self.evaluate(stmt.initializer)
        self.environment.define(stmt.name.lexeme, value)

    @run.register
    def _(self, stmt: BlockStmt) -> None:
        self.run_block(stmt.statements, Environment(enclosing=self.environment))

    ## para reutilizar el codigo en el futuro cuando tengamos funciones   
    def run_block(self, statements: list[Stmt], environment: Environment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements:
                self.run(statement)
        finally:
            self.environment = previous  # Restaura el entorno padre incluso si hay error


## Evaluar expresiones
    @singledispatchmethod
    def evaluate(self, expr: Expr) -> Any:
        raise NotImplementedError(f"Tipo de expresion no soportada: {type(expr)}")

    @evaluate.register
    def _(self, expr: LiteralExpr) -> Any:
        return expr.value

    @evaluate.register
    def _(self, expr: GroupingExpr) -> Any:
        return self.evaluate(expr.expression)

    @evaluate.register
    def _(self, expr: UnaryExpr) -> Any:
        right = self.evaluate(expr.right)

        if expr.operator.kind == TokenKind.MINUS:
            self._check_number_operand(expr.operator, right)
            return -right
        elif expr.operator.kind == TokenKind.BANG:
            return not self._is_truthy(right)

        raise LoxRuntimeError(expr.operator, f"Operador unario no soportado: {expr.operator.lexeme}")

    @evaluate.register
    def _(self, expr: BinaryExpr) -> Any:
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        op = expr.operator

        if op.kind == TokenKind.MINUS:
            self._check_number_operands(op, left, right)
            return left - right

        elif op.kind == TokenKind.SLASH:
            self._check_number_operands(op, left, right)
            if right == 0:
                raise LoxRuntimeError(op, "Division por cero.")
            return left / right

        elif op.kind == TokenKind.STAR:
            self._check_number_operands(op, left, right)
            return left * right

        elif op.kind == TokenKind.PLUS:
            if isinstance(left, float) and isinstance(right, float):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise LoxRuntimeError(op, "Los operandos deben ser dos numeros o dos cadenas de texto.")

        elif op.kind == TokenKind.GREATER:
            self._check_number_operands(op, left, right)
            return left > right

        elif op.kind == TokenKind.GREATER_EQUAL:
            self._check_number_operands(op, left, right)
            return left >= right

        elif op.kind == TokenKind.LESS:
            self._check_number_operands(op, left, right)
            return left < right

        elif op.kind == TokenKind.LESS_EQUAL:
            self._check_number_operands(op, left, right)
            return left <= right

        elif op.kind == TokenKind.BANG_EQUAL:
            return not self._is_equal(left, right)

        elif op.kind == TokenKind.EQUAL_EQUAL:
            return self._is_equal(left, right)

        raise LoxRuntimeError(op, f"Operador binario no soportado: {op.lexeme}")

    @evaluate.register
    def _(self, expr: VariableExpr) -> Any:
        return self.environment.get(expr.name)
    
    @evaluate.register
    def _(self, expr: AssignExpr) -> Any:
        value = self.evaluate(expr.value)
        self.environment.assign(expr.name, value)
        return value

    def _is_equal(self, left: Any, right: Any) -> bool:
        return left == right

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value  
        return True 

    def _stringify(self, value: Any) -> str:
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float):
            text = str(value)
            if text.endswith(".0"):
                text = text[:-2]
            return text
        return str(value)
    
    def _check_number_operand(self, operator: Token, operand: Any) -> None:
        if isinstance(operand, float):
            return
        raise LoxRuntimeError(operator, "El operando debe ser un numero.")
    def _check_number_operands(self, operator: Token, left: Any, right: Any) -> None:
        if isinstance(left, float) and isinstance(right, float):
            return
        raise LoxRuntimeError(operator, "Los operandos deben ser dos numeros.")