import json, os, pickle
from collections import defaultdict, Counter
import pandas as pd
import networkx as nx

# CONFIG ---------------------------------------------------------------------
TEAMS         = ["Argentina", "France", "Croatia", "Morocco"]

# Aggiungo la BASE_DIR per comodità di navigazione nel dataset
BASE_DIR      = "/home/francesco/Desktop/open-data/data"
EVENTS_DIR    = f"{BASE_DIR}/events"
LINEUPS_DIR   = f"{BASE_DIR}/lineups"
MATCHES_FILE  = f"{BASE_DIR}/matches/43/106.json" # 43 = Mondiale, 106 = 2022
OUT_DIR       = "./networks"
MIN_THRESHOLD = 30.0

os.makedirs(OUT_DIR, exist_ok=True)

# 1. Recupera i match_id esatti dal file della competizione
with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
    matches_data = json.load(f)

target_match_ids = []
for match in matches_data:
    home = match["home_team"]["home_team_name"]
    away = match["away_team"]["away_team_name"]
    
    # Se almeno una delle due squadre è tra le semifinaliste, salviamo l'ID
    if home in TEAMS or away in TEAMS:
        target_match_ids.append(match["match_id"])

# 2. Costruisci i percorsi specifici puntando solo a quei file
event_files = [f"{EVENTS_DIR}/{mid}.json" for mid in target_match_ids if os.path.exists(f"{EVENTS_DIR}/{mid}.json")]
lineup_files = [f"{LINEUPS_DIR}/{mid}.json" for mid in target_match_ids if os.path.exists(f"{LINEUPS_DIR}/{mid}.json")]

print(f"Found {len(event_files)} event files and {len(lineup_files)} lineup files.")
if len(event_files) != 23 or len(lineup_files) != 23:
    print("WARNING: Expected 23 of each (one per semifinalist match).")

# STEP 1 — Cumulative minutes per player ------------------------------------
mins          = defaultdict(lambda: defaultdict(float))
positions_log = defaultdict(lambda: defaultdict(list))

def parse_clock(t):
    if t is None: return 0.0
    parts = t.split(":"); return int(parts[0]) + int(parts[1]) / 60.0

for lf in lineup_files:
    with open(lf) as f:
        lineup_json = json.load(f)
    for team_entry in lineup_json:
        tname = team_entry["team_name"]
        if tname not in TEAMS: continue
        for player in team_entry["lineup"]:
            pname = player["player_name"]
            for pos in player.get("positions", []):
                start = parse_clock(pos.get("from"))
                end   = parse_clock(pos.get("to")) if pos.get("to") else 90.0
                from_period = pos.get("from_period") or 1
                to_period   = pos.get("to_period")   or 1
                if to_period   >= 3: end   += 15
                if to_period   >= 4: end   += 15
                if from_period >= 3: start += 15
                duration = max(0.0, end - start)
                mins[tname][pname] += duration
                positions_log[tname][pname].append((pos["position"], duration))

def nominal_position(positions):
    by_pos = defaultdict(float)
    for pos, d in positions: by_pos[pos] += d
    return max(by_pos.items(), key=lambda kv: kv[1])[0]

POSITION_TO_LINE = {
    "Goalkeeper": "GK",
    "Right Back": "DEF", "Left Back": "DEF",
    "Right Center Back": "DEF", "Left Center Back": "DEF", "Center Back": "DEF",
    "Right Wing Back": "DEF", "Left Wing Back": "DEF",
    "Right Defensive Midfield": "MID", "Center Defensive Midfield": "MID",
    "Left Defensive Midfield": "MID",
    "Right Midfield": "MID", "Center Midfield": "MID", "Left Midfield": "MID",
    "Right Center Midfield": "MID", "Left Center Midfield": "MID",
    "Right Attacking Midfield": "MID", "Center Attacking Midfield": "MID",
    "Left Attacking Midfield": "MID",
    "Right Wing": "ATT", "Left Wing": "ATT",
    "Center Forward": "ATT",
    "Right Center Forward": "ATT", "Left Center Forward": "ATT",
    "Secondary Striker": "ATT",
}

