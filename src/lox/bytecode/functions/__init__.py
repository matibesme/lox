"""Valores que existen en runtime para soportar funciones en la VM: Function, Closure, Upvalue y CallFrame."""

from lox.bytecode.functions.call_frame import CallFrame
from lox.bytecode.functions.closure import Closure
from lox.bytecode.functions.function import Function
from lox.bytecode.functions.upvalue import Upvalue

__all__ = ["Function", "Upvalue", "Closure", "CallFrame"]
