# Clases: mide el costo de crear instancias, leer campos y llamar metodos.
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def sumar(self, otro):
        return Vector(self.x + otro.x, self.y + otro.y)


acc = Vector(0, 0)
paso = Vector(1, 2)
i = 0
while i < 30000:
    acc = acc.sumar(paso)
    i = i + 1
print(acc.x + acc.y)
