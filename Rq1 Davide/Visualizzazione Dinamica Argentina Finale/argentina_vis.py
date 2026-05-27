#!/usr/bin/env python3
"""
Argentina — Finale Mondiale 2022
Visualizzazione animata: giocatori appaiono/scompaiono con le sostituzioni.

Uso:   python argentina_vis.py
Output: argentina_finale_2022.html
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
OUTPUT_FILE = "argentina_finale_2022.html"

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

    # ── Passaggi completati ────────────────────────────────────────────────
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

    # Posizioni medie (usate come fallback iniziale)
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

    # ── Prima posizione reale di ogni giocatore ────────────────────────────
    # Usata in buildPlayerStates JS per evitare lo snap da posizione media
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

    # ── Sostituzioni ───────────────────────────────────────────────────────
    subs_df = events[
        (events["team"] == "Argentina") &
        (events["type"] == "Substitution")
    ].copy().sort_values(["minute", "second"])

    def _first_pass_idx_after(minute, second):
        """Indice del primo passaggio >= minute:second."""
        for i, p in enumerate(seq):
            if p["min"] > minute or (p["min"] == minute and p["sec"] >= second):
                return i
        return len(seq)

    def _get_replacement(row):
        """Estrai il nome del giocatore che entra, gestendo vari formati."""
        # Formato 1: colonna 'substitution' come dict
        sub = row.get("substitution")
        if isinstance(sub, dict):
            repl = sub.get("replacement", {})
            if isinstance(repl, dict):
                return repl.get("name")
        # Formato 2: colonna piatta 'substitution_replacement'
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

    subs = []   # [{off, on, passIdx}]  — passIdx = primo pass dopo la sostituzione
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
    print("Apri nel browser per visualizzare l'animazione.")


def _build_html(players, passes, shorts, subs):
    html = _TEMPLATE
    html = html.replace("__PLAYERS__", json.dumps(players, ensure_ascii=False))
    html = html.replace("__PASSES__",  json.dumps(passes,  ensure_ascii=False))
    html = html.replace("__SHORTS__",  json.dumps(shorts,  ensure_ascii=False))
    html = html.replace("__SUBS__",    json.dumps(subs,    ensure_ascii=False))
    return html


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Argentina — Finale Mondiale 2022 | Rete Passaggi</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0d1117; min-height: 100vh;
  display: flex; flex-direction: column; align-items: center;
  font-family: 'Segoe UI', Arial, sans-serif; color: #e6edf3;
  padding: 14px; gap: 10px;
}
header { text-align: center; }
header h1 { font-size: 21px; font-weight: 700; color: #74ACDF; letter-spacing: 0.4px; }
header p  { font-size: 12px; color: #8b949e; margin-top: 3px; }
canvas { border-radius: 6px; box-shadow: 0 4px 28px rgba(0,0,0,0.65); display: block; }

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
  <p>Argentina vs Francia &nbsp;·&nbsp; 18 Dicembre 2022 &nbsp;·&nbsp; Lusail Iconic Stadium</p>
</header>

<canvas id="c" width="900" height="616"></canvas>

<div class="info-bar">
  <div class="info-item"><span class="lbl">Passante</span><span class="val p" id="iPasser">—</span></div>
  <div class="info-item"><span class="lbl">Ricevente</span><span class="val r" id="iRecip">—</span></div>
  <div class="info-item"><span class="lbl">Minuto</span><span class="val" id="iTime">—</span></div>
  <div class="info-item"><span class="lbl">Passaggio</span><span class="val" id="iIdx">—</span></div>
</div>

<div class="controls">
  <button id="btnPlay" onclick="togglePlay()">&#9654; Play</button>
  <button onclick="doReset()">&#8635; Reset</button>
  <button onclick="step(-1)">&#9664;</button>
  <button onclick="step(1)">&#9654;</button>
  <span class="sep">|</span>
  <label>Velocita':
    <input type="range" id="spR" min="0.3" max="6" step="0.1" value="1.5"
           oninput="speed=+this.value; document.getElementById('spV').textContent=speed.toFixed(1)+'x'">
    <span id="spV">1.5x</span>
  </label>
  <label>Timeline:
    <input type="range" id="tl" min="0" max="1000" value="0" oninput="seek(+this.value)">
  </label>
  <label><input type="checkbox" id="chkTrail" checked> Percorsi</label>
</div>

<script>
const PLAYERS = __PLAYERS__;
const PASSES  = __PASSES__;
const SHORTS  = __SHORTS__;
const SUBS    = __SUBS__;    // [{off, on, passIdx}]

const cv = document.getElementById('c');
const cx = cv.getContext('2d');
const CW = cv.width, CH = cv.height;
const PX = 32, PY = 28, PW = CW-2*PX, PH = CH-2*PY;

function px(x) { return PX + (x/120)*PW; }
function py(y) { return PY + ((80-y)/80)*PH; }

// ── Visibilità giocatori ───────────────────────────────────────────────────
//
// Un giocatore è VISIBILE nell'intervallo [visFrom, visUntil).
//   visFrom  = 0 per titolari | = primo passaggio come passante/ricevente per subentrati
//   visUntil = indice passaggio dopo la sua uscita | null = rimane fino alla fine
//
const visFrom  = {};   // player -> pass idx da cui è visibile
const visUntil = {};   // player -> pass idx da cui scompare (null = mai)

// Identifica chi è entrato come sostituto
const subOns = new Set();
SUBS.forEach(s => {
  if (s.on)  subOns.add(s.on);
  if (s.off) visUntil[s.off] = s.passIdx;  // il titolare/precedente esce
});

// Per i sostituti: il primo passaggio in cui compaiono (come passante o ricevente)
for (let i = 0; i < PASSES.length; i++) {
  const p = PASSES[i];
  if (subOns.has(p.fr) && visFrom[p.fr] === undefined) visFrom[p.fr] = i;
  if (subOns.has(p.to) && visFrom[p.to] === undefined) visFrom[p.to] = i;
}
// I titolari che non sono in subOns hanno visFrom = 0 (default)

function isVisible(name, idx) {
  const from  = visFrom[name]  ?? 0;
  const until = visUntil[name] ?? null;
  return idx >= from && (until === null || idx < until);
}

// ── Precomputa posizioni reali ad ogni passaggio ───────────────────────────
//
// playerStates[i] = {nome: {x,y}} = posizioni all'INIZIO del passaggio i.
// Inizializzazione con prima posizione reale (ix,iy), non la media.
//
const playerStates = [];
(function buildStates() {
  const pos = {};
  for (const [name, d] of Object.entries(PLAYERS)) {
    pos[name] = {x: d.ix, y: d.iy};
  }
  for (let i = 0; i <= PASSES.length; i++) {
    const snap = {};
    for (const [n, p] of Object.entries(pos)) snap[n] = {x: p.x, y: p.y};
    playerStates.push(snap);
    if (i < PASSES.length) {
      const p = PASSES[i];
      pos[p.fr] = {x: p.fx, y: p.fy};
      pos[p.to] = {x: p.tx, y: p.ty};
    }
  }
})();

// ── Stato animazione ───────────────────────────────────────────────────────
let idx = 0, t = 0, playing = false, raf = null, speed = 1.5;
const FPP = 50, TRAIL_LEN = 10;
let trail = [];
const N = PASSES.length;

function togglePlay() {
  playing = !playing;
  const b = document.getElementById('btnPlay');
  b.innerHTML = playing ? '&#9646;&#9646; Pausa' : '&#9654; Play';
  b.classList.toggle('paused', !playing);
  if (playing) raf = requestAnimationFrame(tick);
  else cancelAnimationFrame(raf);
}

function doReset() {
  playing = false; cancelAnimationFrame(raf);
  idx = 0; t = 0; trail = [];
  document.getElementById('btnPlay').innerHTML = '&#9654; Play';
  document.getElementById('btnPlay').classList.remove('paused');
  document.getElementById('tl').value = 0;
  draw(); updateInfo();
}

function step(dir) {
  if (dir > 0 && idx < N-1) {
    trail.push(idx); if (trail.length > TRAIL_LEN) trail.shift(); idx++;
  } else if (dir < 0 && idx > 0) {
    trail.pop(); idx--;
  }
  t = 0; syncTL(); draw(); updateInfo();
}

function seek(v) {
  idx = Math.round((v/1000)*(N-1)); t = 0; trail = [];
  const s = Math.max(0, idx - TRAIL_LEN);
  for (let i = s; i < idx; i++) trail.push(i);
  draw(); updateInfo();
}

function syncTL() {
  document.getElementById('tl').value = Math.round((idx/(N-1))*1000);
}

function updateInfo() {
  if (idx >= N) {
    ['iPasser','iRecip','iTime'].forEach(id => document.getElementById(id).textContent = '—');
    document.getElementById('iIdx').textContent = 'Fine';
    return;
  }
  const p = PASSES[idx];
  document.getElementById('iPasser').textContent = SHORTS[p.fr] || p.fr;
  document.getElementById('iRecip').textContent  = SHORTS[p.to] || p.to;
  document.getElementById('iTime').textContent   = p.min + "'" + (p.sec ? ' '+p.sec+'"' : '');
  document.getElementById('iIdx').textContent    = (idx+1) + ' / ' + N;
}

function tick() {
  if (!playing) return;
  t += speed / FPP;
  if (t >= 1) {
    t = 0;
    trail.push(idx); if (trail.length > TRAIL_LEN) trail.shift();
    idx++;
    if (idx >= N) {
      idx = N; playing = false;
      document.getElementById('btnPlay').innerHTML = '&#9654; Play';
      document.getElementById('btnPlay').classList.remove('paused');
      draw(); updateInfo(); return;
    }
    syncTL(); updateInfo();
  }
  draw(); raf = requestAnimationFrame(tick);
}

// ── Disegno campo ──────────────────────────────────────────────────────────
function drawPitch() {
  const g = cx.createLinearGradient(PX, PY, PX, PY+PH);
  g.addColorStop(0, '#2e6b27'); g.addColorStop(0.5, '#31702a'); g.addColorStop(1, '#2e6b27');
  cx.fillStyle = g; cx.fillRect(PX, PY, PW, PH);

  cx.globalAlpha = 0.07; cx.fillStyle = '#193d12';
  const sw = PW/8;
  for (let i = 0; i < 8; i += 2) cx.fillRect(PX+i*sw, PY, sw, PH);
  cx.globalAlpha = 1;

  cx.strokeStyle = 'rgba(255,255,255,0.82)'; cx.lineWidth = 1.5;
  cx.strokeRect(PX, PY, PW, PH);
  cx.beginPath(); cx.moveTo(px(60), PY); cx.lineTo(px(60), PY+PH); cx.stroke();

  const rc = (9.15/120)*PW;
  cx.beginPath(); cx.arc(px(60), py(40), rc, 0, Math.PI*2); cx.stroke();
  cx.fillStyle = 'rgba(255,255,255,0.85)';
  cx.beginPath(); cx.arc(px(60), py(40), 3, 0, Math.PI*2); cx.fill();

  cx.strokeRect(PX, py(62), px(18)-PX, py(18)-py(62));
  cx.strokeRect(PX, py(50), px(6)-PX,  py(30)-py(50));
  cx.fillStyle = 'rgba(255,255,255,0.85)';
  cx.beginPath(); cx.arc(px(12), py(40), 3, 0, Math.PI*2); cx.fill();
  cx.beginPath(); cx.arc(px(12), py(40), rc, -Math.PI*0.82, -Math.PI*0.18); cx.stroke();

  cx.strokeRect(px(102), py(62), px(120)-px(102), py(18)-py(62));
  cx.strokeRect(px(114), py(50), px(120)-px(114), py(30)-py(50));
  cx.fillStyle = 'rgba(255,255,255,0.85)';
  cx.beginPath(); cx.arc(px(108), py(40), 3, 0, Math.PI*2); cx.fill();
  cx.beginPath(); cx.arc(px(108), py(40), rc, Math.PI*0.18, Math.PI*0.82); cx.stroke();

  cx.strokeStyle = 'rgba(255,255,255,0.92)'; cx.lineWidth = 2;
  cx.strokeRect(px(-2.4), py(44), px(0)-px(-2.4),   py(36)-py(44));
  cx.strokeRect(px(120),  py(44), px(122.4)-px(120), py(36)-py(44));

  cx.lineWidth = 1.5; cx.strokeStyle = 'rgba(255,255,255,0.7)';
  const cr = (1/120)*PW*3;
  [[0,0,0,Math.PI/2],[0,80,-Math.PI/2,0],[120,0,Math.PI/2,Math.PI],[120,80,Math.PI,3*Math.PI/2]]
    .forEach(([x,y,a,b]) => { cx.beginPath(); cx.arc(px(x),py(y),cr,a,b); cx.stroke(); });
}

// ── Disegno trail ──────────────────────────────────────────────────────────
function drawTrail() {
  if (!document.getElementById('chkTrail').checked) return;
  trail.forEach((i, ti) => {
    const p = PASSES[i];
    const alpha = ((ti+1)/trail.length) * 0.38;
    cx.strokeStyle = 'rgba(116,172,223,' + alpha + ')';
    cx.lineWidth = 1.5; cx.setLineDash([4,5]);
    cx.beginPath(); cx.moveTo(px(p.fx), py(p.fy)); cx.lineTo(px(p.tx), py(p.ty));
    cx.stroke(); cx.setLineDash([]);
  });
}

// ── Disegno giocatori con posizioni DINAMICHE e VISIBILITA' ───────────────
//
// Regole per ogni frame (passaggio idx, interpolazione t):
//   - PASSANTE:  posizione fissa = (fx, fy) del passaggio corrente
//   - RICEVENTE: si sposta da playerStates[idx][name] → (tx,ty) con l'avanzare di t
//   - ALTRI:     rimangono alla loro ultima posizione nota (playerStates[idx])
//   - VISIBILITA': se non isVisible(name, idx) → il giocatore non viene disegnato
//
function drawPlayers(cur, t) {
  const state = playerStates[Math.min(idx, playerStates.length-1)];
  const allNames = new Set(Object.keys(PLAYERS));
  if (cur) { allNames.add(cur.fr); allNames.add(cur.to); }

  for (const name of allNames) {
    if (!isVisible(name, idx)) continue;   // ← invisibile: non lo disegno

    let bx, by;

    if (cur && name === cur.fr) {
      bx = px(cur.fx); by = py(cur.fy);

    } else if (cur && name === cur.to) {
      const prev = state[name] || {x: cur.tx, y: cur.ty};
      const frac = Math.max(0, Math.min(1, t));
      bx = px(prev.x + (cur.tx - prev.x) * frac);
      by = py(prev.y + (cur.ty - prev.y) * frac);

    } else {
      const p = state[name];
      if (!p) continue;
      bx = px(p.x); by = py(p.y);
    }

    const isP = cur && name === cur.fr;
    const isR = cur && name === cur.to;
    const R   = (isP || isR) ? 13 : 10;

    cx.shadowColor = isP ? '#FFD700' : isR ? '#FF8C00' : 'transparent';
    cx.shadowBlur  = isP ? 20 : isR ? 16 : 0;

    cx.beginPath(); cx.arc(bx, by, R+2, 0, Math.PI*2);
    cx.strokeStyle = isP ? '#FFD700' : isR ? '#FF8C00' : 'rgba(255,255,255,0.38)';
    cx.lineWidth   = (isP||isR) ? 2.5 : 1;
    cx.stroke();

    cx.fillStyle = isP ? '#FFD700' : isR ? '#FF8C00' : '#74ACDF';
    cx.beginPath(); cx.arc(bx, by, R, 0, Math.PI*2); cx.fill();
    cx.shadowBlur = 0;

    const sn = SHORTS[name] || name;
    cx.font = (isP||isR) ? 'bold 11px Segoe UI' : '10px Segoe UI';
    cx.textAlign = 'center'; cx.textBaseline = 'top';
    const tw = cx.measureText(sn).width + 8;
    cx.fillStyle = 'rgba(13,17,23,0.78)';
    cx.fillRect(bx - tw/2, by + R + 3, tw, 14);
    cx.fillStyle = isP ? '#FFD700' : isR ? '#FF8C00' : 'rgba(255,255,255,0.88)';
    cx.fillText(sn, bx, by + R + 4);
  }
}

// ── Disegno pallone ────────────────────────────────────────────────────────
function drawBall(cur, t) {
  const fx = px(cur.fx), fy = py(cur.fy);
  const tx = px(cur.tx), ty = py(cur.ty);
  const mx = (fx+tx)/2, my = (fy+ty)/2;
  const dx = tx-fx, dy = ty-fy;
  const len = Math.sqrt(dx*dx+dy*dy) || 1;
  const cpx = mx - (dy/len)*Math.min(len*0.18,28);
  const cpy = my + (dx/len)*Math.min(len*0.18,28);

  const bx = (1-t)*(1-t)*fx + 2*(1-t)*t*cpx + t*t*tx;
  const by = (1-t)*(1-t)*fy + 2*(1-t)*t*cpy + t*t*ty;

  cx.strokeStyle = 'rgba(255,255,255,0.11)'; cx.lineWidth = 1.2; cx.setLineDash([3,6]);
  cx.beginPath(); cx.moveTo(fx,fy); cx.quadraticCurveTo(cpx,cpy,tx,ty); cx.stroke(); cx.setLineDash([]);

  if (t > 0.7) {
    cx.globalAlpha = (t-0.7)/0.3*0.72;
    const angle = Math.atan2(ty-fy,tx-fx);
    cx.strokeStyle='rgba(255,255,255,0.9)'; cx.lineWidth=2;
    cx.beginPath();
    cx.moveTo(tx,ty); cx.lineTo(tx-10*Math.cos(angle-0.42),ty-10*Math.sin(angle-0.42));
    cx.moveTo(tx,ty); cx.lineTo(tx-10*Math.cos(angle+0.42),ty-10*Math.sin(angle+0.42));
    cx.stroke(); cx.globalAlpha=1;
  }

  const grd = cx.createRadialGradient(bx,by,0,bx,by,16);
  grd.addColorStop(0,'rgba(255,255,210,0.52)'); grd.addColorStop(1,'rgba(255,255,210,0)');
  cx.fillStyle=grd; cx.beginPath(); cx.arc(bx,by,16,0,Math.PI*2); cx.fill();

  cx.fillStyle='rgba(0,0,0,0.28)'; cx.beginPath(); cx.ellipse(bx,by+6,5,2,0,0,Math.PI*2); cx.fill();

  cx.shadowColor='rgba(255,255,200,0.9)'; cx.shadowBlur=14;
  cx.fillStyle='#FFFFFF'; cx.beginPath(); cx.arc(bx,by,6.5,0,Math.PI*2); cx.fill();
  cx.shadowBlur=0;
  cx.fillStyle='rgba(60,60,60,0.22)'; cx.beginPath(); cx.arc(bx-1.5,by-1.5,3,0,Math.PI*2); cx.fill();
}

function drawEndScreen() {
  cx.fillStyle='rgba(0,0,0,0.55)'; cx.fillRect(PX,PY,PW,PH);
  cx.fillStyle='#74ACDF'; cx.font='bold 25px Segoe UI';
  cx.textAlign='center'; cx.textBaseline='middle';
  cx.fillText('Animazione completata', CW/2, CH/2-18);
  cx.fillStyle='#8b949e'; cx.font='14px Segoe UI';
  cx.fillText(N+' passaggi — Argentina vs Francia', CW/2, CH/2+16);
}

function draw() {
  cx.clearRect(0, 0, CW, CH);
  drawPitch();
  drawTrail();
  const cur = idx < N ? PASSES[idx] : null;
  drawPlayers(cur, t);
  if (idx < N) drawBall(cur, t);
  else drawEndScreen();
}

updateInfo(); draw();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
