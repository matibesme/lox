from lox.errors import ErrorReporter
from .errors import ParseError
from .tokens import Token, TokenKind
from .expr import Expr, BinaryExpr, UnaryExpr, LiteralExpr, GroupingExpr, VariableExpr, AssignExpr, LogicalExpr
from typing import Callable
from .statement import BlockStmt, ExpressionStmt, PrintStmt, Stmt, VarStmt


class Parser:
    def __init__(self, tokens: list[Token], reporter: ErrorReporter | None = None) -> None:
        self._tokens = tokens
        self._reporter = reporter or ErrorReporter()
        self._current = 0
       
    
    def parse(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self._is_end():
            stmt = self._declaration()
            if stmt is not None:
                statements.append(stmt)
        return statements

## Statements rules
    def _declaration(self) -> Stmt | None:
        try:
            if self._match(TokenKind.VAR):
                return self._var_declaration()
            return self._statement()
        except ParseError:
            self._skip_to_next_statement()
            return None

    def _var_declaration(self) -> Stmt:
        name = self._consume(TokenKind.IDENTIFIER, "Se esperaba el nombre de la variable.")

        initializer: Expr | None = None
        if self._match(TokenKind.EQUAL):
            initializer = self._expression()

        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' despues de la declaracion de variable.")
        return VarStmt(name, initializer)

    def _statement(self) -> Stmt:
        if self._match(TokenKind.PRINT):
            return self._print_statement()
        if self._match(TokenKind.LEFT_BRACE):
            return BlockStmt(self._block())
        return self._expression_statement()

    def _print_statement(self) -> Stmt:
        value = self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' despues del valor.")
        return PrintStmt(value)

    def _expression_statement(self) -> Stmt:
        expr = self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' despues de la expresion.")
        return ExpressionStmt(expr)

    def _block(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self._check_token(TokenKind.RIGHT_BRACE) and not self._is_end():
            stmt = self._declaration()
            if stmt is not None:
                statements.append(stmt)

        self._consume(TokenKind.RIGHT_BRACE, "Se esperaba '}' despues del bloque.")
        return statements


## operaciones 
    def _expression(self) -> Expr:
        return self._assignment()


## operaciones binarias 
    def _or(self) -> Expr:
        expr = self._and()
        while self._match(TokenKind.OR):
            operator = self._previous()
            right = self._and()
            expr = LogicalExpr(expr, operator, right)
        return expr
    
    def _and(self) -> Expr:
        expr = self._equality()
        while self._match(TokenKind.AND):
            operator = self._previous()
            right = self._equality()
            expr = LogicalExpr(expr, operator, right)
        return expr

    def _equality(self) -> Expr:
        return self._binary(self._comparison, TokenKind.BANG_EQUAL, TokenKind.EQUAL_EQUAL)
    
    def _comparison(self) -> Expr:
        return self._binary(self._term, TokenKind.GREATER, TokenKind.GREATER_EQUAL, TokenKind.LESS, TokenKind.LESS_EQUAL)

    def _term(self) -> Expr:
        return self._binary(self._factor, TokenKind.PLUS, TokenKind.MINUS)

    def _factor(self) -> Expr:
        return self._binary(self._unary, TokenKind.STAR, TokenKind.SLASH)
    
   
# operaciones unarias
    def _unary(self) -> Expr:
        if self._match(TokenKind.BANG, TokenKind.MINUS):
            operator = self._previous()
            right = self._unary()
            return UnaryExpr(operator=operator, right=right)
        return self._primary()

# objetos primarios
    def _primary(self) -> Expr:
        if self._match(TokenKind.FALSE):
            return LiteralExpr(False)
        if self._match(TokenKind.TRUE):
            return LiteralExpr(True)
        if self._match(TokenKind.NIL):
            return LiteralExpr(None)
        if self._match(TokenKind.NUMBER, TokenKind.STRING):
            return LiteralExpr(self._previous().literal)
        if self._match(TokenKind.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenKind.RIGHT_PAREN, "Se esperaba cierre de parentesis.")
            return GroupingExpr(expr)
        if self._match(TokenKind.IDENTIFIER):
            return VariableExpr(self._previous())
        raise self._error(self._peek(), "Se esperaba una expresión.")

    
# helpers

    def _binary(self, operand_parser: Callable[[], Expr], *operators: TokenKind) -> Expr:
        """Parsea una operación binaria. Recibe como parametro la funcion para parsear los operandos de mayor precedencia y los operadores."""
        expr = operand_parser()
        while self._match(*operators):
            operator = self._previous()
            right = operand_parser()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _peek(self) -> Token:
        """Devuelve el token actual"""
        return self._tokens[self._current]

    def _is_end(self) -> bool:
        """Devuelve True si el token actual es EOF"""
        return self._peek().kind == TokenKind.EOF

    def _previous(self) -> Token:
        """Devuelve el token anterior"""
        return self._tokens[self._current - 1]
        
    def _next(self) -> Token:
        """Avanza al siguiente token"""
        if not self._is_end():
            self._current += 1 
        return self._previous()
    
    def _check_token(self, token_kind: TokenKind) -> bool:
        """Devuelve True si el token actual es del tipo token_kind"""
        if self._is_end():
            return False
        return self._peek().kind == token_kind

    def _match(self, *token_kind: TokenKind) -> bool:
        """Devuelve True si el token actual es del tipo token_kind y lo consume"""
        if not self._is_end() and self._peek().kind in token_kind:
            self._next()
            return True
        return False
    
    def _consume(self, token_kind: TokenKind, message: str) -> Token:
        if self._check_token(token_kind):
            return self._next()
        raise self._error(self._peek(), message)  

    def _assignment(self) -> Expr:
        expr = self._or()  
        if self._match(TokenKind.EQUAL):
            equals = self._previous()
            value = self._assignment()
            if isinstance(expr, VariableExpr):
                name = expr.name
                return AssignExpr(name, value)
            raise self._error(equals, "Objetivo de asignacion invalido.")
        return expr


# error

    def _skip_to_next_statement(self) -> None:
            """Descarta tokens hasta encontrar el inicio del siguiente statement"""
            self._next()
            while not self._is_end():
                if self._previous().kind == TokenKind.SEMICOLON:
                    return
                if self._peek().kind in (
                    TokenKind.CLASS,
                    TokenKind.FUN,
                    TokenKind.VAR,
                    TokenKind.FOR,
                    TokenKind.IF,
                    TokenKind.WHILE,
                    TokenKind.PRINT,
                    TokenKind.RETURN,
                ):
                    return
                self._next()



    def _error(self, token: Token, message: str) -> ParseError:
        error = ParseError(token, message)
        self._reporter.report(error)
        return error
    
    
        