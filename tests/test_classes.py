"""Pruebas de clases, instancias, metodos, `this`, inicializadores y herencia."""

from __future__ import annotations

import unittest

from lox_helpers import parse, parse_expression, run
from lox.errors import ErrorReporter
from lox.expr import CallExpr, GetExpr, SetExpr, SuperExpr, ThisExpr, VariableExpr
from lox.statement import ClassStmt, FunctionStmt


class TestParserClases(unittest.TestCase):
    def test_declaracion_de_clase_con_metodos(self):
        (stmt,) = parse("class A { f() {} g(x) {} }")
        self.assertIsInstance(stmt, ClassStmt)
        self.assertEqual(stmt.name.lexeme, "A")
        self.assertIsNone(stmt.superclass)
        self.assertEqual([m.name.lexeme for m in stmt.methods], ["f", "g"])
        self.assertTrue(all(isinstance(m, FunctionStmt) for m in stmt.methods))

    def test_declaracion_con_superclase(self):
        (stmt,) = parse("class B < A {}")
        self.assertIsInstance(stmt.superclass, VariableExpr)
        self.assertEqual(stmt.superclass.name.lexeme, "A")

    def test_acceso_a_propiedad_y_llamada_encadenada(self):
        expr = parse_expression("a.b.c()")
        self.assertIsInstance(expr, CallExpr)
        self.assertIsInstance(expr.callee, GetExpr)
        self.assertEqual(expr.callee.name.lexeme, "c")
        self.assertIsInstance(expr.callee.object, GetExpr)

    def test_asignacion_a_propiedad_es_set(self):
        expr = parse_expression("a.b = 1")
        self.assertIsInstance(expr, SetExpr)
        self.assertEqual(expr.name.lexeme, "b")
        self.assertIsNone(expr.operator)

    def test_this_y_super(self):
        self.assertIsInstance(parse_expression("this"), ThisExpr)
        expr = parse_expression("super.metodo")
        self.assertIsInstance(expr, SuperExpr)
        self.assertEqual(expr.method.lexeme, "metodo")

    def test_super_sin_punto_es_error_sintactico(self):
        reporter = ErrorReporter()
        parse("super;", reporter)
        self.assertTrue(reporter.had_error)


class TestClasesEInstancias(unittest.TestCase):
    def test_imprimir_clase_e_instancia(self):
        source = """
        class Bagel {}
        print Bagel;
        print Bagel();
        """
        self.assertEqual(run(source).lines, ["Bagel", "Bagel instance"])

    def test_campos_se_crean_al_asignarlos(self):
        source = """
        class Caja {}
        var c = Caja();
        c.valor = 42;
        print c.valor;
        c.valor = "otro";
        print c.valor;
        """
        self.assertEqual(run(source).lines, ["42", "otro"])

    def test_asignacion_a_campo_devuelve_el_valor(self):
        self.assertEqual(run("class A {} var a = A(); print a.x = 3;").lines, ["3"])

    def test_cada_instancia_tiene_sus_propios_campos(self):
        source = """
        class P {}
        var a = P();
        var b = P();
        a.x = 1;
        b.x = 2;
        print a.x;
        print b.x;
        """
        self.assertEqual(run(source).lines, ["1", "2"])

    def test_metodo_usa_this(self):
        source = """
        class Persona {
          saludar() { print "Hola, soy " + this.nombre; }
        }
        var p = Persona();
        p.nombre = "Ada";
        p.saludar();
        """
        self.assertEqual(run(source).lines, ["Hola, soy Ada"])

    def test_metodo_extraido_recuerda_su_this(self):
        source = """
        class Persona {
          nombre() { return this.n; }
        }
        var p = Persona();
        p.n = "Grace";
        var f = p.nombre;
        p = nil;
        print f();
        """
        self.assertEqual(run(source).lines, ["Grace"])

    def test_this_en_closure_dentro_de_metodo(self):
        source = """
        class Cosa {
          getCallback() {
            fun callback() { print this.nombre; }
            return callback;
          }
        }
        var c = Cosa();
        c.nombre = "cosa";
        c.getCallback()();
        """
        self.assertEqual(run(source).lines, ["cosa"])

    def test_campo_tapa_al_metodo_del_mismo_nombre(self):
        source = """
        class A { f() { return "metodo"; } }
        var a = A();
        print a.f();
        a.f = "campo";
        print a.f;
        """
        self.assertEqual(run(source).lines, ["metodo", "campo"])

    def test_igualdad_es_por_identidad(self):
        source = """
        class A {}
        var a = A();
        var b = A();
        print a == a;
        print a == b;
        """
        self.assertEqual(run(source).lines, ["true", "false"])

    def test_clase_puede_referirse_a_si_misma_en_un_metodo(self):
        source = """
        class Nodo {
          clonar() { return Nodo(); }
        }
        print Nodo().clonar();
        """
        self.assertEqual(run(source).lines, ["Nodo instance"])

    def test_clase_dentro_de_bloque(self):
        source = """
        {
          class Local { f() { return "local"; } }
          print Local().f();
        }
        """
        self.assertEqual(run(source).lines, ["local"])


