# Reporte: Lox vs Python vs JavaScript

Resultado de las pruebas de rendimiento, presentadas con un grafico y una tabla por benchmark, con el tiempo de proceso completo en segundos: minimo, promedio y maximo de varias corridas.

## Fib

**Que se probo:** Recursion y llamadas a funcion: calcula `fib(24)` de forma recursiva, la misma logica en los tres lenguajes.

![grafico fib](fib.png)

| Lenguaje | MIN (s) | AVG (s) | MAX (s) |
|---|---:|---:|---:|
| lox | 2.9316 | 2.9813 | 3.0297 |
| python | 0.0460 | 0.0499 | 0.0545 |
| javascript | 0.0409 | 0.0441 | 0.0494 |

## Loop

**Que se probo:** Loop apretado: un `while` de 200.000 iteraciones que en cada vuelta evalua una condicion, hace una suma y un incremento.

![grafico loop](loop.png)

| Lenguaje | MIN (s) | AVG (s) | MAX (s) |
|---|---:|---:|---:|
| lox | 4.1516 | 4.2111 | 4.3382 |
| python | 0.0563 | 0.0584 | 0.0624 |
| javascript | 0.0451 | 0.0469 | 0.0501 |

## Concatenación de strings

**Que se probo:** Creacion/descarte de strings: 50.000 concatenaciones sucesivas que arman una cadena de largo creciente.

![grafico string_concat](string_concat.png)

| Lenguaje | MIN (s) | AVG (s) | MAX (s) |
|---|---:|---:|---:|
| lox | 1.2025 | 1.2242 | 1.2517 |
| python | 0.0684 | 0.0725 | 0.0774 |
| javascript | 0.0443 | 0.0487 | 0.0548 |

## Nuestra implementacion vs plox (Catedra)

`plox` es la implementación de referencia de la cátedra en su rama [`full-tree-walk`](https://github.com/FdelMazo/plox/tree/full-tree-walk). Ambas implementaciones están escritas en Python, por lo que esta comparación permite enfocarnos principalmente en las diferencias entre nuestras implementaciones del intérprete, sin que el lenguaje en el que están escritas sea una diferencia entre ellas.

Las mediciones se realizaron con 5 repeticiones por benchmark, utilizando el mismo método que en la comparación anterior: se midió el tiempo total de ejecución de cada proceso y se ejecutó cada corrida mediante `subprocess`.

| Benchmark     | Lox MIN (s) | Lox AVG (s) | plox MIN (s) | plox AVG (s) |
| :------------ | ----------: | ----------: | -----------: | -----------: |
| fib           |      2.9316 |      2.9813 |       3.1433 |       3.1931 |
| loop          |      4.1516 |      4.2111 |       4.1343 |       4.1757 |
| string_concat |      1.2025 |      1.2242 |       1.2451 |       1.2594 |

### Conclusiones

Los resultados muestran que ambas implementaciones tienen un rendimiento bastante similar. Lox resulta ligeramente más rápido en `fib` y `string_concat`, mientras que `plox` es ligeramente más rápido en `loop`. Las diferencias son relativamente pequeñas, por lo que no se observa una ventaja significativa de una implementación sobre la otra en estos benchmarks.

Esto también sirve para poner en contexto la comparación anterior: la gran diferencia de rendimiento respecto de Python y JavaScript no se debe simplemente a que el código esté escrito en Python, ya que ambas implementaciones de Lox utilizan el mismo lenguaje. La diferencia está principalmente relacionada con la forma en que ejecutamos Lox.

En particular, nuestro intérprete recorre el AST para ejecutar cada operación. Esto agrega un costo adicional que se vuelve más visible en benchmarks como `loop` y `fib`, donde se realizan muchas operaciones pequeñas y repetitivas.

