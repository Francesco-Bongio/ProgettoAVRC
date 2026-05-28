"""
Genera rq1_dashboard.html caricando i dati dal pickle.
Esegui con:  python "genera_dashboard.py"
"""
import json, pickle, sys
from pathlib import Path

HERE = Path(__file__).parent

# ── Carica pickle ─────────────────────────────────────────────────────────────
def load(name):
    p = HERE / "shared_data" / name
    if not p.exists():
        sys.exit(f"ERRORE: {p} non trovato. Esegui prima il notebook fino alla cella che salva i pickle.")
    with open(p, "rb") as f:
        return pickle.load(f)

print("Caricamento dati...")
team_graphs       = load("team_graphs.pkl")
team_centralities = load("team_centralities.pkl")
team_profiles     = load("team_profiles.pkl")
print(f"  Squadre: {list(team_graphs.keys())}")

# ── Config ────────────────────────────────────────────────────────────────────
SEMIFINALISTS = ["Argentina", "France", "Croatia", "Morocco"]
TEAM_COLORS   = {
    "Argentina": "#75AADB",
    "France":    "#002395",
    "Croatia":   "#FF0000",
    "Morocco":   "#006233",
}
MEASURES = ["in_degree","out_degree","betweenness","closeness","eigenvector","pagerank"]

# ── Serializzazione ───────────────────────────────────────────────────────────
def serialize(team):
    G, cent, prof = team_graphs[team], team_centralities[team], team_profiles[team]
    ranks = cent[MEASURES].rank(ascending=False).astype(int)
    pm    = {v: k for k, v in prof.items()}
    nodes = []
    for name in cent.index:
        if name not in G.nodes:
            continue
        r = cent.loc[name]
        nodes.append({
            "name":       name,
            "short":      name.split()[-1],
            "avg_x":      round(float(G.nodes[name].get("avg_x", 60)), 2),
            "avg_y":      round(float(G.nodes[name].get("avg_y", 40)), 2),
            **{m: round(float(r[m]), 5) for m in MEASURES},
            "rank_total": int(ranks.loc[name].sum()),
            "ranks":      {m: int(ranks.loc[name, m]) for m in MEASURES},
            "profile":    pm.get(name),
        })
    edges = [
        {"source": u, "target": v, "weight": int(d["weight"])}
        for u, v, d in G.edges(data=True)
        if u in cent.index and v in cent.index
    ]
    return {
        "nodes":         nodes,
        "edges":         edges,
        "profiles":      {k: v.split()[-1] for k, v in prof.items()},
        "profiles_full": {k: v for k, v in prof.items()},
        "color":         TEAM_COLORS[team],
    }

print("Serializzazione...")
DATA = {t: serialize(t) for t in SEMIFINALISTS}
for t, d in DATA.items():
    print(f"  {t}: {len(d['nodes'])} nodi, {len(d['edges'])} archi")

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>RQ1 — Reti di Passaggio Semifinaliste 2022</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;font-family:'Segoe UI',Arial,sans-serif;color:#e6edf3;
  display:flex;flex-direction:column;align-items:center;padding:14px;gap:12px;min-height:100vh}
