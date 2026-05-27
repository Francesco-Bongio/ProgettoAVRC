"""
Esporta le 4 reti delle semifinaliste WC2022 in un singolo JSON pronto per D3.
Stessa pipeline del notebook RQ3 (build_aggregated_network, weighted betweenness,
avg_path_length, efficiency con convention distance = 1/weight).

In più precalcola:
  - baseline metrics
  - outcome di rimozione per OGNI singolo giocatore (così la viz interattiva è
    istantanea: click -> lookup, nessun calcolo client-side)
  - sequenza di rimozione progressiva greedy (1->2->3 top-betweenness)
  - distribuzione delle rimozioni casuali (200 trials di outfield players)
  - pivot identity + fragility z-score per il pannello "RQ1 prevede RQ3?"
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, pickle, random
import numpy as np
import pandas as pd
import networkx as nx

# ----------------------------------------------------------------------------
# Costanti (identiche al notebook)
# ----------------------------------------------------------------------------
COMPETITION_ID = 43
SEASON_ID      = 106
TEAMS          = ["Argentina", "France", "Croatia", "Morocco"]
MIN_MINUTES    = 30
N_RANDOM       = 200
RANDOM_SEED    = 42

ALIASES = {
    "Lionel Andrés Messi Cuccittini": "Messi",
    "Rodrigo Javier De Paul":          "De Paul",
    "Nicolás Hernán Otamendi":         "Otamendi",
    "Enzo Fernandez":                  "Fernandez",
    # Disambiguazione dei tre Martínez argentini (avevano tutti lo stesso
    # cognome). Soprannomi usati comunemente dai media.
    "Damián Emiliano Martínez":        "E. Martínez",     # il portiere ("Dibu")
    "Lisandro Martínez":               "L. Martínez",     # il difensore ("Licha")
    "Lautaro Javier Martínez":         "Lautaro",         # l'attaccante (nome di battesimo)
    "Kylian Mbappé Lottin":            "Mbappé",
    "Aurélien Djani Tchouaméni":       "Tchouaméni",
    "Antoine Griezmann":               "Griezmann",
    "Randal Kolo Muani":               "Kolo Muani",
    "Achraf Hakimi Mouh":              "Hakimi",
    "Yahia Attiyat allah":             "Attiyat-Allah",
    "Luka Modrić":                     "Modrić",
    "Mateo Kovačić":                   "Kovačić",
    "Marcelo Brozović":                "Brozović",
    "Joško Gvardiol":                  "Gvardiol",
    "Sofyan Amrabat":                  "Amrabat",
}
def short(n):
    return ALIASES.get(n, n.split()[-1])


def check_no_collisions(graphs):
    """Verifica che nessuna squadra abbia short-name duplicati.
    Se trova una collisione, alza un errore con i full-name coinvolti — così
    sappiamo subito quali alias aggiungere ad ALIASES."""
    from collections import defaultdict
    problems = []
    for team, G in graphs.items():
        groups = defaultdict(list)
        for n in G.nodes():
            groups[short(n)].append(n)
        for sn, fulls in groups.items():
            if len(fulls) > 1:
                problems.append((team, sn, fulls))
    if problems:
        msg = ["Short-name collisions found — please add explicit ALIASES:"]
        for team, sn, fulls in problems:
            msg.append(f"  [{team}] {sn!r} matched by: {fulls}")
        raise ValueError("\n".join(msg))

# Colori reparto (identici al notebook)
LINE_COLORS = {"GK":"#FCBF49","DEF":"#3A86FF","MID":"#E63946","ATT":"#06D6A0"}
TEAM_COLORS = {"Argentina":"#75AADB","France":"#002395",
               "Croatia":"#C44E52","Morocco":"#006233"}

# ----------------------------------------------------------------------------
# Classifier reparto (identico al notebook)
# ----------------------------------------------------------------------------
def _classify_line(position_name):
    if not isinstance(position_name, str): return "MID"
    p = position_name.lower()
    if "goalkeeper" in p: return "GK"
    if "back" in p: return "DEF"
    if "wing" in p and "wing back" not in p: return "ATT"
    if "forward" in p or "striker" in p or "centre-forward" in p: return "ATT"
    if "midfield" in p: return "MID"
    return "MID"

# ----------------------------------------------------------------------------
# Costruzione rete (identica al notebook)
# ----------------------------------------------------------------------------
def build_aggregated_network(team_name, match_ids, min_minutes=MIN_MINUTES):
    from statsbombpy import sb
    all_passes = []
    player_total_minutes = {}
    player_position = {}
    for mid in match_ids:
        events = sb.events(match_id=mid)
        lineups = events[(events["type"]=="Starting XI") & (events["team"]==team_name)]
        for _, row in lineups.iterrows():
            tactics = row.get("tactics")
            if isinstance(tactics, dict):
                for p in tactics.get("lineup", []):
                    name = p["player"]["name"]
                    player_total_minutes[name] = player_total_minutes.get(name, 0) + 90
                    pos = p.get("position", {})
                    if isinstance(pos, dict):
                        player_position.setdefault(name, pos.get("name", ""))
        subs = events[(events["type"]=="Substitution") & (events["team"]==team_name)]
        for _, row in subs.iterrows():
            passer = row.get("player")
            sub_info = row.get("substitution")
            if not isinstance(sub_info, dict): continue
            name_off = passer["name"] if isinstance(passer, dict) else passer
            name_on  = sub_info["replacement"]["name"]
            minute   = row.get("minute", 90)
            if name_off in player_total_minutes:
                player_total_minutes[name_off] -= (90 - minute)
            else:
                player_total_minutes[name_off] = minute
            player_total_minutes[name_on] = player_total_minutes.get(name_on, 0) + (90 - minute)
        passes = events[(events["type"]=="Pass") & (events["team"]==team_name) &
                        (events["pass_outcome"].isna())].copy()
        passes["x_start"] = passes["location"].apply(lambda l: l[0] if isinstance(l, list) else np.nan)
        passes["y_start"] = passes["location"].apply(lambda l: l[1] if isinstance(l, list) else np.nan)
        passes_clean = passes[["player","pass_recipient","x_start","y_start"]].dropna(
            subset=["player","pass_recipient"])
        all_passes.append(passes_clean)
    df = pd.concat(all_passes, ignore_index=True)
    eligible = {p for p, m in player_total_minutes.items() if m >= min_minutes}
    df = df[df["player"].isin(eligible) & df["pass_recipient"].isin(eligible)]
    edge_counts = df.groupby(["player","pass_recipient"]).size().reset_index(name="weight")
    G = nx.DiGraph()
    for _, row in edge_counts.iterrows():
        w = int(row["weight"])
        G.add_edge(row["player"], row["pass_recipient"], weight=w, distance=1.0/w)
    avg_pos = df.groupby("player").agg(x=("x_start","mean"), y=("y_start","mean")).reset_index()
    for _, row in avg_pos.iterrows():
        if row["player"] in G.nodes():
            G.nodes[row["player"]]["x"] = float(row["x"])
            G.nodes[row["player"]]["y"] = float(row["y"])
            G.nodes[row["player"]]["minutes"] = int(player_total_minutes.get(row["player"], 0))
            G.nodes[row["player"]]["line"] = _classify_line(player_position.get(row["player"], ""))
    return G

# ----------------------------------------------------------------------------
# Metriche (identiche al notebook)
# ----------------------------------------------------------------------------
def add_distance(G):
    H = G.copy()
    for u, v, d in H.edges(data=True):
        d["distance"] = 1.0 / max(d["weight"], 1e-9)
    return H

def avg_path_length(G):
    if G.number_of_nodes() < 2: return float("nan")
    largest = max(nx.weakly_connected_components(G), key=len)
    H = add_distance(G.subgraph(largest).copy())
    lengths = dict(nx.all_pairs_dijkstra_path_length(H, weight="distance"))
    values = [d for u, t in lengths.items() for v, d in t.items() if u != v]
    return float(np.mean(values)) if values else float("nan")

def efficiency(G):
    if G.number_of_nodes() < 2: return float("nan")
    H = add_distance(G)
    lengths = dict(nx.all_pairs_dijkstra_path_length(H, weight="distance"))
    values = [1.0/d for u, t in lengths.items() for v, d in t.items() if u != v and d > 0]
    return float(np.mean(values)) if values else float("nan")

def weighted_betweenness(G):
    return nx.betweenness_centrality(add_distance(G), weight="distance", normalized=True)

def n_components(G):
    return nx.number_weakly_connected_components(G)

# ----------------------------------------------------------------------------
# Load / build graphs
# ----------------------------------------------------------------------------
CACHE_PATH = "./wc2022_graphs.pkl"

def load_graphs():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "rb") as f:
            graphs = pickle.load(f)
        print(f"✓ Reti caricate dalla cache {CACHE_PATH}")
        return graphs
    print("Costruzione delle reti da StatsBomb...")
    from statsbombpy import sb
    matches = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    graphs = {}
    for team in TEAMS:
        team_matches = matches[(matches["home_team"]==team) | (matches["away_team"]==team)]
        match_ids = team_matches["match_id"].tolist()
        print(f"  {team}: {len(match_ids)} partite...", flush=True)
        G = build_aggregated_network(team, match_ids)
        graphs[team] = G
        print(f"    -> {G.number_of_nodes()} nodi, {G.number_of_edges()} archi")
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(graphs, f)
    return graphs

# ----------------------------------------------------------------------------
# Esportazione
# ----------------------------------------------------------------------------
def export_team(team, G):
    """Tutto quello che serve alla viz per una squadra."""
    bc = weighted_betweenness(G)
    out_strength = {n: int(sum(d["weight"] for _,_,d in G.out_edges(n, data=True)))
                    for n in G.nodes()}
    in_strength  = {n: int(sum(d["weight"] for _,_,d in G.in_edges(n, data=True)))
                    for n in G.nodes()}
    nodes = []
    for n, attr in G.nodes(data=True):
        nodes.append({
            "id":       short(n),
            "full":     n,
            "x":        attr.get("x", 60.0),
            "y":        attr.get("y", 40.0),
            "line":     attr.get("line", "MID"),
            "minutes":  attr.get("minutes", 0),
            "bc":       float(bc[n]),
            "out":      out_strength[n],
            "in":       in_strength[n],
        })
    nodes.sort(key=lambda d: -d["bc"])
    links = []
    for u, v, d in G.edges(data=True):
        links.append({
            "source": short(u),
            "target": short(v),
            "weight": int(d["weight"]),
        })

    # Baseline
    base = {
        "apl":  avg_path_length(G),
        "eff":  efficiency(G),
        "comp": n_components(G),
        "n":    G.number_of_nodes(),
        "m":    G.number_of_edges(),
        "passes": int(sum(d["weight"] for _,_,d in G.edges(data=True))),
    }

    # Outcome per OGNI rimozione di singolo giocatore
    print(f"  computing {G.number_of_nodes()} single-removal outcomes for {team}...")
    single = {}
    for n in G.nodes():
        H = G.copy(); H.remove_node(n)
        single[short(n)] = {
            "apl":  avg_path_length(H),
            "eff":  efficiency(H),
            "comp": n_components(H),
        }

    # Random sample (outfield only - escludi il GK)
    print(f"  computing {N_RANDOM} random-removal samples for {team}...")
    rng = random.Random(RANDOM_SEED)
    outfield = [n for n, a in G.nodes(data=True) if a.get("line") != "GK"]
    apl_random, eff_random = [], []
    for _ in range(N_RANDOM):
        v = rng.choice(outfield)
        d = single[short(v)]
        apl_random.append(d["apl"])
        eff_random.append(d["eff"])
    apl_random_arr = np.array([x for x in apl_random if not np.isnan(x)])
    eff_random_arr = np.array([x for x in eff_random if not np.isnan(x)])

    pivot = short(max(G.nodes(), key=lambda n: bc[n]))
    pivot_outcome = single[pivot]

    # z-score della rimozione del pivot rispetto alla distribuzione random
    z_apl = ((pivot_outcome["apl"] - apl_random_arr.mean()) / apl_random_arr.std()
             if apl_random_arr.std() > 0 else 0.0)
    z_eff = ((eff_random_arr.mean() - pivot_outcome["eff"]) / eff_random_arr.std()
             if eff_random_arr.std() > 0 else 0.0)

    # Sequenza progressiva greedy: a ogni passo togli il giocatore con max
    # betweenness corrente, ricalcola, ripeti.
    print(f"  computing progressive removal sequence for {team}...")
    progressive = [{"removed": [], **base}]
    G_curr = G.copy()
    removed = []
    for step in range(1, 4):
        bc_curr = weighted_betweenness(G_curr)
        if not bc_curr: break
        target = max(bc_curr.keys(), key=lambda n: bc_curr[n])
        G_curr.remove_node(target)
        removed.append(short(target))
        progressive.append({
            "removed": list(removed),
            "apl":  avg_path_length(G_curr),
            "eff":  efficiency(G_curr),
            "comp": n_components(G_curr),
            "n":    G_curr.number_of_nodes(),
            "m":    G_curr.number_of_edges(),
        })

    return {
        "nodes":    nodes,
        "links":    links,
        "baseline": base,
        "pivot":    pivot,
        "pivot_outcome": pivot_outcome,
        "single":   single,
        "random": {
            "apl_mean": float(apl_random_arr.mean()) if len(apl_random_arr) else None,
            "apl_std":  float(apl_random_arr.std())  if len(apl_random_arr) else None,
            "eff_mean": float(eff_random_arr.mean()) if len(eff_random_arr) else None,
            "eff_std":  float(eff_random_arr.std())  if len(eff_random_arr) else None,
            "apl_samples": [float(x) for x in apl_random_arr.tolist()],
            "eff_samples": [float(x) for x in eff_random_arr.tolist()],
            "n_samples": int(len(apl_random_arr)),
        },
        "z": {"apl": float(z_apl), "eff": float(z_eff)},
        "progressive": progressive,
    }


def main():
    graphs = load_graphs()
    check_no_collisions(graphs)
    out = {
        "meta": {
            "tournament":  "FIFA World Cup 2022",
            "teams":       TEAMS,
            "team_colors": TEAM_COLORS,
            "line_colors": LINE_COLORS,
            "n_random":    N_RANDOM,
            "min_minutes": MIN_MINUTES,
        },
        "teams": {}
    }
    for team in TEAMS:
        print(f"--- {team} ---")
        out["teams"][team] = export_team(team, graphs[team])
    with open("/home/claude/wc2022_for_d3.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n✓ wc2022_for_d3.json scritto ({os.path.getsize('/home/claude/wc2022_for_d3.json')/1024:.1f} KB)")

if __name__ == "__main__":
    main()
