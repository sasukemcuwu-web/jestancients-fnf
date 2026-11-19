"""JestAncients: mod de FNF (V-Slice 0.8) de Juan. Varias canciones de Toby Fox sacadas de charts de Clone Hero:
  - Black Knife (vs Caballero), Death by Glamour (vs Mettaton EX), Megalovania (vs Sans), y Penumbra Phantasm (su propio pipeline).
Por canción (tabla CANCIONES):
  - parte principal: la indicada o la que más notas tenga; 5 trastes -> 4 flechas (V R A Az N -> ← ↓ ↑ → →),
    acordes de 3+ -> 2 flechas (la más baja y la más alta), abiertas -> ↓, largas si duran >= media negra.
  - turnos de 4 compases con la parte principal: el rival presenta una frase y el jugador la siguiente.
  - Normal/Easy: se ralean (separación mínima 160/320 ms, sin acordes en Easy).
  - Mismo retraso de juego que Penumbra (manual/desfase_juego_ms.txt).
  - rival desde una hoja de 8 poses (4x2) generada con ChatGPT; si la hoja no está, la canción se salta.
Uso: construir.py   (escribe blackknife/mod/JestAncients y lo instala en el FNF del PC)
"""
import json, re, shutil, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

RAIZ = Path(__file__).resolve().parent
CANC = RAIZ.parent / "jestancients-canciones"
MOD = RAIZ / "mod" / "JestAncients"
JUEGO = Path(r"C:\Users\USUARIO\Desktop\jestalvz\archivo\escritorio\juegos\friday-night-funkin-0-8-6-0\mods")
DJ = float((RAIZ.parent / "manual/desfase_juego_ms.txt").read_text(encoding="utf-8-sig").strip())

# rejilla: color de las líneas por escenario
CANCIONES = [
    dict(id="black-knife", nombre="Black Knife", artista="Toby Fox", charter="Gooba", ch=RAIZ / "ch", audio="song.opus",
         partes=("ExpertSingle", "ExpertDoubleBass"), rival="jestCaballero", rival_nombre="Caballero", prefijo="caballero",
         hoja=RAIZ / "caballero-poses.png", escala=2.0, escenario="jestAncientsNoche", rejilla=(40, 46, 110), fondo=(6, 6, 14),
         estilo_fondo="surreal", contorno=(255, 255, 255)),   # ambiente de la portada de Black Knife de surreal (violeta, estática pixelada)
    dict(id="death-by-glamour", nombre="Death by Glamour", artista="Toby Fox", charter="The Aftermath",
         ch=CANC / "death-by-glamour/ch", audio="guitar.opus", partes=("ExpertKeyboard",), partes_erect=("ExpertKeyboard", "ExpertSingle"),
         rival="jestMettaton", rival_nombre="Mettaton EX", prefijo="mettaton", hoja=CANC / "death-by-glamour/mettaton-poses.png",
         escala=1.25, escenario="jestAncientsGlamour", rejilla=(120, 30, 90), fondo=(14, 4, 12)),
    dict(id="megalovania", nombre="Megalovania", artista="Toby Fox (cover de RichaadEB)", charter="Newt",
         ch=CANC / "megalovania/ch", audio="song.opus", partes=("ExpertSingle",),
         rival="jestSans", rival_nombre="Sans", prefijo="sans", hoja=CANC / "megalovania/sans-poses.png",
         escala=1.25, escenario="jestAncientsSans", rejilla=(30, 60, 120), fondo=(2, 4, 10)),
]


