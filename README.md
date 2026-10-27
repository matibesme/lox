# Lox

Intérprete de Lox (*tree-walking*) hecho en Python.

**Integrantes:**
- Matías Besmedrisnik (Padrón: 110487)
- Gonzalo Nicolás Crudo (Padrón: 110816)

---

## Cómo correrlo

El proyecto usa [**uv**](https://docs.astral.sh/uv/) para manejar el entorno y las dependencias (requiere Python 3.12+).

Para instalar el comando `lox` de forma local:
```bash
uv tool install --editable .
```

### Modo interactivo
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

Elegimos la opción 1 del TP (implementar Lox en Python) siguiendo las etapas vistas en clase. A lo largo del desarrollo nos encontramos con varias decisiones técnicas y adaptaciones respecto al libro. La estrategia de implementacion fue no revisar el repo de plox mas alla de lo visto en clase. 

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
  - Lo hicimos asi porque en un árbol sintáctico lo que tiene **mayor precedencia debe quedar más profundo (más abajo)** para que se resuelva primero. Por ejemplo en `1 + 2 * 3`, la suma (`_term`) delega en la multiplicación (`_factor`). La multiplicación se agrupa primero como `(2 * 3)` y pasa a ser el operando derecho de la suma (`1 + (2 * 3)`).
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