header{text-align:center}
header h1{font-size:20px;font-weight:700}
header p{font-size:12px;color:#8b949e;margin-top:4px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;justify-content:center}
.tab{padding:7px 20px;border-radius:20px;border:1px solid #30363d;background:#161b22;
  color:#8b949e;cursor:pointer;font-size:13px;font-family:inherit;transition:all .15s}
.tab:hover{background:#21262d;color:#e6edf3}
.tab.active{color:#fff;border-color:transparent;font-weight:600}
.row{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;width:100%;max-width:1160px}
.box{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;
  display:flex;flex-direction:column;gap:8px}
.bt{font-size:13px;font-weight:600;color:#8b949e}
.ec{font-size:12px;color:#8b949e;display:flex;align-items:center;gap:8px}
.ec input{accent-color:#58a6ff;width:130px;cursor:pointer}
#tv{color:#e6edf3;font-weight:600;min-width:22px}
.pp{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;width:100%;max-width:1160px}
.pc{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 20px;
  flex:1;min-width:230px;max-width:350px}
.pt{font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;font-weight:700}
.pn{font-size:15px;font-weight:700;color:#e6edf3;margin-bottom:2px}
.pf{font-size:11px;color:#6e7681;margin-bottom:5px}
.pd{font-size:11px;color:#8b949e}
.leg{display:flex;gap:16px;font-size:11px;color:#8b949e;flex-wrap:wrap;justify-content:center}
.li{display:flex;align-items:center;gap:5px}
.ld{width:11px;height:11px;border-radius:50%;flex-shrink:0}
#tip{position:fixed;background:#1c2128;border:1px solid #30363d;border-radius:8px;
  padding:9px 13px;font-size:12px;color:#e6edf3;pointer-events:none;opacity:0;
  transition:opacity .1s;max-width:240px;line-height:1.65;z-index:100}
</style></head><body>
<header>
  <h1>RQ1 — Reti di Passaggio · Semifinaliste Mondiale 2022</h1>
  <p>Rete aggregata sulle 7 partite &nbsp;·&nbsp; Dimensione nodo ∝ betweenness &nbsp;·&nbsp; Archi filtrabili per peso</p>
</header>
<div class="tabs">
  <button class="tab active" data-team="Argentina">🇦🇷 Argentina</button>
  <button class="tab" data-team="France">🇫🇷 France</button>
  <button class="tab" data-team="Croatia">🇭🇷 Croatia</button>
  <button class="tab" data-team="Morocco">🇲🇦 Morocco</button>
</div>
<div class="row">
  <div class="box">
    <div class="bt">Rete — <span id="nt">Argentina</span></div>
    <svg id="net"></svg>
    <div class="ec">Soglia arco: <span id="tv">20</span>
      <input type="range" id="thr" min="1" max="300" value="20" oninput="setT(+this.value)">
    </div>
  </div>
  <div class="box">
    <div class="bt">Ranghi di Centralità — Top 10</div>
    <svg id="hm"></svg>
  </div>
</div>
<div class="pp" id="pp"></div>
<div class="leg">
  <span class="li"><span class="ld" style="background:#FFD700"></span>Terminal</span>
  <span class="li"><span class="ld" style="background:#FF6B6B"></span>Broker</span>
  <span class="li"><span class="ld" style="background:#4ECDC4"></span>Metronome</span>
  <span class="li"><span class="ld" style="background:#555"></span>Altri</span>
</div>
<div id="tip"></div>
<script>
const DATA=__DATA__;
const MS=["in_degree","out_degree","betweenness","closeness","eigenvector","pagerank"];
const ML=["In-Deg","Out-Deg","Betweenness","Closeness","Eigenvec.","PageRank"];
const PC={terminal:"#FFD700",broker:"#FF6B6B",metronome:"#4ECDC4"};
const PD={terminal:"Destinazione finale del flusso — riceve più di quanto passa",
          broker:"Ponte tra reparti — alta betweenness centrality",
          metronome:"Cuore del possesso — alto eigenvector, distribuisce verso i centrali"};
const NW=620,NH=415,PM={t:22,r:22,b:22,l:22},PW=620-44,PH=415-44;
const px=x=>PM.l+x*(PW/120),py=y=>PM.t+y*(PH/80);
let team="Argentina",thr=20;
const svg=d3.select("#net").attr("width",NW).attr("height",NH);
const hm=d3.select("#hm");
const tip=d3.select("#tip");
const sT=(e,h)=>tip.html(h).style("opacity",1).style("left",(e.clientX+16)+"px").style("top",(e.clientY-8)+"px");
const mT=e=>tip.style("left",(e.clientX+16)+"px").style("top",(e.clientY-8)+"px");
const hT=()=>tip.style("opacity",0);
(function(){
  const g=svg.append("g");
  g.append("rect").attr("x",PM.l).attr("y",PM.t).attr("width",PW).attr("height",PH).attr("fill","#2d5a27");
  const sw=PW/10;
  for(let i=0;i<10;i+=2)g.append("rect").attr("x",PM.l+i*sw).attr("y",PM.t).attr("width",sw).attr("height",PH).attr("fill","rgba(255,255,255,.022)");
  const ln=(x1,y1,x2,y2,w=1.5)=>g.append("line").attr("x1",px(x1)).attr("y1",py(y1)).attr("x2",px(x2)).attr("y2",py(y2)).attr("stroke","white").attr("stroke-width",w);
  const rc=(x,y,w,h,s=1.5)=>g.append("rect").attr("x",px(x)).attr("y",py(y)).attr("width",px(x+w)-px(x)).attr("height",py(y+h)-py(y)).attr("fill","none").attr("stroke","white").attr("stroke-width",s);
  rc(0,0,120,80,2);ln(60,0,60,80);rc(0,18,18,44);rc(102,18,18,44);rc(0,30,6,20,1);rc(114,30,6,20,1);
  g.append("circle").attr("cx",px(60)).attr("cy",py(40)).attr("r",10*(PW/120)).attr("fill","none").attr("stroke","white").attr("stroke-width",1.5);
  g.append("circle").attr("cx",px(60)).attr("cy",py(40)).attr("r",3).attr("fill","white");
  g.append("circle").attr("cx",px(12)).attr("cy",py(40)).attr("r",2.5).attr("fill","white");
  g.append("circle").attr("cx",px(108)).attr("cy",py(40)).attr("r",2.5).attr("fill","white");
  const gh=py(44)-py(36);
  g.append("rect").attr("x",px(0)-8).attr("y",py(36)).attr("width",8).attr("height",gh).attr("fill","none").attr("stroke","white").attr("stroke-width",2);
  g.append("rect").attr("x",px(120)).attr("y",py(36)).attr("width",8).attr("height",gh).attr("fill","none").attr("stroke","white").attr("stroke-width",2);
})();
const nl=svg.append("g");
function drawNet(t){
  nl.selectAll("*").remove();
  const{nodes,edges,color}=DATA[t];
  const act=edges.filter(e=>e.weight>=thr);
  const nm=new Map(nodes.map(n=>[n.name,n]));
  const mB=d3.max(nodes,d=>d.betweenness)||1,mW=d3.max(act,e=>e.weight)||1;
  const r=d=>7+(d.betweenness/mB)*18;
  nl.selectAll(".e").data(act).join("line").attr("class","e")
    .attr("x1",d=>px(nm.get(d.source)?.avg_x??60)).attr("y1",d=>py(nm.get(d.source)?.avg_y??40))
    .attr("x2",d=>px(nm.get(d.target)?.avg_x??60)).attr("y2",d=>py(nm.get(d.target)?.avg_y??40))
    .attr("stroke","rgba(255,255,255,.6)").attr("stroke-width",d=>.5+(d.weight/mW)*4.5)
    .attr("stroke-opacity",d=>.12+(d.weight/mW)*.6);
  const ng=nl.selectAll(".ng").data(nodes).join("g").attr("class","ng")
    .attr("transform",d=>`translate(${px(d.avg_x)},${py(d.avg_y)})`).style("cursor","pointer")
    .on("mouseover",(e,d)=>sT(e,`<strong>${d.name}</strong><br>Betweenness: ${d.betweenness.toFixed(3)}<br>PageRank: ${d.pagerank.toFixed(3)}<br>In: ${d.in_degree.toFixed(3)} | Out: ${d.out_degree.toFixed(3)}${d.profile?`<br><em style="color:${PC[d.profile]}">${d.profile}</em>`:""}`))
    .on("mousemove",mT).on("mouseout",hT);
  ng.append("circle").attr("r",d=>r(d)).attr("fill",d=>d.profile?PC[d.profile]:color)
    .attr("stroke","white").attr("stroke-width",d=>d.profile?2.5:1.2).attr("fill-opacity",.9);
  ng.append("text").attr("y",d=>-r(d)-3).attr("text-anchor","middle")
    .attr("font-size","9.5px").attr("font-weight","700").attr("fill","white")
    .attr("pointer-events","none").text(d=>d.short);
}
function drawHM(t){
  hm.selectAll("*").remove();
  const{nodes}=DATA[t];
  const n=nodes.length,top=[...nodes].sort((a,b)=>a.rank_total-b.rank_total).slice(0,10);
  const cW=46,cH=34,mL=100,mT=52,mR=16,mB=10;
  hm.attr("width",mL+MS.length*cW+mR).attr("height",mT+top.length*cH+mB);
  const cl=r=>d3.interpolateRdYlGn(n>1?1-(r-1)/(n-1):.5);
  const g=hm.append("g").attr("transform",`translate(${mL},${mT})`);
  g.selectAll(".ch").data(ML).join("text").attr("class","ch")
    .attr("x",(d,i)=>i*cW+cW/2).attr("y",-10).attr("text-anchor","middle")
    .attr("font-size","10px").attr("fill","#8b949e").text(d=>d);
  top.forEach((pl,row)=>{
    g.append("text").attr("x",-8).attr("y",row*cH+cH/2).attr("text-anchor","end")
      .attr("dominant-baseline","middle").attr("font-size","11px")
      .attr("fill",pl.profile?PC[pl.profile]:"#e6edf3").text(pl.short);
    MS.forEach((m,ci)=>{
      const rk=pl.ranks[m];
      g.append("rect").attr("x",ci*cW).attr("y",row*cH).attr("width",cW-2).attr("height",cH-2)
        .attr("fill",cl(rk)).attr("rx",3)
        .on("mouseover",e=>sT(e,`<strong>${pl.name}</strong><br>${ML[ci]}<br>Rango: <strong>${rk}</strong> / ${n}`))
        .on("mousemove",mT).on("mouseout",hT);
      g.append("text").attr("x",ci*cW+cW/2).attr("y",row*cH+cH/2)
        .attr("text-anchor","middle").attr("dominant-baseline","middle")
        .attr("font-size","11px").attr("font-weight","600")
        .attr("fill",rk<=Math.ceil(n*.4)?"#111":"#eee")
        .attr("pointer-events","none").text(rk);
    });
  });
}
function drawP(t){
  const{profiles,profiles_full}=DATA[t];
  document.getElementById("pp").innerHTML=["terminal","broker","metronome"].map(tp=>`
    <div class="pc">
      <div class="pt" style="color:${PC[tp]}">${tp}</div>
      <div class="pn">${profiles[tp]||"—"}</div>
      <div class="pf">${profiles_full[tp]||""}</div>
      <div class="pd">${PD[tp]}</div>
    </div>`).join("");
}
function render(t){team=t;d3.select("#nt").text(t);drawNet(t);drawHM(t);drawP(t);}
document.querySelectorAll(".tab").forEach(b=>{
  b.addEventListener("click",()=>{
    document.querySelectorAll(".tab").forEach(x=>{x.classList.remove("active");x.style.background="";x.style.borderColor="";});
    b.classList.add("active");b.style.background=DATA[b.dataset.team].color;b.style.borderColor=DATA[b.dataset.team].color;
    render(b.dataset.team);
  });
});
function setT(v){thr=v;document.getElementById("tv").textContent=v;drawNet(team);}
const fb=document.querySelector(".tab.active");
fb.style.background=DATA["Argentina"].color;fb.style.borderColor=DATA["Argentina"].color;
render("Argentina");
</script></body></html>"""

# ── Scrivi HTML ───────────────────────────────────────────────────────────────
html_out  = HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
out_path  = HERE / "rq1_dashboard.html"
out_path.write_text(html_out, encoding="utf-8")
print(f"\n✓ Salvato: {out_path}  ({len(html_out)//1024} KB)")