# ---------- leer un .chart ----------
def leer_chart(ruta):
    txt = ruta.read_text(encoding="utf-8-sig", errors="replace")
    sec = dict(re.findall(r"\[(\w+)\]\s*\{(.*?)\}", txt, re.S))
    res = int(re.search(r"Resolution\s*=\s*(\d+)", sec["Song"]).group(1))
    bpms = sorted((int(t), int(v) / 1000) for t, v in re.findall(r"(\d+)\s*=\s*B\s+(\d+)", sec["SyncTrack"]))
    def ms(tick):
        acum, prev_tick, bpm = 0.0, 0, bpms[0][1]
        for tk, b in bpms:
            if tk > tick: break
            acum += (tk - prev_tick) / res * 60000 / bpm; prev_tick, bpm = tk, b
        return acum + (tick - prev_tick) / res * 60000 / bpm
    def notas(seccion):
        por_tick = {}
        for tk, f, ln in re.findall(r"(\d+)\s*=\s*N\s+(\d+)\s+(\d+)", sec.get(seccion, "")):
            tk, f, ln = int(tk), int(f), int(ln)
            if f in (5, 6): continue          # forzada / tap: modificadores
            por_tick.setdefault(tk, []).append((f, ln))
        out = []
        for tk, fs in sorted(por_tick.items()):
            trastes = sorted({f for f, _ in fs}); largo = max(l for _, l in fs)
            carriles = sorted({1 if f == 7 else min(f, 3) for f in trastes})
            if len(carriles) > 2: carriles = [carriles[0], carriles[-1]]
            if len(trastes) >= 2 and len(carriles) == 1:   # acorde que colapsó (B+N): abrir a 2 flechas
                carriles = [max(0, carriles[0] - 1), carriles[0]]
            t = ms(tk); l = ms(tk + largo) - t if largo >= res // 2 else 0
            out.append((round(t, 1), carriles, round(l, 1)))
        return out
    return ms, notas, bpms


def hacer_jugable(lst, gap_min=115, jack_ms=200, max_por_seg=8):
    """Black Knife se sentía injugable (444 jacks < 200 ms, picos de 10 notas/s, 55 % en ↓). Criterios de Juan:
    nada de jacks rápidos (pasan al carril vecino siguiendo el gesto), separación mínima, máx. ~8 pulsaciones/s
    en ventanas de 1 s, y la abierta del bajo no siempre en ↓ (alterna ↓/↑ para no amontonar)."""
    out, ult_t, lane_t, abierta_alt, prev_lane = [], -9e9, {}, 0, 1
    ventana = []
    for t, cs, l in lst:
        if t - ult_t < gap_min: continue
        ventana = [x for x in ventana if t - x < 1000]
        if len(ventana) >= max_por_seg: continue
        cs = list(cs)
        if cs == [1]:                    # abiertas/verdes que caen en ↓: alternar ↓ ↑
            cs = [1 if abierta_alt % 2 == 0 else 2]; abierta_alt += 1
        nuevos = []
        for k in cs:
            if k in lane_t and t - lane_t[k] < jack_ms:
                paso = 1 if k >= prev_lane else -1
                for cand in (k + paso, k - paso, k + 2 * paso, k - 2 * paso):
                    if 0 <= cand <= 3 and cand not in nuevos and (cand not in lane_t or t - lane_t[cand] >= jack_ms):
                        k = cand; break
                else:
                    continue           # no hay carril libre: se omite esa flecha
            if k not in nuevos: nuevos.append(k)
        if not nuevos: continue
        for k in nuevos: lane_t[k] = t
        prev_lane = nuevos[-1]
        out.append((t, sorted(nuevos), l)); ult_t = t; ventana.append(t)
    return variar(equilibrar(out, jack_ms))


