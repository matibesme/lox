// Clases: mide el costo de crear instancias, leer campos y llamar metodos.
class Vector {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }

    sumar(otro) {
        return new Vector(this.x + otro.x, this.y + otro.y);
    }
}

let acc = new Vector(0, 0);
const paso = new Vector(1, 2);
let i = 0;
while (i < 30000) {
    acc = acc.sumar(paso);
    i = i + 1;
}
console.log(acc.x + acc.y);
