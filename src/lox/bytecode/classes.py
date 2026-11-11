"""Valores de runtime de la VM para soportar clases: Class, Instance y BoundMethod."""

from __future__ import annotations

from typing import Any

from .functions.closure import Closure



class Class:
    __slots__ = ("name", "methods")

    def __init__(self, name: str) -> None:
        self.name = name
        self.methods: dict[str, Closure] = {}

    def __str__(self) -> str:
        return self.name


# Objeto creado al invocar una clase. Los campos se crean al asignarlos.
class Instance:
    __slots__ = ("klass", "fields")

    def __init__(self, klass: Class) -> None:
        self.klass = klass
        self.fields: dict[str, Any] = {}

    def __str__(self) -> str:
        return f"{self.klass.name} instance"


class BoundMethod:
    __slots__ = ("receiver", "method")

    def __init__(self, receiver: Instance, method: Closure) -> None:
        self.receiver = receiver
        self.method = method

    def __str__(self) -> str:
        return str(self.method)
