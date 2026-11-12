# Lox

Implementación de Lox en Python con dos formas de ejecución. Un intérprete *tree-walking* puro y un compilador a bytecode con su VM. 

**Integrantes:**
- Matías Besmedrisnik (Padrón: 110487)
- Gonzalo Nicolás Crudo (Padrón: 110816)

---

## Índice

- [Cómo correrlo](#cómo-correrlo)
  - [Modo interactivo](#modo-interactivo)
  - [Correr un archivo](#correr-un-archivo)
  - [Fases intermedias](#fases-intermedias)
- [Tests](#tests)
- [Benchmarks](#benchmarks)
- [Implementación y decisiones de diseño](#implementación-y-decisiones-de-diseño)
- [Frontend (compartido por ambos backends)](#frontend-compartido-por-ambos-backends)
  - [Scanner](#scanner)
  - [Parser](#parser)
- [Intérprete puro (tree-walking)](#intérprete-puro-tree-walking)
  - [Estado y Entornos (Environment)](#estado-y-entornos-environment)
  - [Resolver](#resolver)
  - [Interpreter](#interpreter)
- [Compilación a bytecode y VM](#compilación-a-bytecode-y-vm)
- [Diferencia importante](#diferencia-importante)
- [Limitaciones de esta implementación](#limitaciones-de-esta-implementación)
- [Chunks](#chunks)
- [Compiler](#compiler)
- [VM](#vm)
- [Variables locales y globales](#variables-locales-y-globales)
  - [Funciones](#funciones)
  - [Saltos de flujo](#saltos-de-flujo)
- [Clases y herencia](#clases-y-herencia)
  - [En el intérprete puro](#en-el-intérprete-puro)
  - [En el compilador y la VM](#en-el-compilador-y-la-vm)
- [Funcionalidades extra](#funcionalidades-extra)

---

## Cómo correrlo

El proyecto usa [**uv**](https://docs.astral.sh/uv/) para manejar el entorno y las dependencias (requiere Python 3.12+).

Para instalar el comando `lox` de forma local:
```bash
uv tool install --editable .
```

### Modo interactivo
La ejecución estándar ahora es con fase de compilación. Para ejecutar el intérprete revisar las flags en fases intermedias.
```bash
lox
```

### Correr un archivo
```bash
lox ruta/al/archivo.lox
# o también:
uv run lox ruta/al/archivo.lox
```

### Fases intermedias
```bash
lox --scanning script.lox  # Muestra la lista de tokens del scanner
lox --parsing script.lox   # Muestra la salida del parser
lox --interpreter script.lox # Muestra la salida del intérprete
lox --disassemble script.lox # Muestra el disassembly del código bytecode
```

---

## Tests

```bash
uv run pytest
```

Corre tanto los tests de la cátedra como los nuestros.

---
## Benchmarks
Comparamos el rendimiento de nuestra implementación de Lox contra Python y JavaScript en tres pruebas:

| Benchmark                                    | Lox (s) | Python (s) | JavaScript (s) |
| :------------------------------------------- | ------: | ---------: | -------------: |
| **Fibonacci (recursivo, `fib(24)`)**         |   2.98s |      0.05s |          0.04s |
| **Loop (bucle `while` de 200k iteraciones)** |   4.21s |      0.06s |          0.05s |
| **Concatenación de strings (50k strings)**   |   1.22s |      0.07s |          0.05s |

En estos benchmarks, Lox resulta aproximadamente entre **17x y 70x más lento que Python**, dependiendo de la prueba.

Esta diferencia es entendible ya que es un *tree-walk interpreter* puro. Además, nuestra implementación está escrita en Python, por lo que cada operación de Lox implica también el costo adicional de ejecutar la lógica del intérprete sobre el runtime de Python.

La diferencia es especialmente grande en Fibonacci y en el loop, donde se realizan una gran cantidad de operaciones pequeñas que implican recorridos del AST y *dispatch* del intérprete. En la concatenación de strings, parte del trabajo corresponde a operaciones internas de manejo de strings, por lo que la diferencia resulta menor.


Para tablas y gráficos de cada prueba, ver el [Reporte de benchmarks](benchmarks/report.md).


## Implementación y decisiones de diseño

Elegimos la opción 1 del TP (implementar Lox en Python) siguiendo las etapas vistas en clase. A lo largo del desarrollo nos encontramos con varias decisiones técnicas y adaptaciones respecto al libro. La estrategia de implementación fue no revisar el repo de plox más allá de lo visto en clase. 

## Frontend (compartido por ambos backends)
Esta parte se escribió para el intérprete puro y se reutiliza sin cambios para el compilador. El compilador recibe el AST del parser.

### Scanner
Encargado de la esfera léxica: su objetivo es leer el código carácter por carácter, reconocer las palabras válidas del lenguaje (tokens) y descartar comentarios y espacios en blanco.

- **Pattern matching (`match / case`):** En vez de meter una cadena gigante de `if/elif`, aprovechamos el `match/case` de Python para clasificar los caracteres simples de una y agrupar casos repetidos (como espacios y tabs).
- **Lookahead para no consumir de más:** Usamos `_peek`, `_peek_next` y `_match` para resolver ambigüedades sin avanzar caracteres innecesariamente (distinguir `=` de `==`, `<` de `<=`, o no consumir el `.` de un flotante si no viene seguido de un dígito).
- **Maximal munch:** Leemos los identificadores completos y recién al final los comparamos con el diccionario de palabras reservadas para definir si es palabra clave (`var`, `fun`, etc.) o identificador común.
- **Comentarios multilínea anidados (`/* ... */`):** Soportamos comentarios en bloque que pueden contener otros comentarios adentro; usamos un contador de profundidad (`depth`) que sube con `/*` y baja con `*/`, avisando si alguno queda sin cerrar.
- **Tolerancia a errores:** Ante un carácter desconocido o un string sin cerrar, el scanner registra el error en `ErrorReporter` y sigue adelante para mostrar todos los problemas del archivo de una sola pasada.

### Parser
Encargado de la esfera sintáctica: toma la secuencia de tokens y arma el árbol AST asegurándose de que las oraciones cumplan con la gramática de Lox.

- **Descenso recursivo y precedencia:** Cada regla gramatical es un método del parser. El flujo arranca en las reglas de **menor precedencia** (`assignment`, `or`, `equality`...) y va llamando en cascada hacia las de **mayor precedencia** (`factor`, `unary`, `primary`).
  - Lo hicimos así porque en un árbol sintáctico lo que tiene **mayor precedencia debe quedar más profundo (más abajo)** para que se resuelva primero. Por ejemplo en `1 + 2 * 3`, la suma (`_term`) delega en la multiplicación (`_factor`). La multiplicación se agrupa primero como `(2 * 3)` y pasa a ser el operando derecho de la suma (`1 + (2 * 3)`).
  - Para no duplicar el mismo bucle `while` en todas las operaciones binarias (`==`, `<`, `+`, `*`), usamos el helper `_binary` pasándole como callback la regla de precedencia inmediatamente superior y los tokens que acepta:
  ```python
  def _binary(self, operand_parser: Callable[[], Expr], *operators: TokenKind) -> Expr:
      expr = operand_parser()
      while self._match(*operators):
          operator = self._previous()
          right = operand_parser()
          expr = BinaryExpr(expr, operator, right)
      return expr

  # Así, por ejemplo, definir sumas y restas delegando en los factores queda en una sola línea:
  def _term(self) -> Expr:
      return self._binary(self._factor, TokenKind.PLUS, TokenKind.MINUS)
  ```
- **Parsear asignaciones (`_assignment`):** Cuando el parser lee una variable, todavía no sabe si es una lectura o una asignación. Primero parseamos la expresión normalmente y, si aparece un `=`, verificamos que el lado izquierdo sea una variable:
  ```python
  expr = self._or()
  if self._match(TokenKind.EQUAL):
      equals = self._previous()
      value = self._assignment()
      if isinstance(expr, VariableExpr):
          return AssignExpr(expr.name, value)
      raise self._error(equals, "Objetivo de asignación inválido.")
  ```
- **Operadores lógicos:** No tratamos a `and` y `or` como operaciones binarias comunes (que evalúan los dos lados sí o sí). Los modelamos con su propio nodo (`LogicalExpr`) para que el intérprete corte antes: si el lado izquierdo de un `or` ya es verdadero, el derecho ni se evalúa.
- **El bucle `for` como azúcar sintáctico:** No creamos un nodo `ForStmt` ni agregamos lógica en el intérprete. El parser desarma el `for` en el momento de leerlo, traduciéndolo a un bloque con el inicializador, un `WhileStmt` con la condición y el incremento ejecutándose al final del cuerpo.
- **Recuperación ante errores:** Si falta un `;` o un paréntesis, lanzamos un `ParseError`, lo reportamos y sincronizamos (`_skip_to_next_statement`) descartando tokens hasta el próximo `;` o el inicio de una nueva declaración (`var`, `fun`, `if`, etc.) para poder continuar parseando el resto del archivo sin acumular errores derivados del primero. 

## Intérprete puro (tree-walking)

### Estado y Entornos (Environment)
Acá dejamos de ser una calculadora que solo evalúa números y pasamos a un lenguaje completo con variables, bloques y funciones.

- **Expresiones vs. Statements:** Una expresión siempre se reduce a un valor (`2 + 3`), mientras que un statement hace algo en el mundo (imprime en pantalla con `print` o declara una variable). Para poder usar expresiones sueltas agregamos los *expression statements* (`<expr>;`). Esto nos permite evaluar una expresión como una sentencia, por ejemplo para llamar a una función aunque no nos interese su valor de retorno.
- **Cómo modelamos el entorno:** Básicamente es un diccionario de variables (`nombre -> valor`) con una referencia a su entorno "padre" (`enclosing`). Cuando entramos a un bloque `{ ... }`, creamos un entorno hijo nuevo, armando un árbol que mira de adentro hacia afuera.
- **Búsqueda y Shadowing:**
  - `define`: guarda la variable en el entorno actual. Si ya existe una afuera con el mismo nombre, hace shadowing. Al salir del bloque, la de afuera sigue viva con su valor previo.
  - `get` y `assign`: van subiendo por los padres hasta encontrar la variable. Si llegan al entorno global y no está, recién ahí tiran error en tiempo de ejecución.
- **Entrar y salir de bloques con `try / finally` (`run_block`):** Al ejecutar un bloque cambiamos el entorno actual por el nuevo, corremos lo que tiene adentro y, pase lo que pase (incluso si hay un error o un `return` que corta la ejecución), en el `finally` restauramos el entorno que teníamos antes para no romper el estado:
  ```python
  def run_block(self, statements: list[Stmt], environment: Environment) -> None:
      previous = self.environment
      try:
          self.environment = environment
          for statement in statements:
              self.run(statement)
      finally:
          self.environment = previous
  ```
- **Funciones, Closures y enclosing:**
  - **Al declararse:** la función guarda el entorno actual en el que fue creada como su `closure` (`LoxFunction(stmt, self.environment)`).
  - **Al invocarse:** se crea un entorno local para sus parámetros cuyo padre (`enclosing`) es justamente ese closure:
  ```python
  def call(self, interpreter: Interpreter, arguments: list[Any]) -> Any:
      environment = Environment(enclosing=self.closure)
      for param, argument in zip(self.declaration.params, arguments):
          environment.define(param.lexeme, argument)

      try:
          interpreter.run_block(self.declaration.body, environment)
      except ReturnSignal as signal:
          return signal.value
      return None
  ```
  De esta forma, la resolución de variables sube por la cadena de `enclosing` hacia donde nació la función y no hacia donde se la llama.

### Resolver
Análisis semántico: recorre el AST una sola vez antes de ejecutar para fijar el alcance léxico y detectar errores estáticos.

- **Calcular distancias fijas:** En vez de buscar variables a ciegas en runtime, recorre los scopes locales de adentro hacia afuera y le anota al intérprete a cuántos saltos (`depth`) exactos está cada variable:
  ```python
  def _resolve_local(self, expr: Expr, name: Token) -> None:
      for depth, scope in enumerate(reversed(self._scopes)):
          if name.lexeme in scope:
              self._interpreter.resolve(expr, depth)
              return
      # Si no está en ningún scope local, queda libre para resolverse dinámica en globals
  ```
  Esto garantiza que los closures siempre recuerden la variable correcta aunque después cambie el entorno.
- **Declarar vs. Definir (`var a = a;`):** Evita que una variable se use para calcular su propio valor inicial. Al procesar un `var a = ...;`, `_declare` la guarda en el scope con `False` (existe pero aún no tiene valor). Luego analiza la expresión de la derecha: si ahí adentro se intenta leer `a`, el resolver ve ese `False` y lanza error antes de ejecutar. Recién cuando la expresión termina de evaluarse, `_define` pasa la variable a `True` para que quede disponible para el resto del código.
- **Identidad de nodos (`itertools.count`):** Le asignamos a cada `Expr` un ID numérico único incremental con `itertools.count()`. Esto hace que el garbage collector no reutilice las direcciones de memoria de nodos ya liberados.
- **Validaciones semánticas:** Reporta errores antes de ejecutar el código, como hacer un `return` fuera de una función o redeclarar una variable dentro del mismo bloque.

### Interpreter
Encargado del runtime y la ejecución: recorre el AST evaluando expresiones y ejecutando sentencias sobre los entornos de variables en memoria.

- **Dispatch con `singledispatchmethod`:** En lugar del patrón Visitor que usa el libro, usamos `@singledispatchmethod` de Python con dos métodos principales: `evaluate(expr)` para resolver expresiones y devolver su valor (como hacer `2 + 3` y obtener `5`), y `run(stmt)` para ejecutar sentencias (como un `print`, un bucle `while` o declarar una variable). De esta forma, los nodos del AST no necesitan implementar lógica de ejecución y esta queda concentrada en el intérprete.
- **Entornos y saltos directos (`get_at` / `ancestor`):** El estado vive en instancias enlazadas de `Environment`. Si el Resolver calculó una distancia, el intérprete salta directamente con `ancestor(distance)` al entorno correspondiente sin recorrer linealmente la cadena. Si no tiene distancia, va directo a `globals`.
- **Retornos con señales:** Para propagar un return a través de loops y bloques anidados, lanzamos una excepción `ReturnSignal(value)`, capturada por `LoxFunction.call()`.
- **Persistencia en el REPL:** En `_run_prompt()`, el `Interpreter` se instancia una sola vez fuera del loop principal, permitiendo que las variables y funciones declaradas en una línea persistan para las siguientes.
- **Códigos de salida:** El `ErrorReporter` maneja los códigos de retorno `65` para errores estáticos (léxicos, sintácticos o del resolver), `70` para errores en runtime (`LoxRuntimeError`) y `64` para argumentos inválidos de CLI.

## Compilación a bytecode y VM

Hasta acá fue la explicación de un intérprete puro. En la segunda parte de la materia vimos cómo agregarle la compilación para terminar con el recorrido completo de la montañita. Con esto el pipeline pasa a tener dos fases bien separadas. Primero se compila todo el programa a bytecode (*tiempo de compilación*) y recién después la VM lo ejecuta (*tiempo de ejecución*).

Compilar nos acerca al código máquina. En lugar de recorrer un AST, donde cada nodo es un objeto separado y hay que ir entrando y saliendo de los hijos con una llamada a función por cada nodo, el programa pasa a ser una secuencia lineal de bytes, parecida a assembly, que se recorre de corrido una instrucción atrás de la otra. Es mucho más eficiente de ejecutar, y por eso logramos mayor performance.

El bytecode no es código máquina. No nos ata a ninguna arquitectura de hardware, así que sigue siendo portable (corre en cualquier lugar donde exista nuestra VM). En ese sentido es el punto medio entre el AST, muy portable y comprensible pero poco eficiente, y el código máquina que es muy rápido pero atado a una arquitectura.

A cambio de la performance perdemos legibilidad, igualmente sigue siendo entendible, porque el bytecode está pensado para poder entenderlo (`lox --disassemble`). Queda entonces el trade-off de más performance y menos comprensión.

Además queda la puerta abierta a futuras optimizaciones sobre representaciones intermedias que mejoren aún más la performance de nuestra implentacion de lox. 

## Diferencia importante

En clase el compilador es *single pass*. Lee los tokens, parsea y emite bytecode en el mismo paso, sin AST de por medio. Nosotros partimos del AST que ya construye el parser del frontend, como hacen muchas implementaciones de lenguajes vistas en clase (Go, Rust, Zig), y lo recorremos para generar el bytecode. Con el AST completo se puede analizar o transformar el programa antes de generar código, pero el costo es una pasada más de compilación, que se paga una sola vez y no empeora la ejecución.

## Limitaciones de esta implementación

Antes de entrar en la compilación hay que remarcar las limitaciones de esta implementación. Casi todas vienen de usar operandos de 1 byte en el bytecode, y ninguna cambia el comportamiento del lenguaje en programas normales.

* **Parámetros y argumentos por función (255).** La cantidad de argumentos de una llamada viaja en el operando de 1 byte de `OP_CALL`, y los parámetros son las primeras variables locales de la función (ver el límite de locales). Lo controla el parser, que es compartido, así que el límite es igual en el intérprete y en el compilador.
* **Constantes por chunk (256).** Los pools se indexan con 1 byte (ver [Chunks](#chunks)). Si se supera, `CompileError` ("Demasiadas constantes en un chunk.").
* **Variables locales por función (255).** El slot 0 está reservado para la función (ver [Funciones](#funciones)). Si se supera, `CompileError` ("Demasiadas variables locales.").
* **Variables capturadas por función (256).** Cada upvalue se identifica con 1 byte. Si se supera, `CompileError` ("Demasiadas variables capturadas en una funcion.").
* **Tamaño de un salto (65535 bytes).** El operando de un salto ocupa 2 bytes ([Saltos de flujo](#saltos-de-flujo)), así que el cuerpo de un `if` o de un bucle no puede pasar ese tamaño. Si se supera, `CompileError` ("El salto es demasiado largo." o "El cuerpo del bucle es demasiado largo.").
* **Profundidad de recursión.** La VM admite hasta 10.000 llamadas anidadas (`FRAMES_MAX`) y después falla con un `VMError`. El intérprete puro llega menos ya que recorre el AST con funciones recursivas de Python, así que cada llamada de Lox consume varios niveles de la pila de Python. 

## Chunks

Un chunk es donde se guarda el bytecode de un programa o de una función. Contiene la secuencia de instrucciones y su pool de constantes.

```python
class Chunk:
    def __init__(self) -> None:
        self.code = bytearray()      # instrucciones (opcodes y operandos)
        self.consts: list = []       # pool de constantes
        self.lines: list[int] = []   # línea de Lox de cada byte de code
```

- Cada instrucción empieza con un opcode de 1 byte (definidos en `op_code.py`) que indica la operación, seguido de sus operandos. Según la instrucción, el operando puede ser un índice al pool de constantes (1 byte), una posición de la pila (1 byte) o un offset de salto (2 bytes).
- `OP_CONSTANT` no lleva el valor sino un índice al pool. Los valores (números grandes, strings) tienen tamaño variable y así mantenemos las instrucciones de un tamaño uniforme, lo que hace el recorrido más rápido.
- `lines` guarda de qué línea de Lox salió cada byte, así los errores en tiempo de ejecución informan la línea donde ocurrieron.
- Todo el programa se compila en un main chunk, con un solo pool compartido. Las funciones tienen su propio chunk (ver [Funciones](#funciones)).

Con `lox --disassemble` se puede ver el bytecode.

## Compiler
El BytecodeCompiler recorre el AST en post-order y emite las instrucciones en el chunk. Reutiliza la misma técnica de dispatch que el intérprete, con `@singledispatchmethod` para `gen_stmt` (statements) y `gen_expr` (expresiones).
**Invariantes de la pila.**

- Las **expresiones** dejan un solo valor en la pila.
- Los **statements** dejan la pila como la encontraron.


Así se compila una expresión binaria (versión simplificada). Primero se compilan los dos operandos y después se emite la operación, que es el recorrido en post-order.

```python
@gen_expr.register
def _(self, expr: BinaryExpr) -> None:
    self.gen_expr(expr.left)                        # primero los operandos
    self.gen_expr(expr.right)
    self.emit(*_BINARY_OPS[expr.operator.kind])     # y después la operación
```

Los operadores `!=`, `>=` y `<=` no tienen instrucción propia, el compilador las traduce a una combinación de las que ya existen. 
 
**La pila se simula en el compilador.** Como el compilador sabe cómo cambia la pila cada instrucción que emite, lleva una lista `locals` que imita el orden de la pila real. El índice de una local en esa lista es directamente su slot en la VM. Cada `Local` guarda su nombre, la profundidad del bloque donde se declaró y si alguna función anidada la capturó (`is_captured`). Una profundidad de `-1` marca que la variable fue declarada pero todavía no inicializada, que es lo que permite detectar `var a = a;`.
 
**Un compilador por función.** Al encontrar un `fun`, se crea un `BytecodeCompiler` nuevo que apunta al compilador de afuera (`enclosing`) y compila el cuerpo en su propio chunk. Al terminar se vuelve al compilador anterior.

**Validaciones.** En el camino de compilación no se ejecuta el Resolver. Las validaciones estáticas las hace el propio compilador mientras recorre el AST (`return` fuera de una función, redeclarar una variable en el mismo scope, leer una local en su propio inicializador y usar `break` o `continue` fuera de un bucle). Un `CompileError` corta la compilación y el programa no llega a ejecutarse.

## VM
La VM es la encargada de ejecutar el código bytecode. Tiene un *instruction pointer* (`ip`) que apunta a la próxima instrucción, una pila donde se apilan los valores temporales y la tabla de `globals`. 
El bucle de ejecución es un `while True` con un `match` sobre el opcode. El programa principal se envuelve en un `Closure` que se apila en la posición 0 y se ejecuta como cualquier otra función. 

```python
while True:
    op = code[ip]
    ip += 1
    match op:
        case OpCode.OP_CONSTANT:
            stack.append(consts[code[ip]])   # busca la constante en el pool y la apila
            ip += 1
        case OpCode.OP_ADD:
            b, a = stack.pop(), stack.pop()  # el tope es el operando derecho
            ...                              # verifica los tipos
            stack.append(a + b)
        ...                                  # un caso por cada opcode
```

 
- **Errores en runtime.** Un `VMError` indica la línea de Lox (a partir de `chunk.lines`) y se reporta como cualquier otro error de ejecución.


## Variables locales y globales
 
- Las **globales** son *late-bound*. Se resuelven en runtime, así que las maneja la VM con un diccionario (`globals`). 
- Las **locales** son *early-bound*. Se resuelven en compilación, porque el scope es léxico y estático. El compilador simula el stack de la vm y sabe en qué posición exacta va a vivir cada variable local.

 
Para decidir qué instrucción emitir, el compilador busca el nombre primero entre sus locales (`resolve_local`), después entre las variables de las funciones de afuera (`resolve_upvalue`) y si no aparece en ninguna lo trata como global.

Así se ve en el compilador. `emit_get` prueba las tres opciones en orden y `resolve_local` recorre la lista `locals` de atrás hacia adelante para encontrar la variable más interna.

```python
def emit_get(self, name: Token) -> None:
    slot = self.resolve_local(name)
    if slot != -1:
        self.emit(OpCode.OP_GET_LOCAL, slot)               # local, el operando es su slot
    else:
        upvalue = self.resolve_upvalue(name)
        if upvalue != -1:
            self.emit(OpCode.OP_GET_UPVALUE, upvalue)      # variable de una función de afuera
        else:
            self.emit(OpCode.OP_GET_GLOBAL, self.name_const(name.lexeme))   # global, el operando es el índice del nombre en el pool

def resolve_local(self, name: Token) -> int:
    for slot in range(len(self.locals) - 1, -1, -1):       # de atrás hacia adelante
        local = self.locals[slot]
        if local.name == name.lexeme:
            if local.depth == -1:                          # declarada pero sin inicializar
                raise CompileError(name.line, "No se puede leer una variable local en su propio inicializador.")
            return slot                                    # el índice en la lista es el slot en la pila
    return -1
```
 
- Al cerrar un bloque se emite un `OP_POP` por cada local de ese scope (o un `OP_CLOSE_UPVALUE` si alguna función la capturó).

```python
def end_scope(self) -> None:
    self.scope_depth -= 1
    while self.locals and self.locals[-1].depth > self.scope_depth:
        if self.locals[-1].is_captured:
            self.emit(OpCode.OP_CLOSE_UPVALUE)   # alguna función la capturó, hay que cerrar el upvalue
        else:
            self.emit(OpCode.OP_POP)             # se descarta de la pila
        self.locals.pop()
```


### Funciones
 
Una función es un programa dentro de un programa, así que se compila a su propio chunk, con su propio pool de constantes
 
- **Función cruda vs. closure.** Al compilar un `fun` se arma un objeto `Function` (nombre, aridad, cantidad de upvalues y chunk). 

```python
class Function:
    def __init__(self, name: str | None) -> None:
        self.name = name
        self.arity = 0           # cantidad de parámetros
        self.upvalue_count = 0   # cuántas variables de afuera captura
        self.chunk = Chunk()     # su propio bytecode y su propio pool de constantes
```

Se arma en `compile_function`. Un compilador nuevo compila el cuerpo en el chunk de la función, y la función terminada se guarda en el pool del compilador de afuera junto con un `OP_CLOSURE`.

```python
def compile_function(self, stmt: FunctionStmt, kind: str = FUNCTION) -> None:
    function = Function(stmt.name.lexeme)
    function.arity = len(stmt.params)
    sub = BytecodeCompiler(enclosing=self, function=function, kind=kind)   # un compilador por función
    sub.begin_scope()
    for param in stmt.params:
        sub.declare_local(param)                                # los parámetros son las primeras locales
        sub.locals[-1].depth = sub.scope_depth
    for inner in stmt.body:
        sub.gen_stmt(inner)
    sub.emit_implicit_return()                                  # OP_NIL y OP_RETURN (un init devuelve this)
    function.upvalue_count = len(sub.upvalues)

    idx = self.chunk.add_const(function)                        # la función cruda vive en el pool de afuera
    self.emit(OpCode.OP_CLOSURE, idx)
    for upvalue in sub.upvalues:                                # un par de bytes por cada variable capturada
        self.emit(1 if upvalue.is_local else 0, upvalue.index)
```

Vive en el pool de constantes. En runtime, `OP_CLOSURE` toma esa función cruda y la envuelve en un `Closure`, que es lo que se apila, se guarda en una variable y se llama. 

- **Llamadas.** Se llama `OP_CALL` con la cantidad de argumentos como operando. Los argumentos ya quedaron en la pila justo después del closure. Con ese número la VM también verifica la aridad.

- **Retorno.** Si una función no tiene `return`, el compilador agrega `OP_NIL` y `OP_RETURN` al final.

**Call frames.** Tenemos una única pila por programa, pero una misma función puede llamarse desde contextos distintos, así que las locales no pueden usar posiciones absolutas. 
Cada llamada crea un *call frame*, una ventana sobre la pila que guarda el closure en ejecución, su propio `ip` y la posición del closure en la pila (`base`).

```python
class CallFrame:
    __slots__ = ("closure", "ip", "base")

    def __init__(self, closure: Closure, base: int) -> None:
        self.closure = closure
        self.ip = 0          # por dónde va esta función
        self.base = base     # dónde empieza su ventana en la pila
```

La VM crea el frame en `OP_CALL` y cambia el chunk que está ejecutando. Antes de entrar guarda el `ip` de quien llama, así `OP_RETURN` puede retomar justo donde había quedado.

```python
case OpCode.OP_CALL:
    argc = code[ip]
    ip += 1
    callee = stack[-1 - argc]                      # el closure está debajo de sus argumentos
    ...                                            # resuelve métodos y clases (ver Clases y herencia), verifica la aridad y FRAMES_MAX
    frame.ip = ip                                  # guarda por dónde iba quien llama
    frame = CallFrame(callee, len(stack) - argc - 1)
    frames.append(frame)
    code = callee.function.chunk.code              # pasa a ejecutar el chunk de la función
    consts = callee.function.chunk.consts
    base = frame.base
    ip = 0

case OpCode.OP_GET_LOCAL:
    stack.append(stack[base + code[ip]])           # el slot es relativo a la base del frame
    ip += 1
```


**Upvalues.** 
Los upvalues están implementados con `OP_GET_UPVALUE`, `OP_SET_UPVALUE` y `OP_CLOSE_UPVALUE`.

- **En compilación.** Cuando el compilador no encuentra un nombre entre las locales de la función actual, lo busca en el compilador de afuera (`resolve_upvalue`). Si lo encuentra, marca esa local como capturada (`is_captured`) y registra un `UpvalueRef`. Si está todavía más afuera, el upvalue se encadena a través de las funciones intermedias. Después de `OP_CLOSURE`, el compilador emite un par de bytes por cada upvalue que indica si se captura una local de la función contenedora o un upvalue suyo, y con qué índice.
- **En runtime.** Al ejecutar `OP_CLOSURE`, la VM arma el `Closure` y por cada par captura la variable. Si es una local, busca o crea un `Upvalue` abierto para esa posición de la pila (`capture_upvalue`). Si no, reutiliza el upvalue del closure de afuera. Dos closures que capturan la misma variable comparten el mismo `Upvalue`.
- **Abierto y cerrado.** Un upvalue abierto apunta a la posición de la pila donde sigue viva la variable. Cuando la variable está por salir de la pila (porque se cierra el bloque con `OP_CLOSE_UPVALUE` o porque la función retorna con `OP_RETURN`), la VM copia su valor al propio upvalue (`close_upvalues`) y lo marca como cerrado. A partir de ahí `OP_GET_UPVALUE` y `OP_SET_UPVALUE` leen y escriben ese valor copiado.


 
### Saltos de flujo
 
En el intérprete puro resolviamos el `if` y el `while` con un `if` y un `while` de Python. Ahora el flujo es una secuencia de bytes recorrida por el `ip`, así que controlar el flujo es **mover el `ip`**.
 
| Instrucción | Operando | Qué hace |
| :--- | :--- | :--- |
| `OP_JUMP` | offset | Salta siempre hacia adelante (`ip += offset`) |
| `OP_JUMP_IF_FALSE` | offset | Salta hacia adelante si el tope es falsey, sin sacarlo de la pila |
| `OP_LOOP` | offset | Salta hacia atrás (`ip -= offset`) |
 
- **Backpatching** Al compilar un `if` hay que emitir el salto antes de compilar el cuerpo, así que todavía no se sabe cuánto saltar. Se emite el salto con un operando provisorio, se compila el cuerpo y recién entonces se vuelve a esa posición a escribir el offset real. Los operandos de salto usan 2 bytes porque el cuerpo puede ser largo.

```python
def emit_jump(self, op: OpCode) -> int:
    self.emit(op, 0xFF, 0xFF)            # operando provisorio
    return len(self.chunk.code) - 2      # posición del operando, para parchearlo después

def patch_jump(self, at: int) -> None:
    offset = len(self.chunk.code) - at - 2
    if offset > 0xFFFF:
        raise CompileError(self.line, "El salto es demasiado largo.")
    self.chunk.code[at] = (offset >> 8) & 0xFF
    self.chunk.code[at + 1] = offset & 0xFF
```

- **`OP_JUMP_IF_FALSE` no saca la condición de la pila.** Solo la mira para decidir si salta. Por eso el compilador emite un `OP_POP` al principio de cada camino (el `then` y el `else`), así la condición se descarta pase lo que pase y la pila queda como estaba.
- **`while`.** Al final del cuerpo, `OP_LOOP` vuelve al inicio de la condición. Ese destino ya está compilado, así que no necesita backpatching. El salto de salida apunta hacia adelante y sí se parchea.
- **`for`.** No tiene instrucciones propias. El parser lo convierte en un `WhileStmt` que lleva el incremento como campo aparte, y el compilador lo emite al final del cuerpo, antes del `OP_LOOP`.
- **`and` y `or`.** Devuelven uno de los operandos y no un booleano, y se saltean el lado derecho cuando ya no hace falta evaluarlo. `and` usa un solo `OP_JUMP_IF_FALSE`. Si el lado izquierdo es falso salta al final y ese valor queda como resultado. `or` necesita dos saltos porque no existe un "saltar si es verdadero". Un `OP_JUMP_IF_FALSE` lleva al lado derecho y un `OP_JUMP` incondicional saltea ese lado cuando el izquierdo ya era verdadero.
- **`break` y `continue`.** Son un `OP_JUMP` hacia adelante que queda sin parchear. El compilador anota esos saltos en una pila de bucles abiertos (`Loop`) y los parchea después. El `break` apunta al final del bucle y el `continue` al incremento (o al fin del cuerpo si no hay). Antes de saltar descarta con `OP_POP` las locales declaradas dentro del bucle, para que la pila no quede desfasada. Para saber cuántas son, el `Loop` guarda cuántas había al entrar.

Así se compilan `and` y `or`. En `or` se ve la combinación de los dos saltos.

```python
def _(self, expr: LogicalExpr) -> None:
    self.gen_expr(expr.left)
    if expr.operator.kind == TokenKind.AND:
        end_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE)   # si es falso, ese valor es el resultado
        self.emit(OpCode.OP_POP)                             # si es verdadero, se descarta
        self.gen_expr(expr.right)
        self.patch_jump(end_jump)
    else:
        right_jump = self.emit_jump(OpCode.OP_JUMP_IF_FALSE) # si es falso, va a evaluar el lado derecho
        end_jump = self.emit_jump(OpCode.OP_JUMP)            # si es verdadero, saltea el lado derecho
        self.patch_jump(right_jump)
        self.emit(OpCode.OP_POP)                             # camino del falso, descarta el izquierdo
        self.gen_expr(expr.right)
        self.patch_jump(end_jump)
```

## Clases y herencia

Las clases funcionan en los dos backends. Una clase tiene métodos y puede heredar de otra con `<`. Dentro de un método, `this` es la instancia y `super` permite llamar al método de la superclase.



### En el intérprete puro

- **Clase e instancia.** `LoxClass` guarda el nombre, la superclase y sus métodos. Llamarla crea una `LoxInstance` (con su diccionario de campos) y corre el `init`. Para buscar un método, sube por la cadena de superclases hasta encontrarlo.

```python
def find_method(self, name: str) -> LoxFunction | None:
    klass: LoxClass | None = self
    while klass is not None:
        if name in klass.methods:
            return klass.methods[name]
        klass = klass.superclass          # si no está, sigue con la superclase
    return None
```

- **`this`.** Cuando se obtiene un método de una instancia, `bind` crea un entorno nuevo donde `this` apunta a esa instancia. Es el mismo mecanismo de closures de las funciones, solo que con una variable más.

```python
def bind(self, instance: "LoxInstance") -> LoxFunction:
    environment = Environment(enclosing=self.closure)
    environment.define("this", instance)
    return LoxFunction(self.declaration, environment, self.is_initializer)
```

- **`super`.** Si la clase tiene superclase, sus métodos cierran sobre un entorno extra apuntando con `super`. El Resolver calcula la distancia a ese entorno como para cualquier otra variable.
- **`init`.** Siempre devuelve la instancia, aunque no tenga `return`.

### En el compilador y la VM

La VM tiene sus propios valores para las clases. Una `Class` guarda su nombre y sus métodos, una `Instance` guarda su clase y sus campos, y un `BoundMethod` es un método ya ligado a su instancia.

- **Declarar una clase.** Se hace en tiempo de ejecución, en tres pasos. Se crea la clase vacía, si hereda se le copian los métodos de la superclase y por último se agrega cada método, compilado como un closure.
- **Los métodos se copian.** A diferencia del intérprete, que busca subiendo por la cadena de superclases, la VM copia los métodos heredados a la subclase al declararla. Los métodos propios se agregan después y pisan a los heredados. Como una clase no se modifica una vez declarada, el resultado es el mismo y buscar un método es una sola consulta.
- **`this`.** Es una variable local más. En un método, la posición 0 de la ventana (la que en una función común guarda el closure) guarda la instancia.
- **`super`.** Al compilar una subclase, la superclase queda como una variable local que los métodos capturan como upvalue. Así `super` siempre apunta a la superclase correcta, aunque después se cambie la variable original.
- **Llamar una clase o un método.** La VM distingue qué se está llamando. Si es una clase, crea la instancia y ejecuta su `init`. Si es un método ligado, pone la instancia en la posición 0 y ejecuta el método. En cualquier otro caso es una llamada común.



## Funcionalidades extra

Agregamos algunas funcionalidades que funcionan igual en los dos backends. 

- **Asignación compuesta (`+=`, `-=`, `*=`, `/=`, `%=`).** `a += b` es una forma abreviada de `a = a + b`. El parser la guarda como una asignación común, la misma que ya existía, que además recuerda qué operación hay que hacer. Al ejecutarla se lee el valor actual, se aplica la operación y se guarda el resultado.  

- **Módulo (`%`).** Operador binario, convierte los operandos a entero y devuelve un número. 

```python
case OpCode.OP_MODULO:
    b, a = stack.pop(), stack.pop()
    numbers(a, b)
    if b == 0:
        raise fail("Modulo por cero.")
    stack.append(float(int(a) % int(b)))
```

- **`break` y `continue`.** El scanner los reconoce como palabras clave y el parser genera un nodo para cada uno. En el compilador se traducen a saltos (ver [Saltos de flujo](#saltos-de-flujo)). En el intérprete puro se implementan con señales, igual que el `return`. `break` lanza una `BreakSignal` que corta el bucle más cercano y `continue` lanza una `ContinueSignal` que salta a la siguiente vuelta, ejecutando antes el incremento del `for`. En ambos backends es un error usarlos fuera de un bucle, y tampoco pueden cruzar el límite de una función.

```python
while self._is_truthy(self.evaluate(stmt.condition)):
    try:
        self.run(stmt.body)
    except BreakSignal:
        break
    except ContinueSignal:
        pass
    if stmt.increment is not None:      # el continue igual ejecuta el incremento
        self.evaluate(stmt.increment)
```

En `examples/clases.lox` hay un programa que usa clases, herencia, `super`, `+=`, `break` y `continue`.
