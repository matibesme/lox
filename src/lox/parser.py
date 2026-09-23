from typing import Callable
from lox.errors import ErrorReporter, ParseError
from lox.statement import BlockStmt, ExpressionStmt, PrintStmt, Stmt, VarStmt, IfStmt, WhileStmt, FunctionStmt, ReturnStmt
from lox.tokens import Token, TokenKind
from lox.expr import Expr, BinaryExpr, UnaryExpr, LiteralExpr, GroupingExpr, VariableExpr, AssignExpr, LogicalExpr, CallExpr


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
            if self._match(TokenKind.FUN):
                return self._function_declaration("funcion")
            if self._match(TokenKind.VAR):
                return self._var_declaration()
            return self._statement()
        except ParseError:
            self._skip_to_next_statement()
            return None

    def _function_declaration(self, kind: str) -> Stmt:
        name = self._consume(TokenKind.IDENTIFIER, f"Se esperaba el nombre de la {kind}.")
        self._consume(TokenKind.LEFT_PAREN, f"Se esperaba '(' despues del nombre de la {kind}.")

        params: list[Token] = []
        if not self._check_token(TokenKind.RIGHT_PAREN):
            while True:
                if len(params) >= 255:
                    self._error(self._peek(), "No se pueden tener mas de 255 parametros.")
                params.append(self._consume(TokenKind.IDENTIFIER, "Se esperaba el nombre del parametro."))
                if not self._match(TokenKind.COMMA):
                    break
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' despues de los parametros.")

        self._consume(TokenKind.LEFT_BRACE, f"Se esperaba '{{' antes del cuerpo de la {kind}.")
        body = self._block()
        return FunctionStmt(name, params, body)

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
        if self._match(TokenKind.IF):
            return self._if_statement()
        if self._match(TokenKind.WHILE):
            return self._while_statement()
        if self._match(TokenKind.FOR):
            return self._for_statement()
        if self._match(TokenKind.RETURN):
            return self._return_statement()
        return self._expression_statement()

    def _return_statement(self) -> Stmt:
        keyword = self._previous()
        value: Expr | None = None
        if not self._check_token(TokenKind.SEMICOLON):
            value = self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' despues del valor de retorno.")
        return ReturnStmt(keyword, value)

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
    
    def _if_statement(self) -> Stmt:
        self._consume(TokenKind.LEFT_PAREN, "Se esperaba '(' despues de 'if'.")
        condition = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' despues de la condicion.")

        then_branch = self._statement()

        else_branch: Stmt | None = None
        if self._match(TokenKind.ELSE):
            else_branch = self._statement()

        return IfStmt(condition, then_branch, else_branch)
    
    def _while_statement(self) -> Stmt:
        self._consume(TokenKind.LEFT_PAREN, "Se esperaba '(' despues de 'while'.")
        condition = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' despues de la condicion.")
        body = self._statement()
        return WhileStmt(condition, body)
    
    def _for_statement(self) -> Stmt:
        # Azúcar sintáctico: descompone el for en un bloque que contiene
        # la inicialización y un bucle while con la condición y el incremento.
        self._consume(TokenKind.LEFT_PAREN, "Se esperaba '(' despues de 'for'.")

        if self._match(TokenKind.SEMICOLON):
            start = None
        elif self._match(TokenKind.VAR):
            start = self._var_declaration()
        else:
            start = self._expression_statement()

        condition: Expr | None = None
        if not self._check_token(TokenKind.SEMICOLON):
            condition = self._expression()
        self._consume(TokenKind.SEMICOLON, "Se esperaba ';' despues de la condicion.")

        increment: Expr | None = None
        if not self._check_token(TokenKind.RIGHT_PAREN):
            increment = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' despues del 'for'.")

        body = self._statement()
        if increment is not None:
            body = BlockStmt([body, ExpressionStmt(increment)])

        if condition is None:
            condition = LiteralExpr(True)
        body = WhileStmt(condition, body)

        if start is not None:
            body = BlockStmt([start, body])

        return body






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
        return self._binary(self._unary, TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT)
    
   
# operaciones unarias
    def _unary(self) -> Expr:
        if self._match(TokenKind.BANG, TokenKind.MINUS):
            operator = self._previous()
            right = self._unary()
            return UnaryExpr(operator=operator, right=right)
        return self._call()

# llamadas: nombre(args) o cualquier expresion que resuelva a una funcion, ej getFn()(3)
    def _call(self) -> Expr:
        expr = self._primary()
        while self._match(TokenKind.LEFT_PAREN):
            expr = self._finish_call(expr)
        return expr

    def _finish_call(self, callee: Expr) -> Expr:
        arguments: list[Expr] = []
        if not self._check_token(TokenKind.RIGHT_PAREN):
            while True:
                if len(arguments) >= 255:
                    self._error(self._peek(), "No se pueden tener mas de 255 argumentos.")
                arguments.append(self._expression())
                if not self._match(TokenKind.COMMA):
                    break
        paren = self._consume(TokenKind.RIGHT_PAREN, "Se esperaba ')' despues de los argumentos.")
        return CallExpr(callee, paren, arguments)

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
    
    
        