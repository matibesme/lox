"""Definicion de tokens y sus tipos."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenKind(Enum):
    # Simbolos de un caracter
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    COMMA = auto()
    DOT = auto()
    MINUS = auto()
    PLUS = auto()
    SEMICOLON = auto()
    SLASH = auto()
    STAR = auto()
    PERCENT = auto()

    BANG = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()

    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Palabras clave
    AND = auto()
    CLASS = auto()
    ELSE = auto()
    FALSE = auto()
    FUN = auto()
    FOR = auto()
    IF = auto()
    NIL = auto()
    OR = auto()
    PRINT = auto()
    RETURN = auto()
    SUPER = auto()
    THIS = auto()
    TRUE = auto()
    VAR = auto()
    WHILE = auto()

    EOF = auto()


KEYWORDS: dict[str, TokenKind] = {
    "and": TokenKind.AND,
    "class": TokenKind.CLASS,
    "else": TokenKind.ELSE,
    "false": TokenKind.FALSE,
    "for": TokenKind.FOR,
    "fun": TokenKind.FUN,
    "if": TokenKind.IF,
    "nil": TokenKind.NIL,
    "or": TokenKind.OR,
    "print": TokenKind.PRINT,
    "return": TokenKind.RETURN,
    "super": TokenKind.SUPER,
    "this": TokenKind.THIS,
    "true": TokenKind.TRUE,
    "var": TokenKind.VAR,
    "while": TokenKind.WHILE,
}


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    literal: Any
    line: int

    def __str__(self) -> str:  # pragma: no cover - formato
        return f"{self.kind.name} {self.lexeme!r} {self.literal!r}"