# STEP 2 — Completed passes -------------------------------------------------
edges      = {t: Counter() for t in TEAMS}
locs_start = {t: defaultdict(list) for t in TEAMS}
locs_end   = {t: defaultdict(list) for t in TEAMS}
lengths    = {t: defaultdict(list) for t in TEAMS}

for ef in event_files:
    with open(ef) as f:
        events = json.load(f)
    for e in events:
        if e["type"]["name"] != "Pass": continue
        team = e["team"]["name"]
        if team not in TEAMS: continue
        p = e["pass"]
        if "outcome" in p: continue
        if "recipient" not in p: continue
        passer    = e["player"]["name"]
        recipient = p["recipient"]["name"]
        edges[team][(passer, recipient)] += 1
        locs_start[team][passer].append(tuple(e["location"]))
        locs_end[team][recipient].append(tuple(p["end_location"]))
        lengths[team][(passer, recipient)].append(p["length"])

# STEP 3 — Filter and build DiGraphs ----------------------------------------
networks = {}
for t in TEAMS:
    eligible = {p for p, m in mins[t].items() if m >= MIN_THRESHOLD}
    G = nx.DiGraph(team=t)
    for (u, v), w in edges[t].items():
        if u in eligible and v in eligible:
            mean_len = sum(lengths[t][(u, v)]) / len(lengths[t][(u, v)])
            G.add_edge(u, v, weight=w, mean_length=mean_len)
    for n in list(G.nodes()):
        positions = positions_log[t].get(n, [])
        if not positions: continue
        np_ = nominal_position(positions)
        G.nodes[n]["nominal_position"] = np_
        G.nodes[n]["line"]    = POSITION_TO_LINE.get(np_, "OTHER")
        G.nodes[n]["minutes"] = round(mins[t][n], 1)
        all_pts = locs_start[t].get(n, []) + locs_end[t].get(n, [])
        if all_pts:
            mx = sum(x for x, _ in all_pts) / len(all_pts)
            my = sum(y for _, y in all_pts) / len(all_pts)
            G.nodes[n]["x"] = mx
            G.nodes[n]["y"] = my
    networks[t] = G

# STEP 4 — Report and persist -----------------------------------------------
summary_rows = []
for t in TEAMS:
    G = networks[t]
    summary_rows.append({
        "team": t, "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "total_passes": sum(d["weight"] for _,_,d in G.edges(data=True)),
        "density": round(nx.density(G), 3),
        "reciprocity": round(nx.reciprocity(G), 3),
        "GK":  sum(1 for n in G.nodes() if G.nodes[n].get("line") == "GK"),
        "DEF": sum(1 for n in G.nodes() if G.nodes[n].get("line") == "DEF"),
        "MID": sum(1 for n in G.nodes() if G.nodes[n].get("line") == "MID"),
        "ATT": sum(1 for n in G.nodes() if G.nodes[n].get("line") == "ATT"),
    })

print()
print("=" * 78)
print(" AGGREGATED TEAM-TOURNAMENT NETWORKS  (WC 2022 semifinalists)")
print("=" * 78)
print(pd.DataFrame(summary_rows).to_string(index=False))
print()
print("Expected reference values (must match exactly):")
print("  Argentina  20 nodes, 286 edges, 3813 total passes")
print("  France     23 nodes, 314 edges, 3225 total passes")
print("  Croatia    20 nodes, 281 edges, 3796 total passes")
print("  Morocco    23 nodes, 289 edges, 2271 total passes")
print()

for t, G in networks.items():
    with open(f"{OUT_DIR}/{t}.gpickle", "wb") as f:
        pickle.dump(G, f)
print(f"Saved 4 networks to {OUT_DIR}/")
