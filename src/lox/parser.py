from lox.errors import ErrorReporter
from .errors import ParseError
from .tokens import Token, TokenKind
from .expr import Expr, BinaryExpr, UnaryExpr, LiteralExpr, GroupingExpr
from typing import Callable

class Parser:
    def __init__(self, tokens: list[Token], reporter: ErrorReporter | None = None) -> None:
        self._tokens = tokens
        self._reporter = reporter or ErrorReporter()
        self._current = 0
       
    
    def parse(self) -> Expr:
        try: 
            return self._expression()
        except ParseError:
            return None

## operaciones 
    def _expression(self) -> Expr:
        return self._equality()


## operaciones binarias 
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
# error
    def _error(self, token: Token, message: str) -> ParseError:
        error = ParseError(token, message)
        self._reporter.report(error)
        return error
    
    
        