def variar(lst, ventana=6):
    """Juan (18 nov): más variedad de patrones. Los tramos largos de notas sueltas que solo usan 2 carriles (↓↑↓↑…)
    se vuelven escaleras de 4 carriles (←↓↑→ / →↑↓←, alternando sentido en cada tramo); un carril no se repite
    antes de 4 notas, así que no aparecen jacks. Las frases con acordes o que ya usan 3-4 carriles no se tocan."""
    lst = [(t, list(cs), l) for t, cs, l in lst]
    suelta = lambda k: len(lst[k][1]) == 1
    i, sentido = 0, 0
    while i < len(lst) - 2:
        # trino: sueltas A B A B ... (cada nota igual a la de dos atrás y distinta a la anterior), sin huecos > 400 ms
        j = i + 2
        if suelta(i) and suelta(i + 1) and lst[i][1] != lst[i + 1][1]:
            while j < len(lst) and suelta(j) and lst[j][1] == lst[j - 2][1] and lst[j][0] - lst[j - 1][0] < 400:
                j += 1
        if j - i >= ventana - 1:
            # primer par se queda (ancla el gesto); desde la 3.ª nota sigue una escalera de 4 carriles
            # dibujos de 4 que rotan entre trinos (cada carril se repite cada 4 notas: sin jacks); incluye el barrido R U D L de Juan
            DIBUJOS = [[0, 1, 2, 3], [3, 2, 1, 0], [0, 2, 1, 3], [3, 1, 2, 0], [1, 3, 0, 2], [2, 0, 3, 1]]
            esc = DIBUJOS[sentido % len(DIBUJOS)]
            pos = esc.index(lst[i + 1][1][0])
            for n in range(i + 2, j):
                pos = (pos + 1) % 4
                lst[n] = (lst[n][0], [esc[pos]], lst[n][2])
            sentido += 1
            i = j
        else:
            i += 1
    # repaso final: ningún jack < 200 ms (mueve la flecha al carril libre más cercano)
    ult = {}
    for n, (t, cs, l) in enumerate(lst):
        nuevos = []
        for k in cs:
            if k in ult and t - ult[k] < 200:
                for cand in (k + 1, k - 1, k + 2, k - 2, k + 3, k - 3):
                    if 0 <= cand <= 3 and cand not in nuevos and (cand not in ult or t - ult[cand] >= 200):
                        k = cand; break
            if k not in nuevos: nuevos.append(k)
        for k in nuevos: ult[k] = t
        lst[n] = (t, nuevos, l)
    return [(t, sorted(cs), l) for t, cs, l in lst]


def equilibrar(lst, jack_ms=200, tope=0.34):
    """Ningún carril con más del ~34 % de las flechas (Juan usa ↓↑ de base y ← → para acentos, ~40 %):
    las notas sueltas del carril sobrecargado pasan al vecino menos usado, sin crear jacks."""
    lst = [(t, list(cs), l) for t, cs, l in lst]
    for _ in range(3):
        cuenta = [sum(k == c for _, cs, _ in lst for c in cs) for k in range(4)]
        total = sum(cuenta)
        lleno = max(range(4), key=lambda k: cuenta[k])
        if cuenta[lleno] <= tope * total: break
        sobra = int(cuenta[lleno] - tope * total)
        for i, (t, cs, l) in enumerate(lst):
            if sobra <= 0: break
            if cs != [lleno] or i % 2: continue          # solo sueltas, una sí una no para no romper frases
            vecinos = sorted((v for v in (lleno - 1, lleno + 1, lleno - 2, lleno + 2) if 0 <= v <= 3), key=lambda v: cuenta[v])
            for v in vecinos:
                cerca = [x for x in lst[max(0, i - 3):i + 4] if x is not lst[i] and abs(x[0] - t) < jack_ms and v in x[1]]
                if not cerca:
                    lst[i] = (t, [v], l); cuenta[lleno] -= 1; cuenta[v] += 1; sobra -= 1; break
    return [(t, sorted(cs), l) for t, cs, l in lst]


