"""Invierte jugador <-> rival en un chart V-Slice (FNF 0.5+): d 0-3 (jugador) <-> 4-7 (rival) y FocusCamera 0 <-> 1.
Uso: python -I invertir_lados.py <ruta-chart.json> <ruta-respaldo.json>
Correrlo dos veces devuelve el chart original."""
import json, shutil, sys

src, bak = sys.argv[1], sys.argv[2]
shutil.copy2(src, bak)
c = json.load(open(src, encoding="utf-8"))
n_notas = 0
for dif, notas in c["notes"].items():
    for n in notas:
        n["d"] = (int(n["d"]) + 4) % 8
        n_notas += 1
n_cam = 0
for e in c.get("events", []):
    if e.get("e") == "FocusCamera" and isinstance(e.get("v"), dict) and str(e["v"].get("char")) in ("0", "1"):
        orig = e["v"]["char"]
        nuevo = "1" if str(orig) == "0" else "0"
        e["v"]["char"] = nuevo if isinstance(orig, str) else int(nuevo)
        n_cam += 1
json.dump(c, open(src, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"invertidas {n_notas} notas y {n_cam} eventos de camara; respaldo en {bak}")
