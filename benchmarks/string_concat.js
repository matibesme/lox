function repeat(n) {
    let s = "";
    let i = 0;
    while (i < n) {
        s = s + "x";
        i = i + 1;
    }
    return s;
}

repeat(50000);
console.log("OK");