class TestInicializadores(unittest.TestCase):
    def test_init_recibe_argumentos(self):
        source = """
        class Punto {
          init(x, y) { this.x = x; this.y = y; }
          suma() { return this.x + this.y; }
        }
        print Punto(2, 3).suma();
        """
        self.assertEqual(run(source).lines, ["5"])

    def test_aridad_de_la_clase_es_la_de_init(self):
        resultado = run("class P { init(a, b) {} } P(1);")
        self.assertTrue(resultado.reporter.had_runtime_error)
        self.assertIn("Se esperaban 2 argumentos pero se recibieron 1", resultado.output)

    def test_clase_sin_init_no_acepta_argumentos(self):
        resultado = run("class P {} P(1);")
        self.assertTrue(resultado.reporter.had_runtime_error)

    def test_llamar_init_directamente_devuelve_la_instancia(self):
        source = """
        class Foo { init() { this.n = 1; } }
        var foo = Foo();
        print foo.init();
        """
        self.assertEqual(run(source).lines, ["Foo instance"])

    def test_return_vacio_en_init_devuelve_la_instancia(self):
        source = """
        class Foo {
          init() {
            this.listo = true;
            return;
            this.listo = false;
          }
        }
        var f = Foo();
        print f.listo;
        print f.init();
        """
        self.assertEqual(run(source).lines, ["true", "Foo instance"])