def construir_cancion(c):
    ms, notas, bpms = leer_chart(c["ch"] / "notes.chart")
    cand = [(p, notas(p)) for p in c["partes"]]
    parte, jug = max(cand, key=lambda x: len(x[1]))
    print(f"{c['id']}: parte principal {parte} ({len(jug)} pulsaciones)")
    MED = 2 * 60000 / bpms[0][1]
    BLOQUE = 8 * MED   # 4 compases
    primer = min(t for t, _, _ in jug)
    turno = lambda t: int((t - primer) // BLOQUE) % 2   # 0 = rival presenta, 1 = jugador
    base = jug
    base_erect = base
    if c.get("partes_erect"):
        union = {}
        for p in c["partes_erect"]:
            for t, cs, l in notas(p):
                k = round(t / 40)
                if k not in union: union[k] = (t, cs, l)
        base_erect = sorted(union.values())

    def a_notas(lst, lado, acordes):
        out = []
        for t, cs, l in lst:
            for k in (cs if acordes else cs[:1]):
                n = {"t": round(t + DJ, 1), "d": k + (4 if lado else 0)}
                if l: n["l"] = l
                out.append(n)
        return out

    # Juan (18 nov): la distribución ya está bien, pero quedó muy fácil -> volver a la cantidad original,
    # sin amontonar: separación mínima por dificultad y tope por segundo; los jacks se arreglan cambiando de carril.
    NIVELES = {  # dificultad: (separación mínima ms, máx. pulsaciones por segundo, acordes, turnos)
        "easy": (260, 4, False, True), "normal": (150, 6, True, True), "hard": (95, 9, True, True),
        "erect": (75, 11, True, True),
        "nightmare": (75, 11, True, False),   # sin turnos: el jugador toca TODA la parte y el rival la canta a la vez (dúo)
    }
    chart_notes = {}
    for dif, (gap, mps, ac, turnos) in NIVELES.items():
        lst = hacer_jugable(base_erect if dif in ("erect", "nightmare") else base, gap_min=gap, max_por_seg=mps)
        if turnos:
            riv = [n for n in lst if turno(n[0]) == 0]; jug_ = [n for n in lst if turno(n[0]) == 1]
        else:
            riv, jug_ = lst, lst
        chart_notes[dif] = sorted(a_notas(jug_, 0, ac) + a_notas(riv, 1, ac), key=lambda n: (n["t"], n["d"]))

    def camara(notas_ref, solo_jugador=False):
        ev, actual, k = [], None, 0
        fin = max(n["t"] for n in notas_ref)
        while k * MED < fin + MED:
            a, b = k * MED + DJ, (k + 1) * MED + DJ
            j_ = any(a <= n["t"] < b and n["d"] < 4 for n in notas_ref); r_ = any(a <= n["t"] < b and n["d"] >= 4 for n in notas_ref)
            quien = 0 if (j_ and not (solo_jugador and r_ and k % 8 < 4)) else (1 if r_ else actual)
            if quien is not None and quien != actual:
                ev.append({"t": round(max(0, a - 500), 1), "e": "FocusCamera", "v": {"char": quien, "duration": 10, "ease": "sineInOut"}})
                actual = quien
            k += 1
        ev.append({"t": 0.0, "e": "SetCameraBop", "v": {"rate": 2, "intensity": 1.1}})
        return sorted(ev, key=lambda e: e["t"])

    S = c["id"]
    (MOD / f"data/songs/{S}").mkdir(parents=True, exist_ok=True); (MOD / f"songs/{S}").mkdir(parents=True, exist_ok=True)
    gen = f"Elías (desde el chart de Clone Hero de {c['charter']})"
    chart = {"version": "2.0.0", "scrollSpeed": {"easy": 2.0, "normal": 2.4, "hard": 2.8, "default": 2.4},
             "events": camara(chart_notes["hard"]), "notes": {d: chart_notes[d] for d in ("easy", "normal", "hard")}, "generatedBy": gen}
    (MOD / f"data/songs/{S}/{S}-chart.json").write_text(json.dumps(chart), encoding="utf-8")
    # variación "erect" (Erect + Nightmare) con el mismo instrumental (Inst.ogg)
    chart_e = {"version": "2.0.0", "scrollSpeed": {"erect": 3.1, "nightmare": 3.3, "default": 3.1},
               "events": camara(chart_notes["erect"]), "notes": {d: chart_notes[d] for d in ("erect", "nightmare")}, "generatedBy": gen}
    (MOD / f"data/songs/{S}/{S}-chart-erect.json").write_text(json.dumps(chart_e), encoding="utf-8")
    personajes = {"player": "bf", "girlfriend": "", "opponent": c["rival"], "opponentVocals": [], "playerVocals": [], "instrumental": ""}
    tiempos = [{"t": round(ms(tk), 2), "bpm": b} for tk, b in bpms]
    meta = {"version": "2.2.4", "songName": c["nombre"], "artist": c["artista"], "charter": f"{c['charter']} (Clone Hero) / Elías",
            "offsets": {}, "playData": {"songVariations": ["erect"], "difficulties": ["easy", "normal", "hard"],
            "characters": personajes, "stage": c["escenario"], "noteStyle": "funkin", "ratings": {"easy": 3, "normal": 6, "hard": 9}},
            "generatedBy": "Elías", "timeChanges": tiempos}
    (MOD / f"data/songs/{S}/{S}-metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    meta_e = {"version": "2.2.4", "songName": c["nombre"] + " Erect", "artist": c["artista"], "charter": f"{c['charter']} (Clone Hero) / Elías",
              "offsets": {}, "playData": {"songVariations": [], "difficulties": ["erect", "nightmare"],
              "characters": personajes, "stage": c["escenario"], "noteStyle": "funkin", "ratings": {"erect": 12, "nightmare": 15}},
              "generatedBy": "Elías", "timeChanges": tiempos}
    (MOD / f"data/songs/{S}/{S}-metadata-erect.json").write_text(json.dumps(meta_e, indent=1), encoding="utf-8")
    print("  " + ", ".join(f"{d}: {sum(1 for n in chart_notes[d] if n['d'] < 4)} tuyas" for d in NIVELES))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(c["ch"] / c["audio"]), "-c:a", "libvorbis", "-q:a", "6",
                    str(MOD / f"songs/{S}/Inst.ogg")], check=True)
    escenario(c)
    idle = personaje_desde_hoja(c["hoja"], c["rival"], c["prefijo"], c["escala"], c["rival_nombre"], c.get("contorno", (190, 205, 255)),
                                c.get("recorte_celda", 0))
    print(f"  {S}: rival {c['rival']}")
    return idle


