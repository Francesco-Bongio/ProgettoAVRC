#!/usr/bin/env python3
"""
Argentina — Finale Mondiale 2022
Visualizzazione animata con D3.js v7 (general update pattern + transitions).

Uso:   python argentina_vis_d3.py
Output: argentina_finale_2022_d3.html
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import json
import sys
import os

try:
    from statsbombpy import sb
except ImportError:
    print("Errore: pip install statsbombpy")
    sys.exit(1)

MATCH_ID    = 3869685
OUTPUT_FILE = "argentina_finale_2022_d3.html"

SHORT = {
    "Lionel Andrés Messi Cuccittini":      "Messi",
    "Nicolás Hernán Otamendi":              "Otamendi",
    "Enzo Fernandez":                       "E. Fernández",
    "Rodrigo Javier De Paul":              "De Paul",
    "Alexis Mac Allister":                  "Mac Allister",
    "Damián Emiliano Martínez":             "E. Martínez",
    "Lautaro Javier Martínez":             "L. Martínez",
    "Ángel Fabián Di María Hernández":      "Di María",
    "Cristian Gabriel Romero":              "Romero",
    "Nahuel Molina Lucero":                 "Molina",
    "Marcos Javier Acuña":                  "Acuña",
    "Nicolás Alejandro Tagliafico":         "Tagliafico",
    "Leandro Daniel Paredes":               "Paredes",
    "Julián Álvarez":                       "J. Álvarez",
    "Paulo Bruno Exequiel Dybala":          "Dybala",
    "Germán Alejandro Pezzella":            "Pezzella",
    "Gonzalo Ariel Montiel":                "Montiel",
    "Thiago Almada":                        "Almada",
}


def main():
    print("Caricamento dati StatsBomb — Argentina vs Francia, Finale 2022...")
    events = sb.events(match_id=MATCH_ID)

    # ── Passaggi completati ──────────────────────────────────────────────
    mask = (
        (events["team"] == "Argentina") &
        (events["type"] == "Pass") &
        (events["pass_outcome"].isna())
    )
    df = events[mask].copy().sort_values(["minute", "second", "index"])

    df["fx"] = df["location"].apply(lambda l: float(l[0]) if isinstance(l, list) else np.nan)
    df["fy"] = df["location"].apply(lambda l: float(l[1]) if isinstance(l, list) else np.nan)
    df["tx"] = df["pass_end_location"].apply(lambda l: float(l[0]) if isinstance(l, list) else np.nan)
    df["ty"] = df["pass_end_location"].apply(lambda l: float(l[1]) if isinstance(l, list) else np.nan)
    df = df.dropna(subset=["fx", "fy", "tx", "ty"])

    # Posizioni medie (fallback iniziale)
    pos = {}
    for _, r in df.iterrows():
        pos.setdefault(r["player"], {"xs": [], "ys": []})
        pos[r["player"]]["xs"].append(r["fx"])
        pos[r["player"]]["ys"].append(r["fy"])

    players = {
        name: {
            "x": float(np.mean(d["xs"])),
            "y": float(np.mean(d["ys"])),
            "n": len(d["xs"])
        }
        for name, d in pos.items()
    }

    # Sequenza passaggi
    seq = []
    for _, r in df.iterrows():
        rec = r.get("pass_recipient")
        if pd.isna(rec):
            continue
        rec = str(rec)
        if rec not in players:
            players[rec] = {"x": float(r["tx"]), "y": float(r["ty"]), "n": 0}
        seq.append({
            "fr":  r["player"],
            "to":  rec,
            "fx":  float(r["fx"]),
            "fy":  float(r["fy"]),
            "tx":  float(r["tx"]),
            "ty":  float(r["ty"]),
            "min": int(r["minute"]),
            "sec": int(r["second"]),
        })

    # Prima posizione reale di ogni giocatore
    first_pos = {}
    for p in seq:
        if p["fr"] not in first_pos:
            first_pos[p["fr"]] = {"x": p["fx"], "y": p["fy"]}
        if p["to"] not in first_pos:
            first_pos[p["to"]] = {"x": p["tx"], "y": p["ty"]}

    for name in players:
        fp = first_pos.get(name, {"x": players[name]["x"], "y": players[name]["y"]})
        players[name]["ix"] = fp["x"]
        players[name]["iy"] = fp["y"]

    # ── Sostituzioni ─────────────────────────────────────────────────────
    subs_df = events[
        (events["team"] == "Argentina") &
        (events["type"] == "Substitution")
    ].copy().sort_values(["minute", "second"])

    def _first_pass_idx_after(minute, second):
        for i, p in enumerate(seq):
            if p["min"] > minute or (p["min"] == minute and p["sec"] >= second):
                return i
        return len(seq)

    def _get_replacement(row):
        sub = row.get("substitution")
        if isinstance(sub, dict):
            repl = sub.get("replacement", {})
            if isinstance(repl, dict):
                return repl.get("name")
        rep = row.get("substitution_replacement")
        if rep is not None:
            if isinstance(rep, dict):
                return rep.get("name")
            try:
                if not pd.isna(rep):
                    return str(rep)
            except TypeError:
                pass
        return None

    subs = []
    for _, row in subs_df.iterrows():
        m   = int(row["minute"])
        sec = int(row["second"]) if not pd.isna(row.get("second", np.nan)) else 0
        player_off = row.get("player")
        if isinstance(player_off, dict):
            player_off = player_off.get("name", "")
        player_off = str(player_off) if player_off else None
        player_on = _get_replacement(row)
        pi = _first_pass_idx_after(m, sec)
        subs.append({"off": player_off, "on": player_on, "passIdx": pi})
        print(f"  Sub {m}': {player_off} -> {player_on}  (pass idx {pi})")

    print(f"\nPassaggi: {len(seq)} | Giocatori: {len(players)} | Sostituzioni: {len(subs)}")

    short = {n: (SHORT.get(n) or n.strip().split()[-1]) for n in players}

    html = _build_html(players, seq, short, subs)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print("Salvato: " + out)
    print("Apri nel browser per visualizzare l'animazione D3.")


def _build_html(players, passes, shorts, subs):
    html = _TEMPLATE
    html = html.replace("__PLAYERS__", json.dumps(players, ensure_ascii=False))
    html = html.replace("__PASSES__",  json.dumps(passes,  ensure_ascii=False))
    html = html.replace("__SHORTS__",  json.dumps(shorts,  ensure_ascii=False))
    html = html.replace("__SUBS__",    json.dumps(subs,    ensure_ascii=False))
    return html


# ════════════════════════════════════════════════════════════════════════
#  TEMPLATE HTML — visualizzazione con D3.js v7
#  Tecniche D3 usate (dal corso DV09):
#    • d3.scaleLinear()  — mappiamo coordinate StatsBomb (0-120, 0-80) → pixel
#    • data join con .selectAll().data(key).join(enter, update, exit)
#      → enter  : giocatore appare (sostituto o inizio)
#      → update : giocatore si sposta con transition
#      → exit   : giocatore esce (sostituito) — fade out + remove
#    • d3.transition().duration().ease() — animazione spostamenti
#    • d3.timer() — loop di riproduzione automatica
#    • d3.line()  — trail dei passaggi precedenti (percorsi)
# ════════════════════════════════════════════════════════════════════════
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Argentina — Finale Mondiale 2022 | D3.js</title>

<!-- D3.js v7 (richiesto dal corso DV09) -->
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #0d1117;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: 'Segoe UI', Arial, sans-serif;
  color: #e6edf3;
  padding: 14px;
  gap: 10px;
}

header { text-align: center; }
header h1 { font-size: 21px; font-weight: 700; color: #74ACDF; letter-spacing: 0.4px; }
header p  { font-size: 12px; color: #8b949e; margin-top: 3px; }

/* Il campo SVG */
#pitch-container {
  border-radius: 6px;
  box-shadow: 0 4px 28px rgba(0,0,0,0.65);
  overflow: hidden;
}

/* Trail — linee tratteggiate passaggi precedenti */
.trail-line {
  fill: none;
  stroke: rgba(116,172,223,0.35);
  stroke-width: 1.5;
  stroke-dasharray: 4 5;
  pointer-events: none;
}

/* Freccia del passaggio corrente */
.pass-arrow {
  fill: none;
  stroke: rgba(255,255,255,0.15);
  stroke-width: 1.2;
  stroke-dasharray: 3 6;
  pointer-events: none;
}

/* Nodo giocatore */
.player-group circle.player-bg {
  stroke-width: 1;
  stroke: rgba(255,255,255,0.35);
}
.player-group circle.player-fill { }
.player-group rect.label-bg {
  fill: rgba(13,17,23,0.78);
}
.player-group text.label {
  font-size: 10px;
  font-family: 'Segoe UI', Arial, sans-serif;
  fill: rgba(255,255,255,0.88);
  text-anchor: middle;
  dominant-baseline: hanging;
  pointer-events: none;
}

/* Pallone */
#ball { pointer-events: none; }
#ball circle { fill: white; }
#ball circle.shadow { fill: rgba(0,0,0,0.25); }

/* Barra informazioni */
.info-bar {
  display: flex; gap: 18px; flex-wrap: wrap; justify-content: center;
  background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 9px 20px; max-width: 900px; width: 100%;
}
.info-item { display: flex; flex-direction: column; align-items: center; min-width: 80px; }
.lbl { font-size: 10px; color: #6e7681; text-transform: uppercase; letter-spacing: 0.5px; }
.val { font-size: 14px; font-weight: 600; color: #e6edf3; white-space: nowrap; }
.val.p { color: #FFD700; }
.val.r { color: #FF8C00; }

/* Controlli */
.controls {
  display: flex; align-items: center; gap: 9px; flex-wrap: wrap; justify-content: center;
  background: #161b22; border: 1px solid #30363d; border-radius: 8px;
  padding: 9px 14px; max-width: 900px; width: 100%;
}
button {
  background: #21262d; color: #e6edf3; border: 1px solid #30363d;
  padding: 6px 13px; border-radius: 6px; cursor: pointer; font-size: 13px;
  transition: background 0.12s; font-family: inherit;
}
button:hover { background: #30363d; }
#btnPlay { background: #238636; border-color: #2ea043; font-weight: 600; }
#btnPlay:hover { background: #2ea043; }
#btnPlay.paused { background: #b94040; border-color: #d05050; }
label { font-size: 12px; color: #8b949e; display: flex; align-items: center; gap: 5px; }
input[type=range] { accent-color: #74ACDF; cursor: pointer; }
input[type=checkbox] { accent-color: #238636; cursor: pointer; }
#spV { color: #e6edf3; font-weight: 600; min-width: 30px; }
.sep { color: #30363d; font-size: 16px; user-select: none; }
</style>
</head>
<body>

<header>
  <h1>&#127462;&#127479; Argentina — Finale Mondiale 2022 &#127942;</h1>
  <p>Argentina vs Francia &nbsp;·&nbsp; 18 Dicembre 2022 &nbsp;·&nbsp; Lusail Iconic Stadium
     &nbsp;·&nbsp; <em>visualizzazione D3.js v7</em></p>
</header>

<div id="pitch-container">
  <svg id="pitch"></svg>
</div>

<div class="info-bar">
  <div class="info-item"><span class="lbl">Passante</span><span class="val p" id="iPasser">—</span></div>
  <div class="info-item"><span class="lbl">Ricevente</span><span class="val r" id="iRecip">—</span></div>
  <div class="info-item"><span class="lbl">Minuto</span><span class="val" id="iTime">—</span></div>
  <div class="info-item"><span class="lbl">Passaggio</span><span class="val" id="iIdx">—</span></div>
</div>

<div class="controls">
  <button id="btnPlay" onclick="togglePlay()">&#9654; Play</button>
  <button onclick="doReset()">&#8635; Reset</button>
  <button onclick="stepPass(-1)">&#9664;</button>
  <button onclick="stepPass(1)">&#9654;</button>
  <span class="sep">|</span>
  <label>Velocità:
    <input type="range" id="spR" min="200" max="2000" step="50" value="700"
           oninput="stepDuration = +this.value; document.getElementById('spV').textContent = (+this.value < 500 ? 'Veloce' : +this.value > 1400 ? 'Lenta' : 'Media')">
    <span id="spV">Media</span>
  </label>
  <label>Timeline:
    <input type="range" id="tl" min="0" max="1000" value="0" oninput="seekTo(+this.value)">
  </label>
  <label><input type="checkbox" id="chkTrail" checked> Percorsi</label>
</div>

<script>
// ═══════════════════════════════════════════════════════════════════════
//  DATI iniettati da Python
// ═══════════════════════════════════════════════════════════════════════
const PLAYERS = __PLAYERS__;
const PASSES  = __PASSES__;
const SHORTS  = __SHORTS__;
const SUBS    = __SUBS__;

// ═══════════════════════════════════════════════════════════════════════
//  DIMENSIONI SVG e SCALE D3  (DV09 — d3.scaleLinear)
//
//  StatsBomb usa coordinate (x: 0-120, y: 0-80) con origine in basso-sx
//  Il campo SVG ha origine in alto-sx → invertiamo l'asse y con il range
// ═══════════════════════════════════════════════════════════════════════
const W = 900, H = 616;
const MARGIN = { left: 32, right: 32, top: 28, bottom: 28 };

// Scale che mappano il sistema StatsBomb → pixel SVG
const scX = d3.scaleLinear()
  .domain([0, 120])
  .range([MARGIN.left, W - MARGIN.right]);

const scY = d3.scaleLinear()
  .domain([0, 80])
  .range([H - MARGIN.bottom, MARGIN.top]);   // range invertito: y=0 → fondo campo

// ═══════════════════════════════════════════════════════════════════════
//  SETUP SVG
// ═══════════════════════════════════════════════════════════════════════
const svg = d3.select("#pitch")
  .attr("width", W)
  .attr("height", H);

// ── Gradiente campo ──────────────────────────────────────────────────
const defs = svg.append("defs");
const grad = defs.append("linearGradient")
  .attr("id", "fieldGrad").attr("x1","0%").attr("y1","0%").attr("x2","0%").attr("y2","100%");
grad.append("stop").attr("offset","0%").attr("stop-color","#2e6b27");
grad.append("stop").attr("offset","50%").attr("stop-color","#31702a");
grad.append("stop").attr("offset","100%").attr("stop-color","#2e6b27");

// Arrowhead marker per la freccia del passaggio corrente
defs.append("marker")
  .attr("id","arrowhead")
  .attr("markerWidth",7).attr("markerHeight",6)
  .attr("refX",7).attr("refY",3)
  .attr("orient","auto")
  .append("polygon")
  .attr("points","0 0, 7 3, 0 6")
  .attr("fill","rgba(255,255,255,0.5)");

// ── Layer ordinati ───────────────────────────────────────────────────
const layerField   = svg.append("g").attr("id","layer-field");
const layerStripes = svg.append("g").attr("id","layer-stripes");
const layerTrail   = svg.append("g").attr("id","layer-trail");
const layerArrow   = svg.append("g").attr("id","layer-arrow");
const layerPlayers = svg.append("g").attr("id","layer-players");
const layerBall    = svg.append("g").attr("id","ball");

// ═══════════════════════════════════════════════════════════════════════
//  DISEGNO CAMPO (linee SVG — nessun Canvas)
//  Ogni elemento è un <rect> o <line> o <circle> SVG nativo
// ═══════════════════════════════════════════════════════════════════════
function drawPitch() {
  // Fondo verde
  layerField.append("rect")
    .attr("x", MARGIN.left).attr("y", MARGIN.top)
    .attr("width", W - MARGIN.left - MARGIN.right)
    .attr("height", H - MARGIN.top - MARGIN.bottom)
    .attr("fill","url(#fieldGrad)");

  // Strisce alternate
  const sw = (W - MARGIN.left - MARGIN.right) / 8;
  for (let i = 0; i < 8; i += 2) {
    layerStripes.append("rect")
      .attr("x", MARGIN.left + i * sw).attr("y", MARGIN.top)
      .attr("width", sw).attr("height", H - MARGIN.top - MARGIN.bottom)
      .attr("fill","rgba(25,61,18,0.07)");
  }

  const L = layerField;
  const lw = { "stroke-width": 1.5, "stroke": "rgba(255,255,255,0.82)", "fill": "none" };
  const lw2 = { ...lw, "stroke-width": 2 };

  function rect(x1, y1, x2, y2) {
    L.append("rect")
      .attr("x", scX(x1)).attr("y", scY(y2))
      .attr("width", scX(x2) - scX(x1)).attr("height", scY(y1) - scY(y2))
      .attr("fill","none").attr("stroke","rgba(255,255,255,0.82)").attr("stroke-width",1.5);
  }
  function circle(cx, cy, r) {
    L.append("circle")
      .attr("cx", scX(cx)).attr("cy", scY(cy))
      .attr("r", (r / 120) * (W - MARGIN.left - MARGIN.right))
      .attr("fill","none").attr("stroke","rgba(255,255,255,0.82)").attr("stroke-width",1.5);
  }
  function dot(cx, cy) {
    L.append("circle")
      .attr("cx", scX(cx)).attr("cy", scY(cy))
      .attr("r", 3).attr("fill","rgba(255,255,255,0.85)");
  }

  // Bordo campo
  rect(0, 0, 120, 80);
  // Linea mediana
  L.append("line")
    .attr("x1", scX(60)).attr("y1", scY(0))
    .attr("x2", scX(60)).attr("y2", scY(80))
    .attr("stroke","rgba(255,255,255,0.82)").attr("stroke-width",1.5);
  // Cerchio centrale
  circle(60, 40, 9.15);
  dot(60, 40);

  // Area grande sx
  rect(0, 18, 18, 62);
  // Area piccola sx
  rect(0, 30, 6, 50);
  // Punto rigore sx
  dot(12, 40);
  // Arco area sx
  L.append("path")
    .attr("d", d3.arc()({
      innerRadius: (9.15/120)*(W - MARGIN.left - MARGIN.right),
      outerRadius: (9.15/120)*(W - MARGIN.left - MARGIN.right) + 1.5,
      startAngle: -0.93, endAngle: 0.93
    }))
    .attr("transform", `translate(${scX(12)},${scY(40)})`)
    .attr("fill","rgba(255,255,255,0.82)");

  // Area grande dx
  rect(102, 18, 120, 62);
  // Area piccola dx
  rect(114, 30, 120, 50);
  // Punto rigore dx
  dot(108, 40);
  // Arco area dx
  L.append("path")
    .attr("d", d3.arc()({
      innerRadius: (9.15/120)*(W - MARGIN.left - MARGIN.right),
      outerRadius: (9.15/120)*(W - MARGIN.left - MARGIN.right) + 1.5,
      startAngle: Math.PI - 0.93, endAngle: Math.PI + 0.93
    }))
    .attr("transform", `translate(${scX(108)},${scY(40)})`)
    .attr("fill","rgba(255,255,255,0.82)");

  // Porte
  L.append("rect")
    .attr("x", scX(-2.4)).attr("y", scY(44))
    .attr("width", scX(0) - scX(-2.4)).attr("height", scY(36) - scY(44))
    .attr("fill","none").attr("stroke","rgba(255,255,255,0.92)").attr("stroke-width",2);
  L.append("rect")
    .attr("x", scX(120)).attr("y", scY(44))
    .attr("width", scX(122.4) - scX(120)).attr("height", scY(36) - scY(44))
    .attr("fill","none").attr("stroke","rgba(255,255,255,0.92)").attr("stroke-width",2);

  // Angoli (archi)
  const crPx = (1/120) * (W - MARGIN.left - MARGIN.right) * 3;
  [[0,0,0,Math.PI/2],[0,80,-Math.PI/2,0],[120,0,Math.PI/2,Math.PI],[120,80,Math.PI,3*Math.PI/2]]
    .forEach(([x,y,a,b]) => {
      L.append("path")
        .attr("d", d3.arc()({ innerRadius: crPx-1, outerRadius: crPx, startAngle: a, endAngle: b }))
        .attr("transform", `translate(${scX(x)},${scY(y)})`)
        .attr("fill","rgba(255,255,255,0.7)");
    });
}

drawPitch();

// ═══════════════════════════════════════════════════════════════════════
//  VISIBILITÀ GIOCATORI
//  Stessa logica di prima, ma usata poi nel data join D3
// ═══════════════════════════════════════════════════════════════════════
const visFrom  = {};
const visUntil = {};
const subOns = new Set();
SUBS.forEach(s => {
  if (s.on)  subOns.add(s.on);
  if (s.off) visUntil[s.off] = s.passIdx;
});
for (let i = 0; i < PASSES.length; i++) {
  const p = PASSES[i];
  if (subOns.has(p.fr) && visFrom[p.fr] === undefined) visFrom[p.fr] = i;
  if (subOns.has(p.to) && visFrom[p.to] === undefined) visFrom[p.to] = i;
}

function isVisible(name, idx) {
  const from  = visFrom[name]  ?? 0;
  const until = visUntil[name] ?? null;
  return idx >= from && (until === null || idx < until);
}

// ═══════════════════════════════════════════════════════════════════════
//  STATO POSIZIONI (precomputato)
// ═══════════════════════════════════════════════════════════════════════
const playerStates = [];
(function buildStates() {
  const pos = {};
  for (const [name, d] of Object.entries(PLAYERS)) pos[name] = { x: d.ix, y: d.iy };
  for (let i = 0; i <= PASSES.length; i++) {
    const snap = {};
    for (const [n, p] of Object.entries(pos)) snap[n] = { x: p.x, y: p.y };
    playerStates.push(snap);
    if (i < PASSES.length) {
      const p = PASSES[i];
      pos[p.fr] = { x: p.fx, y: p.fy };
      pos[p.to] = { x: p.tx, y: p.ty };
    }
  }
})();

// ═══════════════════════════════════════════════════════════════════════
//  STATO ANIMAZIONE
// ═══════════════════════════════════════════════════════════════════════
const N = PASSES.length;
const TRAIL_LEN = 10;

let idx = 0;
let playing = false;
let stepDuration = 700;   // ms per passaggio (controllato dallo slider)
let timer = null;
let trail = [];

// ═══════════════════════════════════════════════════════════════════════
//  RENDER PRINCIPALE — aggiorna SVG al passaggio `idx`
//
//  Cuore D3: usa il GENERAL UPDATE PATTERN (DV09 slide 31-34):
//    .selectAll().data(key).join(enter, update, exit)
//
//  • enter  → nuovi giocatori (sostituti) appaiono con fade-in
//  • update → i giocatori già presenti si spostano con transition
//  • exit   → giocatori sostituiti spariscono con fade-out + remove
// ═══════════════════════════════════════════════════════════════════════
function render(animated) {
  const dur = animated ? Math.max(100, stepDuration - 100) : 0;
  const cur = idx < N ? PASSES[idx] : null;
  const state = playerStates[Math.min(idx, playerStates.length - 1)];

  // Lista giocatori visibili in questo passaggio
  const activePlayers = Object.keys(PLAYERS)
    .filter(name => isVisible(name, idx))
    .map(name => {
      const s = state[name] || { x: PLAYERS[name].x, y: PLAYERS[name].y };
      const isPasser   = cur && name === cur.fr;
      const isRecipient = cur && name === cur.to;
      return {
        name,
        x: isPasser ? cur.fx : s.x,
        y: isPasser ? cur.fy : s.y,
        isPasser,
        isRecipient,
        label: SHORTS[name] || name.split(" ").pop(),
      };
    });

  // ── DATA JOIN — general update pattern D3 v7 ─────────────────────
  //
  //  .join(enter, update, exit) forma esplicita (DV09 slide 31-34):
  //    enter  → sostituto / primo passaggio: struttura SVG + fade-in
  //    update → giocatore già presente: aggiorniamo solo stile/posizione
  //    exit   → giocatore sostituito: fade-out + remove dal DOM
  //
  //  La key function (d => d.name) è fondamentale: senza di essa D3
  //  userebbe l'indice e non distinguerebbe correttamente enter/exit.
  //
  layerPlayers
    .selectAll("g.player-group")
    .data(activePlayers, d => d.name)
    .join(
      // ── ENTER ──────────────────────────────────────────────────────
      enter => {
        const g = enter.append("g")
          .attr("class", "player-group")
          .attr("transform", d => `translate(${scX(d.x)},${scY(d.y)})`)
          .style("opacity", 0);
        g.append("circle").attr("class","player-bg");
        g.append("circle").attr("class","player-fill");
        g.append("rect").attr("class","label-bg").attr("y",14).attr("height",14).attr("rx",2);
        g.append("text").attr("class","label").attr("y",15);
        // Fade-in — DV09: animated transitions su enter
        g.transition().duration(300).style("opacity", 1);
        return g;
      },
      // ── UPDATE ─────────────────────────────────────────────────────
      update => update,
      // ── EXIT ───────────────────────────────────────────────────────
      exit => exit.transition().duration(400).style("opacity", 0).remove()
    )
    // Applica stile e posizione su tutti (enter+update merged da .join)
    .call(all => {
      // Transizione posizione — cuore animazione D3
      all.transition().duration(dur).ease(d3.easeCubicOut)
        .attr("transform", d => `translate(${scX(d.x)},${scY(d.y)})`);

      // ── ILLUMINAZIONE passante (giallo) e ricevente (arancio) ──────
      //  Aggiornati immediatamente (senza transition) così il colore
      //  è visibile per tutta la durata del passaggio corrente.
      all.select("circle.player-bg")
        .attr("r",      d => (d.isPasser || d.isRecipient) ? 15 : 12)
        .attr("stroke", d => d.isPasser ? "#FFD700" : d.isRecipient ? "#FF8C00" : "rgba(255,255,255,0.35)")
        .attr("stroke-width", d => (d.isPasser || d.isRecipient) ? 3 : 1)
        .attr("filter", d => d.isPasser
          ? "drop-shadow(0 0 8px #FFD700)"
          : d.isRecipient
          ? "drop-shadow(0 0 8px #FF8C00)"
          : "none");

      all.select("circle.player-fill")
        .attr("r",    d => (d.isPasser || d.isRecipient) ? 12 : 10)
        .attr("fill", d => d.isPasser ? "#FFD700" : d.isRecipient ? "#FF8C00" : "#74ACDF");

      all.select("text.label")
        .text(d => d.label)
        .attr("fill",        d => d.isPasser ? "#FFD700" : d.isRecipient ? "#FF8C00" : "rgba(255,255,255,0.88)")
        .attr("font-weight", d => (d.isPasser || d.isRecipient) ? "bold" : "normal")
        .attr("font-size",   d => (d.isPasser || d.isRecipient) ? "11px" : "10px");

      // Sfondo etichetta (larghezza dinamica sul testo)
      all.each(function(d) {
        const txt = d3.select(this).select("text.label").node();
        if (!txt) return;
        const tw = txt.getComputedTextLength() + 8;
        d3.select(this).select("rect.label-bg").attr("x", -tw/2).attr("width", tw);
      });
    });

  // ── TRAIL (ultimi TRAIL_LEN passaggi) ─────────────────────────────
  const showTrail = document.getElementById("chkTrail").checked;
  const trailData = showTrail ? trail : [];

  layerTrail.selectAll("line.trail-line")
    .data(trailData)
    .join("line")                          // join compatto (DV09 slide 33)
    .attr("class","trail-line")
    .attr("x1", d => scX(PASSES[d].fx)).attr("y1", d => scY(PASSES[d].fy))
    .attr("x2", d => scX(PASSES[d].tx)).attr("y2", d => scY(PASSES[d].ty))
    .style("opacity", (_, i) => (i + 1) / trailData.length * 0.7);

  // ── FRECCIA passaggio corrente ─────────────────────────────────────
  if (cur) {
    layerArrow.selectAll("line.pass-arrow")
      .data([cur])
      .join("line")
      .attr("class","pass-arrow")
      .attr("x1", d => scX(d.fx)).attr("y1", d => scY(d.fy))
      .attr("x2", d => scX(d.tx)).attr("y2", d => scY(d.ty))
      .attr("marker-end","url(#arrowhead)");
  } else {
    layerArrow.selectAll("line.pass-arrow").remove();
  }

  // ── PALLONE — posizionato da animateBall(), qui solo visibilità ──────
  if (!cur) layerBall.selectAll("circle").remove();

  // ── INFO BAR ──────────────────────────────────────────────────────
  if (cur) {
    document.getElementById("iPasser").textContent = SHORTS[cur.fr] || cur.fr;
    document.getElementById("iRecip").textContent  = SHORTS[cur.to] || cur.to;
    document.getElementById("iTime").textContent   = cur.min + "'" + (cur.sec ? ' ' + cur.sec + '"' : '');
    document.getElementById("iIdx").textContent    = (idx + 1) + ' / ' + N;
  } else {
    document.getElementById("iPasser").textContent = "—";
    document.getElementById("iRecip").textContent  = "—";
    document.getElementById("iTime").textContent   = "Fine";
    document.getElementById("iIdx").textContent    = N + " / " + N;
  }

  // Sincronizza timeline slider
  document.getElementById("tl").value = Math.round((idx / (N - 1)) * 1000);
}

// ═══════════════════════════════════════════════════════════════════════
//  PALLA — animazione indipendente con d3.timer
//
//  Quando si avanza di un passaggio, animateBall() lancia un d3.timer
//  che ogni frame calcola t = elapsed/stepDuration (0→1) e sposta la
//  palla da (fx,fy) a (tx,ty) con interpolazione lineare.
//  Quando t>=1 la palla rimane su (tx,ty) e il timer si ferma.
//  Questo è completamente separato da render() che aggiorna i giocatori.
// ═══════════════════════════════════════════════════════════════════════
let ballTimer = null;

// Crea i due cerchi del pallone se non esistono ancora
function ensureBall() {
  if (layerBall.select("circle.shadow").empty()) {
    layerBall.append("circle").attr("class","shadow")
      .attr("fill","rgba(0,0,0,0.22)").attr("r",4);
  }
  if (layerBall.select("circle.ball-main").empty()) {
    layerBall.append("circle").attr("class","ball-main")
      .attr("fill","white").attr("r",6.5);
  }
}

function placeBall(x, y) {
  // Posiziona istantaneamente (nessuna animazione)
  layerBall.select("circle.shadow").attr("cx", x).attr("cy", y + 5);
  layerBall.select("circle.ball-main").attr("cx", x).attr("cy", y);
}

function animateBall(pass) {
  // Ferma eventuale animazione precedente
  if (ballTimer) { ballTimer.stop(); ballTimer = null; }
  ensureBall();

  const x0 = scX(pass.fx), y0 = scY(pass.fy);
  // La palla si ferma al punto medio del link, non sul giocatore ricevente
  const x1 = (scX(pass.fx) + scX(pass.tx)) / 2;
  const y1 = (scY(pass.fy) + scY(pass.ty)) / 2;
  const dur = stepDuration;
  const t0 = performance.now();

  // d3.timer chiama la callback ogni frame finché non restituisce true
  ballTimer = d3.timer(() => {
    const t = Math.min(1, (performance.now() - t0) / dur);
    const bx = x0 + (x1 - x0) * t;
    const by = y0 + (y1 - y0) * t;
    placeBall(bx, by);
    if (t >= 1) { ballTimer.stop(); ballTimer = null; return true; }
  });
}

// ═══════════════════════════════════════════════════════════════════════
//  CONTROLLI
// ═══════════════════════════════════════════════════════════════════════
function advanceOne() {
  if (idx >= N - 1) {
    playing = false;
    if (timer) { timer.stop(); timer = null; }
    document.getElementById("btnPlay").innerHTML = "&#9654; Play";
    document.getElementById("btnPlay").classList.remove("paused");
    render(false);
    return false;
  }
  trail.push(idx);
  if (trail.length > TRAIL_LEN) trail.shift();
  idx++;
  render(true);
  // Lancia animazione palla per il passaggio appena diventato corrente
  if (idx < N) animateBall(PASSES[idx]);
  return true;
}

function togglePlay() {
  if (playing) {
    playing = false;
    if (timer) { timer.stop(); timer = null; }
    document.getElementById("btnPlay").innerHTML = "&#9654; Play";
    document.getElementById("btnPlay").classList.remove("paused");
  } else {
    if (idx >= N - 1) { idx = 0; trail = []; }
    playing = true;
    document.getElementById("btnPlay").innerHTML = "&#9646;&#9646; Pausa";
    document.getElementById("btnPlay").classList.add("paused");

    // d3.timer: avanza un passaggio ogni stepDuration ms
    let last = null;
    timer = d3.timer(elapsed => {
      if (!playing) { timer.stop(); timer = null; return; }
      if (last === null) { last = elapsed; return; }
      if (elapsed - last >= stepDuration) {
        last = elapsed;
        if (!advanceOne()) { timer.stop(); timer = null; }
      }
    });
  }
}

function doReset() {
  playing = false;
  if (timer) { timer.stop(); timer = null; }
  if (ballTimer) { ballTimer.stop(); ballTimer = null; }
  idx = 0; trail = [];
  document.getElementById("btnPlay").innerHTML = "&#9654; Play";
  document.getElementById("btnPlay").classList.remove("paused");
  document.getElementById("tl").value = 0;
  render(false);
  if (idx < N) { ensureBall(); placeBall(scX(PASSES[0].fx), scY(PASSES[0].fy)); }
}

function stepPass(dir) {
  if (playing) togglePlay();
  if (dir > 0 && idx < N - 1) {
    trail.push(idx);
    if (trail.length > TRAIL_LEN) trail.shift();
    idx++;
    render(true);
    if (idx < N) animateBall(PASSES[idx]);
  } else if (dir < 0 && idx > 0) {
    trail.pop();
    idx--;
    render(false);
    if (idx < N) { ensureBall(); placeBall(scX(PASSES[idx].fx), scY(PASSES[idx].fy)); }
  }
}

function seekTo(v) {
  if (playing) togglePlay();
  if (ballTimer) { ballTimer.stop(); ballTimer = null; }
  idx = Math.round((v / 1000) * (N - 1));
  trail = [];
  const s = Math.max(0, idx - TRAIL_LEN);
  for (let i = s; i < idx; i++) trail.push(i);
  render(false);
  if (idx < N) { ensureBall(); placeBall(scX(PASSES[idx].fx), scY(PASSES[idx].fy)); }
}

// ── Primo render ──────────────────────────────────────────────────────
render(false);
if (PASSES.length > 0) { ensureBall(); placeBall(scX(PASSES[0].fx), scY(PASSES[0].fy)); }
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()