class TestHerencia(unittest.TestCase):
    def test_subclase_hereda_metodos(self):
        source = """
        class Animal { hablar() { return "..."; } }
        class Perro < Animal {}
        print Perro().hablar();
        """
        self.assertEqual(run(source).lines, ["..."])

    def test_subclase_sobreescribe_metodo(self):
        source = """
        class Animal { hablar() { return "..."; } }
        class Perro < Animal { hablar() { return "Guau"; } }
        print Perro().hablar();
        print Animal().hablar();
        """
        self.assertEqual(run(source).lines, ["Guau", "..."])

    def test_super_llama_al_metodo_de_la_superclase(self):
        source = """
        class Donut {
          cocinar() { print "Freir hasta dorar."; }
        }
        class BostonCream < Donut {
          cocinar() {
            super.cocinar();
            print "Rellenar con crema.";
          }
        }
        BostonCream().cocinar();
        """
        self.assertEqual(run(source).lines, ["Freir hasta dorar.", "Rellenar con crema."])

    def test_super_en_init(self):
        source = """
        class Figura {
          init(nombre) { this.nombre = nombre; }
        }
        class Cuadrado < Figura {
          init(lado) {
            super.init("cuadrado");
            this.lado = lado;
          }
          area() { return this.lado * this.lado; }
        }
        var c = Cuadrado(3);
        print c.nombre;
        print c.area();
        """
        self.assertEqual(run(source).lines, ["cuadrado", "9"])

    def test_init_heredado(self):
        source = """
        class A { init(x) { this.x = x; } }
        class B < A {}
        print B(7).x;
        """
        self.assertEqual(run(source).lines, ["7"])

    def test_super_se_resuelve_estaticamente(self):
        # El caso clasico del libro: super se liga a la superclase de la clase
        # donde esta escrito el metodo, no a la de la instancia.
        source = """
        class A { metodo() { print "A"; } }
        class B < A {
          metodo() { print "B"; }
          probar() { super.metodo(); }
        }
        class C < B {}
        C().probar();
        """
        self.assertEqual(run(source).lines, ["A"])

    def test_cadena_de_herencia_larga(self):
        source = """
        class A { quien() { return "A"; } }
        class B < A {}
        class C < B {}
        class D < C {}
        print D().quien();
        """
        self.assertEqual(run(source).lines, ["A"])

    def test_metodo_de_super_extraido_conserva_this(self):
        source = """
        class A { nombre() { return this.n; } }
        class B < A {
          getNombre() { return super.nombre; }
        }
        var b = B();
        b.n = "bee";
        var f = b.getNombre();
        print f();
        """
        self.assertEqual(run(source).lines, ["bee"])


class TestErroresDeClases(unittest.TestCase):
    def _runtime_error(self, source: str, mensaje: str) -> None:
        resultado = run(source)
        self.assertTrue(resultado.reporter.had_runtime_error, resultado.output)
        self.assertIn(mensaje, resultado.output)

    def _static_error(self, source: str, mensaje: str) -> None:
        resultado = run(source)
        self.assertTrue(resultado.reporter.had_error, resultado.output)
        self.assertIn(mensaje, resultado.output)

    def test_propiedad_inexistente(self):
        self._runtime_error("class A {} A().nada;", "Propiedad no definida 'nada'")

    def test_propiedad_de_algo_que_no_es_instancia(self):
        self._runtime_error('var x = "texto"; x.largo;', "Solo las instancias tienen propiedades")

    def test_asignar_campo_a_algo_que_no_es_instancia(self):
        self._runtime_error("var x = 1; x.y = 2;", "Solo las instancias tienen campos")

    def test_superclase_que_no_es_clase(self):
        self._runtime_error('var NoClase = "x"; class A < NoClase {}', "La superclase debe ser una clase")

    def test_super_a_metodo_inexistente(self):
        self._runtime_error(
            "class A {} class B < A { f() { super.nada(); } } B().f();",
            "Propiedad no definida 'nada'",
        )

    def test_this_fuera_de_clase(self):
        self._static_error("print this;", "No se puede usar 'this' fuera de una clase")

    def test_this_en_funcion_suelta(self):
        self._static_error("fun f() { return this; }", "No se puede usar 'this' fuera de una clase")

    def test_super_fuera_de_clase(self):
        self._static_error("super.f();", "No se puede usar 'super' fuera de una clase")

    def test_super_en_clase_sin_superclase(self):
        self._static_error("class A { f() { super.f(); } }", "No se puede usar 'super' en una clase sin superclase")

    def test_clase_que_hereda_de_si_misma(self):
        self._static_error("class A < A {}", "Una clase no puede heredar de si misma")

    def test_return_con_valor_en_init(self):
        self._static_error("class A { init() { return 1; } }", "No se puede retornar un valor desde un inicializador")

    def test_return_con_valor_en_funcion_dentro_de_init_es_valido(self):
        source = """
        class A {
          init() {
            fun f() { return 1; }
            this.v = f();
          }
        }
        print A().v;
        """
        self.assertEqual(run(source).lines, ["1"])


if __name__ == "__main__":
    unittest.main()