# ---------- escenario: noche oscura con rejilla de color (imagen ya coloreada, a tamaño real) ----------
def fondo_surreal(GW, GH, PX=8, semilla=7):
    """Ambiente de la portada de Black Knife de surreal: estática violeta/azul en vetas horizontales (agua con glitch),
    pixelada, con un mosaico claro detrás del rival (como el halo del caballero en la portada)."""
    from scipy import ndimage
    w, h = GW // PX, GH // PX
    rng = np.random.default_rng(semilla)
    ruido = rng.random((h, w))
    vetas = ndimage.uniform_filter(ruido, size=(1, 28), mode="wrap")          # largas en horizontal
    vetas = (vetas - vetas.min()) / (vetas.max() - vetas.min())
    vetas = 0.65 * vetas + 0.35 * ndimage.uniform_filter(rng.random((h, w)), size=(2, 9), mode="wrap")
    yy = np.linspace(0, 1, h)[:, None]
    base = np.clip(vetas + 0.25 * (yy - 0.4), 0, 1)                            # más violeta abajo
    pal = np.array([(14, 6, 58), (34, 14, 140), (58, 26, 200), (92, 40, 226), (128, 60, 236), (168, 110, 248)], float)
    idx = np.clip((base * (len(pal) - 1)), 0, len(pal) - 1.001)
    i0 = idx.astype(int); fr = (idx - i0)[..., None]
    img = pal[i0] * (1 - fr) + pal[np.minimum(i0 + 1, len(pal) - 1)] * fr
    # mosaico claro detrás del rival (dad en x≈300, pies y≈900 del mundo -> coords del fondo)
    cx, cy = (300 + GW // 2 - 640) / PX + 18, (900 + GH // 2 - 360) / PX - 45
    Y, X = np.mgrid[0:h, 0:w]
    r = np.sqrt(((X - cx) / 42) ** 2 + ((Y - cy) / 64) ** 2)
    prob = np.clip(1.15 - r, 0, 1) ** 0.8
    blq = (rng.random((h // 2 + 1, w // 2 + 1)) < 0.72).repeat(2, 0).repeat(2, 1)[:h, :w]   # bloques de 2x2
    luz = np.array([200, 186, 255], float) * (0.75 + 0.25 * rng.random((h, w, 1)))
    m = (blq & (rng.random((h, w)) < prob))[..., None]
    img = np.where(m, img * 0.35 + luz * 0.65, img)
    # viñeta
    xx = np.linspace(-1, 1, w)[None, :]; yv = np.linspace(-1, 1, h)[:, None]
    img *= np.clip(1 - 0.45 * (xx ** 2 + yv ** 2), 0.35, 1)[..., None]
    img = np.clip(img, 0, 255).astype(np.uint8).repeat(PX, 0).repeat(PX, 1)
    return img[:GH, :GW]


def escenario(c):
    GW, GH, P = 3200, 2000, 64
    if c.get("estilo_fondo") == "surreal":
        img = fondo_surreal(GW, GH)
    else:
        img = np.zeros((GH, GW, 3), np.uint8); img[...] = c["fondo"]
        img[::P, :] = c["rejilla"]; img[:, ::P] = c["rejilla"]
        yy = np.linspace(-1, 1, GH)[:, None]; xx = np.linspace(-1, 1, GW)[None, :]
        vin = np.clip(1 - 0.55 * (xx ** 2 + yy ** 2), 0.25, 1)
        img = (img * vin[..., None]).astype(np.uint8)
    nom = c["escenario"]
    (MOD / "images/stages/jestancients").mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGB").save(MOD / f"images/stages/jestancients/{nom}.png", optimize=True)
    stage = {"version": "1.0.0", "name": f"JestAncients: {c['nombre']}", "cameraZoom": 0.8,
             "props": [{"name": "fondo", "assetPath": f"stages/jestancients/{nom}", "position": [640 - GW // 2, 360 - GH // 2],
                        "scroll": [0.05, 0.05], "zIndex": 1, "scale": [1, 1], "isPixel": True, "danceEvery": 0, "animations": []}],
             "characters": {"bf": {"zIndex": 300, "position": [1220, 860], "cameraOffsets": [-120, -60]},
                            "dad": {"zIndex": 200, "position": [300, 900], "cameraOffsets": [200, 40], "scale": 1.0},
                            "gf": {"zIndex": 100, "position": [820, 820], "cameraOffsets": [0, 0]}}}
    (MOD / f"data/stages/{nom}.json").write_text(json.dumps(stage, indent=1), encoding="utf-8")


# ---------- personaje rival desde la hoja 4x2 ----------
def personaje_desde_hoja(hoja_png, ident, prefijo, escala, nombre, contorno=(190, 205, 255), recorte=0):
    """recorte = fracción de cada celda que se descarta en los bordes (líneas de cuadrícula / etiquetas abajo)."""
    hoja = Image.open(hoja_png).convert("RGBA"); W, H = hoja.width / 4, hoja.height / 2
    celdas = []
    for fila in range(2):
        for col in range(4):
            m_x, m_y = W * recorte, H * recorte
            c = hoja.crop((round(col * W + m_x), round(fila * H + m_y), round((col + 1) * W - m_x), round((fila + 1) * H - m_y * (3 if recorte else 1))))
            arr = np.array(c)
            if arr[..., 3].min() == 255:   # sin transparencia: quitar el fondo del color de las esquinas
                esq = np.median(np.concatenate([arr[:6, :6, :3].reshape(-1, 3), arr[-6:, -6:, :3].reshape(-1, 3)]), axis=0)
                rgb = arr[..., :3].astype(int)
                if esq[1] > 180 and esq[0] < 100 and esq[2] < 100:   # fondo verde: llave de croma + quitar el reflejo verde
                    fondo = (rgb[..., 1] > 120) & (rgb[..., 1] > rgb[..., 0] + 50) & (rgb[..., 1] > rgb[..., 2] + 50)
                    arr[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]) + 20).astype(np.uint8)
                else:
                    fondo = np.abs(rgb - esq).sum(-1) < 60
                    # solo el fondo conectado al borde (no el negro del personaje)
                    from scipy import ndimage
                    lab, _ = ndimage.label(fondo)
                    borde_ids = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
                    fondo = np.isin(lab, borde_ids[borde_ids > 0])
                arr[..., 3] = np.where(fondo, 0, 255)
                c = Image.fromarray(arr)
            a = np.array(c)[..., 3]; m = np.where(a > 12, 255, 0).astype("uint8")
            c.putalpha(Image.fromarray(np.minimum(a, m))); bb = Image.fromarray(m).getbbox()
            c = c.crop(bb) if bb else c
            # contorno claro de 4 px para que se lea sobre el fondo oscuro
            c2 = Image.new("RGBA", (c.width + 16, c.height + 16), (0, 0, 0, 0)); c2.alpha_composite(c, (8, 8))
            borde = c2.getchannel("A").filter(ImageFilter.MaxFilter(9))
            capa = Image.new("RGBA", c2.size, (*contorno, 0)); capa.putalpha(borde.point(lambda v: 230 if v > 40 else 0))
            capa.alpha_composite(c2); celdas.append(capa)
    idleA, idleB, izq, abajo, arriba, der, poder, golpe = celdas
    poses = {"idle": [idleA, idleA, idleB, idleB, idleB, idleA], "singLEFT": [izq], "singDOWN": [abajo], "singUP": [arriba],
             "singRIGHT": [der], "poder": [poder], "golpe": [golpe]}
    CW = max(c.width for c in celdas) + 40; CHh = max(c.height for c in celdas) + 40
    def lienzo(im, e=1.0, dy=0):
        if e != 1.0: im = im.resize((round(im.width * e), round(im.height * e)), Image.NEAREST)
        base = Image.new("RGBA", (CW, CHh), (0, 0, 0, 0)); base.alpha_composite(im, ((CW - im.width) // 2, CHh - 20 - im.height + dy)); return base
    frames = []
    for anim, lst in poses.items():
        if anim == "idle":
            for i, im in enumerate(lst): frames.append((f"{prefijo} idle{i:04d}", lienzo(im)))
        else:
            for i, im in enumerate([lienzo(lst[0], 1.06, -6), lienzo(lst[0], 1.03, -3), lienzo(lst[0]), lienzo(lst[0])]):
                frames.append((f"{prefijo} {anim}{i:04d}", im))
    COLS = 6; filas = (len(frames) + COLS - 1) // COLS
    atlas = Image.new("RGBA", (COLS * CW, filas * CHh), (0, 0, 0, 0))
    xml = ['<?xml version="1.0" encoding="utf-8"?>', f'<TextureAtlas imagePath="{ident}.png">']
    for i, (nom, im) in enumerate(frames):
        x, y = (i % COLS) * CW, (i // COLS) * CHh; atlas.alpha_composite(im, (x, y))
        xml.append(f'  <SubTexture name="{nom}" x="{x}" y="{y}" width="{CW}" height="{CHh}"/>')
    xml.append("</TextureAtlas>")
    atlas.save(MOD / f"images/characters/{ident}.png", optimize=True)
    (MOD / f"images/characters/{ident}.xml").write_text("\n".join(xml), encoding="utf-8")
    ico = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
    for i, src in enumerate((idleA, golpe)):
        t = src.copy(); t.thumbnail((150, 150), Image.NEAREST); ico.alpha_composite(t, (i * 150 + (150 - t.width) // 2, 150 - t.height))
    ico.save(MOD / f"images/icons/icon-{ident}.png")
    # miniatura del freeplay (convención de Kapi: images/freeplay/icons/<healthIconId>pixel.png, 50x50 pixel art)
    (MOD / "images/freeplay/icons").mkdir(parents=True, exist_ok=True)
    fp = idleA.copy(); bb = fp.getchannel("A").getbbox(); fp = fp.crop(bb) if bb else fp
    lado = max(fp.width, fp.height); cuad = Image.new("RGBA", (lado, lado), (0, 0, 0, 0)); cuad.alpha_composite(fp, ((lado - fp.width) // 2, (lado - fp.height) // 2))
    cuad.resize((50, 50), Image.NEAREST).save(MOD / f"images/freeplay/icons/{ident}pixel.png")
    an = lambda n, p, fps: {"name": n, "prefix": f"{prefijo} {p}", "frameRate": fps, "looped": False, "offsets": [0, 0], "flipX": False, "flipY": False}
    ch = {"version": "1.0.0", "name": nombre, "danceEvery": 2, "scale": escala, "offsets": [0, 0], "flipX": False, "singTime": 6,
          "startingAnimation": "idle", "isPixel": True, "assetPath": f"characters/{ident}",
          "healthIcon": {"id": ident, "offsets": [0, 0], "flipX": False, "isPixel": True, "scale": 1},
          "animations": [an("idle", "idle", 10), an("singLEFT", "singLEFT", 24), an("singDOWN", "singDOWN", 24), an("singUP", "singUP", 24),
                         an("singRIGHT", "singRIGHT", 24), an("poder", "poder", 24), an("golpe", "golpe", 24)]}
    (MOD / f"data/characters/{ident}.json").write_text(json.dumps(ch, indent=1), encoding="utf-8")
    return idleA


# ---------- armar el mod ----------
if MOD.exists(): shutil.rmtree(MOD)
for d in ("data/characters", "data/stages", "data/levels", "images/characters", "images/icons", "images/stages/jestancients",
          "images/storymenu/titles", "images/storymenu/props"):
    (MOD / d).mkdir(parents=True, exist_ok=True)
canciones, idle_cab = [], None
for c in CANCIONES:
    if not c["hoja"].exists():
        print(f"{c['id']}: falta la hoja de poses {c['hoja'].name}, se salta"); continue
    idle = construir_cancion(c); canciones.append(c["id"])
    if idle_cab is None: idle_cab = idle

f = None
for nombre in ("arialbd.ttf", "arial.ttf"):
    try: f = ImageFont.truetype(nombre, 64); break
    except Exception: pass
titulo = Image.new("RGBA", (620, 90), (0, 0, 0, 0)); ImageDraw.Draw(titulo).text((10, 8), "JESTANCIENTS", font=f, fill=(235, 235, 255, 255))
titulo.save(MOD / "images/storymenu/titles/jestancients.png")
# Penumbra Phantasm también va dentro de JestAncients (un solo mod de Juan)
PEN = RAIZ.parent / "penumbra" / "fnf-mod" / "Penumbra Phantasm"
if PEN.exists():
    for sub in ("data", "images", "songs", "scripts"):
        if (PEN / sub).exists(): shutil.copytree(PEN / sub, MOD / sub, dirs_exist_ok=True)
    viejo_nivel = MOD / "data/levels/penumbra.json"
    if viejo_nivel.exists(): viejo_nivel.unlink()   # una sola semana: JestAncients
    canciones += ["penumbra-phantasm-piano", "penumbra-phantasm"]
    print("Penumbra Phantasm incluido en JestAncients")
level = {"version": "1.0.0", "name": "JESTANCIENTS", "titleAsset": "storymenu/titles/jestancients", "background": "#06060E",
         "props": [{"assetPath": "storymenu/props/bf", "scale": 1.0, "offsets": [150, 80],
                    "animations": [{"name": "idle", "prefix": "idle0", "frameRate": 24}, {"name": "confirm", "prefix": "confirm0", "frameRate": 24}]}],
         "songs": canciones}
(MOD / "data/levels/jestancients.json").write_text(json.dumps(level, indent=1), encoding="utf-8")
(MOD / "_polymod_meta.json").write_text(json.dumps({
    "title": "JestAncients", "description": "Mod de Juan (JestAncients): Black Knife, Death by Glamour, Megalovania y Penumbra Phantasm.",
    "contributors": [{"name": "Toby Fox", "role": "Música"}, {"name": "surreal", "role": "Penumbra Phantasm (versión y portada)"},
                     {"name": "Gooba, The Aftermath, Newt", "role": "Charts originales (Clone Hero)"}, {"name": "RichaadEB", "role": "Megalovania (cover metal)"},
                     {"name": "Elías", "role": "Conversión, escenarios y empaquetado"}, {"name": "Juan", "role": "Dirección"}],
    "api_version": "0.8.4", "mod_version": "1.1.0", "license": "Uso personal"}, indent=1, ensure_ascii=False), encoding="utf-8")
if idle_cab is not None:
    ic = idle_cab.copy(); ic.thumbnail((150, 150)); fondo = Image.new("RGBA", (150, 150), (6, 6, 14, 255)); fondo.alpha_composite(ic, ((150 - ic.width) // 2, 150 - ic.height))
    fondo.save(MOD / "_polymod_icon.png")
# el mod suelto de Penumbra en el juego ya no hace falta (sus canciones están aquí): a la papelera
suelto = JUEGO / "Penumbra Phantasm"
if suelto.exists():
    subprocess.run(["powershell", "-NoProfile", "-Command", f"Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(\"{suelto}\", \"OnlyErrorDialogs\", \"SendToRecycleBin\")"], check=False)
dst = JUEGO / "JestAncients"
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(MOD, dst)
print(f"JestAncients listo con {canciones}; instalado en {dst}")



