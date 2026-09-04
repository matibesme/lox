"""Scanner: convierte el codigo fuente en una lista de tokens."""

from __future__ import annotations

from .errors import ErrorReporter, ScanError
from .tokens import KEYWORDS, Token, TokenKind


def _is_digit(c: str) -> bool:
    return "0" <= c <= "9"


def _is_alpha(c: str) -> bool:
    return c == "_" or "a" <= c <= "z" or "A" <= c <= "Z"


def _is_alnum(c: str) -> bool:
    return _is_alpha(c) or _is_digit(c)


class Scanner:
    """Recorre el fuente caracter por caracter emitiendo tokens."""

    def __init__(self, source: str, reporter: ErrorReporter | None = None) -> None:
        self._source = source
        self._reporter = reporter or ErrorReporter()
        self._tokens: list[Token] = []
        self._start = 0    # inicio del lexema actual
        self._current = 0  # caracter que estamos mirando
        self._line = 1

    def scan_tokens(self) -> list[Token]:
        while not self._at_end():
            self._start = self._current
            self._scan_token()
        self._tokens.append(Token(TokenKind.EOF, "", None, self._line))
        return self._tokens

    def _scan_token(self) -> None:
        c = self._advance()
        match c:
            case "(":
                self._add(TokenKind.LEFT_PAREN)
            case ")":
                self._add(TokenKind.RIGHT_PAREN)
            case "{":
                self._add(TokenKind.LEFT_BRACE)
            case "}":
                self._add(TokenKind.RIGHT_BRACE)
            case ",":
                self._add(TokenKind.COMMA)
            case ".":
                self._add(TokenKind.DOT)
            case "-":
                self._add(TokenKind.MINUS)
            case "+":
                self._add(TokenKind.PLUS)
            case ";":
                self._add(TokenKind.SEMICOLON)
            case "*":
                self._add(TokenKind.STAR)
            case "!":
                self._add(TokenKind.BANG_EQUAL if self._match("=") else TokenKind.BANG)
            case "=":
                self._add(TokenKind.EQUAL_EQUAL if self._match("=") else TokenKind.EQUAL)
            case "<":
                self._add(TokenKind.LESS_EQUAL if self._match("=") else TokenKind.LESS)
            case ">":
                self._add(TokenKind.GREATER_EQUAL if self._match("=") else TokenKind.GREATER)
            case "/":
                self._slash()
            case " " | "\r" | "\t":
                pass  # ignoramos espacios en blanco
            case "\n":
                self._line += 1
            case '"':
                self._string()
            case _:
                if _is_digit(c):
                    self._number()
                elif _is_alpha(c):
                    self._identifier()
                else:
                    self._error(f"Caracter inesperado {c!r}.")


    def _slash(self) -> None:
        if self._match("/"):
            # Comentario de linea: consumir hasta el fin de linea.
            while self._peek() != "\n" and not self._at_end():
                self._advance()
        elif self._match("*"):
            self._block_comment()
        else:
            self._add(TokenKind.SLASH)

    def _block_comment(self) -> None:
        depth = 1
        while depth > 0 and not self._at_end():
            if self._peek() == "/" and self._peek_next() == "*":
                self._advance()
                self._advance()
                depth += 1
            elif self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                depth -= 1
            else:
                if self._peek() == "\n":
                    self._line += 1
                self._advance()
        if depth > 0:
            self._error("Comentario de bloque sin cerrar.")

    def _string(self) -> None:
        while self._peek() != '"' and not self._at_end():
            if self._peek() == "\n":
                self._line += 1
            self._advance()
        if self._at_end():
            self._error("Cadena sin cerrar.")
            return
        self._advance()  # comilla de cierre
        value = self._source[self._start + 1 : self._current - 1]
        self._add(TokenKind.STRING, value)

    def _number(self) -> None:
        while _is_digit(self._peek()):
            self._advance()
        if self._peek() == "." and _is_digit(self._peek_next()):
            self._advance()  # el punto
            while _is_digit(self._peek()):
                self._advance()
        value = float(self._source[self._start : self._current])
        self._add(TokenKind.NUMBER, value)

    def _identifier(self) -> None:
        while _is_alnum(self._peek()):
            self._advance()
        text = self._source[self._start : self._current]
        kind = KEYWORDS.get(text, TokenKind.IDENTIFIER)
        self._add(kind)


    def _advance(self) -> str:
        c = self._source[self._current]
        self._current += 1
        return c

    def _match(self, expected: str) -> bool:
        if self._at_end() or self._source[self._current] != expected:
            return False
        self._current += 1
        return True

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self._source[self._current]

    def _peek_next(self) -> str:
        if self._current + 1 >= len(self._source):
            return "\0"
        return self._source[self._current + 1]

    def _add(self, kind: TokenKind, literal: object = None) -> None:
        lexeme = self._source[self._start : self._current]
        self._tokens.append(Token(kind, lexeme, literal, self._line))

    def _at_end(self) -> bool:
        return self._current >= len(self._source)

    def _error(self, message: str) -> None:
        self._reporter.report(ScanError(self._line, message))
