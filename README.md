# JestAncients (mod de Friday Night Funkin')

Mod fan-made de FNF (V-Slice / Funkin' 0.8.x) con canciones de Toby Fox y un cover de surreal.

| Canción | Rival | Dificultades |
|---|---|---|
| Black Knife (Toby Fox) | El Caballero | Easy, Normal, Hard + Erect, Nightmare |
| Death by Glamour (Toby Fox) | Mettaton EX | Easy, Normal, Hard + Erect, Nightmare |
| Megalovania (cover de RichaadEB) | Sans | Easy, Normal, Hard + Erect, Nightmare |
| Penumbra Phantasm (versión piano de surreal) | El ángel | Easy, Normal, Hard |
| Penumbra Phantasm (versión original) | El ángel | Easy, Normal, Hard |

- **Erect y Nightmare** están en la variación "Erect" de cada canción. En **Nightmare** no hay turnos: tú tocas toda la parte y el rival la canta contigo a dúo.
- Charts sin jacks rápidos (< 200 ms en el mismo carril) y con los carriles repartidos.

## Instalar

1. Tener Friday Night Funkin' 0.8.x (la versión oficial V-Slice, PC o Android).
2. Copiar la carpeta `JestAncients/` dentro de `mods/` del juego:
   - PC: `<carpeta del juego>/mods/JestAncients`
   - Android: `Android/data/me.funkin.fnf/files/mods/JestAncients`
3. Abrir el juego: aparece la semana **JESTANCIENTS** en Story Mode y las canciones en Freeplay.

## Para un agente (Claude, Codex, etc.)

- Estructura V-Slice estándar: `data/songs/<id>/<id>-chart.json` (Easy/Normal/Hard), `<id>-chart-erect.json` (Erect/Nightmare), `<id>-metadata*.json`, `songs/<id>/Inst.ogg`, `data/characters`, `data/stages`, `images/`.
- Notas: `d` 0-3 = jugador (← ↓ ↑ →), 4-7 = rival; `t` en ms; `l` = largo de nota sostenida.
- `herramientas/construir.py`: el script que genera el mod desde charts de Clone Hero (rutas locales del autor; sirve de referencia: `hacer_jugable`, `equilibrar`, `variar` y las dificultades).
- `herramientas/invertir_lados.py <chart.json> <respaldo.json>`: intercambia jugador y rival en cualquier chart V-Slice (correrlo otra vez lo devuelve).

## Créditos

- Música: Toby Fox (Black Knife, Death by Glamour, Megalovania); surreal (Penumbra Phantasm y portada que inspira el fondo de Black Knife); RichaadEB (cover de Megalovania).
- Charts originales de Clone Hero: Gooba (Black Knife), The Aftermath (Death by Glamour), Newt (Megalovania).
- Conversión, escenarios, sprites y empaquetado: Juan (JestAncients) con ayuda de IA.

Proyecto fan-made sin fines comerciales. Los derechos de la música y los personajes son de sus autores.
