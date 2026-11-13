"""Mide los benchmarks de benchmarks/*.lox con nuestros dos backends (tree-walk y
VM de bytecode) contra programas equivalentes en Python y JavaScript (Node), y
genera benchmarks/report.md con una tabla y un grafico por benchmark.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BENCH_DIR = Path(__file__).parent
REPO_ROOT = BENCH_DIR.parent

BENCHMARKS = ["fib", "loop", "string_concat", "classes"]

DESCRIPTIONS = {
    "fib": (
        "Recursion y llamadas a funcion: calcula `fib(24)` de forma recursiva "
        "(sin memoizacion), la misma logica en todos los lenguajes."
    ),
    "loop": (
        "Loop apretado: un `while` de 200.000 iteraciones que en cada vuelta "
        "evalua una condicion, hace una suma y un incremento sobre variables globales."
    ),
    "string_concat": (
        "Creacion/descarte de strings: 50.000 concatenaciones sucesivas que "
        "arman una cadena de largo creciente (con variables locales)."
    ),
    "classes": (
        "Clases: 30.000 llamadas a un metodo que lee campos de dos instancias y "
        "crea una instancia nueva (pasa por `init`)."
    ),
}

LOX_SRC = REPO_ROOT / "src"


def _lox(stage: str | None):
    return lambda name: [
        sys.executable,
        "-c",
        f"import sys; sys.path.insert(0, {str(LOX_SRC)!r}); "
        f"import lox; sys.exit(lox._run_file({str(BENCH_DIR / f'{name}.lox')!r}, {stage!r}))",
    ]


RUNNERS = {
    "lox tree-walk": (_lox("interpreter"), None),
    "lox VM": (_lox(None), None),
    "python": (lambda name: [sys.executable, str(BENCH_DIR / f"{name}.py")], None),
    "javascript": (lambda name: ["node", str(BENCH_DIR / f"{name}.js")], None),
}

COLORS = {
    "lox tree-walk": "#eb6834",
    "lox VM": "#2a78d6",
    "python": "#1baf7a",
    "javascript": "#eda100",
    "plox (catedra)": "#6250d6",
}
TEXT = "#52514e"
GRID = "#e4e3df"


def time_run(cmd: list[str], cwd: Path | None) -> tuple[float, str]:
    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        raise RuntimeError(f"Comando fallo ({' '.join(cmd)}):\n{result.stdout}\n{result.stderr}")
    return elapsed, result.stdout.strip()


def run_all(runners: dict, repeats: int) -> dict[str, dict[str, list[float]]]:
    results: dict[str, dict[str, list[float]]] = {b: {} for b in BENCHMARKS}
    for benchmark in BENCHMARKS:
        outputs: dict[str, str] = {}
        for name, (build_cmd, cwd) in runners.items():
            cmd = build_cmd(benchmark)
            runs = [time_run(cmd, cwd) for _ in range(repeats)]
            results[benchmark][name] = [elapsed for elapsed, _ in runs]
            outputs[name] = runs[0][1]
            times = results[benchmark][name]
            print(f"{benchmark:<15}{name:<16}min={min(times):.4f}s  avg={sum(times) / len(times):.4f}s")
        # Todas las implementaciones tienen que calcular lo mismo
        if len(set(outputs.values())) != 1:
            raise RuntimeError(f"Salidas distintas en {benchmark}: {outputs}")
    return results


def _style(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def make_chart(benchmark: str, times: dict[str, list[float]], out_path: Path) -> None:
    names = list(times)
    mins = [min(times[n]) for n in names]
    fig, ax = plt.subplots(figsize=(6, 0.5 * len(names) + 1.2))
    bars = ax.barh(names, mins, color=[COLORS[n] for n in names], height=0.6)
    ax.invert_yaxis()
    ax.bar_label(bars, labels=[f"{m:.2f}s" for m in mins], padding=4, color=TEXT, fontsize=9)
    ax.set_xlabel("tiempo minimo (s, menos es mejor)", color=TEXT)
    ax.set_title(benchmark, loc="left", fontsize=11, fontweight="bold")
    ax.set_xlim(0, max(mins) * 1.18)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_speedup_chart(results: dict[str, dict[str, list[float]]], out_path: Path) -> None:
    speedups = [min(results[b]["lox tree-walk"]) / min(results[b]["lox VM"]) for b in BENCHMARKS]
    fig, ax = plt.subplots(figsize=(6, 0.5 * len(BENCHMARKS) + 1.2))
    bars = ax.barh(BENCHMARKS, speedups, color=COLORS["lox VM"], height=0.6)
    ax.invert_yaxis()
    ax.bar_label(bars, labels=[f"{s:.1f}x" for s in speedups], padding=4, color=TEXT, fontsize=9)
    ax.axvline(1, color=TEXT, linewidth=1)
    ax.set_xlabel("cuantas veces mas rapida es la VM que el tree-walk", color=TEXT)
    ax.set_title("VM vs tree-walk", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlim(0, max(speedups) * 1.18)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_report(
    results: dict[str, dict[str, list[float]]], repeats: int, out_path: Path
) -> None:
    names = list(next(iter(results.values())))
    best = {b: {n: min(results[b][n]) for n in names} for b in BENCHMARKS}

    lines = ["# Reporte de benchmarks", ""]
    lines.append(
        "Tiempo de proceso completo (incluye el arranque del runtime) en segundos: "
        f"minimo, promedio y maximo de {repeats} corridas por combinacion. "
        "Antes de comparar se verifica que todas las implementaciones impriman lo mismo."
    )
    lines.append("")
    lines.append(
        f"Maquina: {platform.system()} {platform.release()}, {platform.processor() or platform.machine()}, "
        f"Python {platform.python_version()}."
    )
    lines.append("")

    lines.append("## VM vs tree-walk")
    lines.append("")
    lines.append("![VM vs tree-walk](speedup.png)")
    lines.append("")
    lines.append("| benchmark | tree-walk (s) | VM (s) | VM mas rapida |")
    lines.append("|---|---:|---:|---:|")
    for b in BENCHMARKS:
        tw, vm = best[b]["lox tree-walk"], best[b]["lox VM"]
        lines.append(f"| {b} | {tw:.4f} | {vm:.4f} | {tw / vm:.1f}x |")
    lines.append("")

    for b in BENCHMARKS:
        lines.append(f"## {b}")
        lines.append("")
        lines.append(f"**Que se probo:** {DESCRIPTIONS[b]}")
        lines.append("")
        lines.append(f"![grafico {b}]({b}.png)")
        lines.append("")
        lines.append("| implementacion | min (s) | promedio (s) | max (s) |")
        lines.append("|---|---:|---:|---:|")
        for n in names:
            times = results[b][n]
            lines.append(f"| {n} | {min(times):.4f} | {sum(times) / len(times):.4f} | {max(times):.4f} |")
        lines.append("")

    if "plox (catedra)" in names:
        lines.append("## Lox vs plox (catedra)")
        lines.append("")
        lines.append("| benchmark | tree-walk (s) | VM (s) | plox (s) |")
        lines.append("|---|---:|---:|---:|")
        for b in BENCHMARKS:
            r = best[b]
            lines.append(f"| {b} | {r['lox tree-walk']:.4f} | {r['lox VM']:.4f} | {r['plox (catedra)']:.4f} |")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeats", type=int, default=5, help="Corridas por combinacion (default: 5)")
    parser.add_argument("--plox", type=Path, help="Carpeta de un checkout de plox para incluirlo en la comparacion")
    args = parser.parse_args()

    runners = dict(RUNNERS)
    if args.plox is not None:
        runners["plox (catedra)"] = (
            lambda name: [sys.executable, "-m", "plox", str((BENCH_DIR / f"{name}.lox").resolve())],
            args.plox.resolve(),
        )

    results = run_all(runners, args.repeats)
    for benchmark in BENCHMARKS:
        make_chart(benchmark, results[benchmark], BENCH_DIR / f"{benchmark}.png")
    make_speedup_chart(results, BENCH_DIR / "speedup.png")
    make_report(results, args.repeats, BENCH_DIR / "report.md")
    print("\nReporte generado en benchmarks/report.md y benchmarks/*.png")


if __name__ == "__main__":
    main()
