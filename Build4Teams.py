"""
Costruisce le 4 reti passaggi aggregate (Argentina, France, Croatia, Morocco)
sull'intero torneo WC 2022. Applica il filtro dei 30 minuti.
Produce: 4 NetworkX DiGraph (pickle) + tabelle metadata.
"""
import json, glob, os, pickle
from collections import defaultdict, Counter
import pandas as pd
import networkx as nx

TEAMS = ['Argentina', 'France', 'Croatia', 'Morocco']
EVENTS_DIR = '/home/francesco/Desktop/open-data/data/events'
LINEUPS_DIR = '/home/francesco/Desktop/open-data/data/lineups'
OUT_DIR = '/home/francesco/Desktop/ProgettoAVRC/networks'
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- 1. Minuti giocati per (player, team) sommando tutte le partite ----------
mins = defaultdict(lambda: defaultdict(float))  # mins[team][player_name] = total minutes
positions_log = defaultdict(lambda: defaultdict(list))  # positions per player

def to_minutes(t):
    """Parse '88:12' -> 88.2 minutes float."""
    if t is None: return 0.0
    parts = t.split(':')
    return int(parts[0]) + int(parts[1])/60.0

for lf in glob.glob(f'{LINEUPS_DIR}/*.json'):
    with open(lf) as f:
        L = json.load(f)
    for team in L:
        tname = team['team_name']
        if tname not in TEAMS: continue
        for p in team['lineup']:
            pname = p['player_name']
            for pos in p.get('positions', []):
                start = to_minutes(pos['from'])
                end_str = pos.get('to')
                # if 'to' is None, the player stayed until the end (assume 90+)
                end = to_minutes(end_str) if end_str else 90.0
                # add periods for extra time
                tp = pos.get('to_period') or 1
                fp = pos.get('from_period') or 1
                if tp >= 3: end += 15
                if tp >= 4: end += 15
                if fp >= 3: start += 15  # rough heuristic ok
                dur = max(0.0, end - start)
                mins[tname][pname] += dur
                positions_log[tname][pname].append((pos['position'], dur))

# nominal position = position with longest cumulative duration
def nominal_pos(positions_with_durations):
    by_pos = defaultdict(float)
    for pos, d in positions_with_durations:
        by_pos[pos] += d
    return max(by_pos.items(), key=lambda kv: kv[1])[0]

POS_TO_LINE = {  # StatsBomb position name -> tactical line
    'Goalkeeper': 'GK',
    # Defenders
    'Right Back': 'DEF', 'Left Back': 'DEF',
    'Right Center Back': 'DEF', 'Left Center Back': 'DEF', 'Center Back': 'DEF',
    'Right Wing Back': 'DEF', 'Left Wing Back': 'DEF',
    # Midfielders
    'Right Defensive Midfield': 'MID', 'Center Defensive Midfield': 'MID',
    'Left Defensive Midfield': 'MID',
    'Right Midfield': 'MID', 'Center Midfield': 'MID', 'Left Midfield': 'MID',
    'Right Center Midfield': 'MID', 'Left Center Midfield': 'MID',
    'Right Attacking Midfield': 'MID', 'Center Attacking Midfield': 'MID',
    'Left Attacking Midfield': 'MID',
    # Attackers
    'Right Wing': 'ATT', 'Left Wing': 'ATT',
    'Center Forward': 'ATT', 'Right Center Forward': 'ATT', 'Left Center Forward': 'ATT',
    'Secondary Striker': 'ATT',
}

# ---------- 2. Aggrega passaggi completati per squadra ----------
edges = {t: Counter() for t in TEAMS}       # (passer, recipient) -> count
locs_start = {t: defaultdict(list) for t in TEAMS}  # player -> [(x,y), ...]
locs_end   = {t: defaultdict(list) for t in TEAMS}
lengths    = {t: defaultdict(list) for t in TEAMS}  # edge -> [length, ...]

for ef in glob.glob(f'{EVENTS_DIR}/*.json'):
    with open(ef) as f:
        events = json.load(f)
    for e in events:
        if e['type']['name'] != 'Pass': continue
        team = e['team']['name']
        if team not in TEAMS: continue
        p = e['pass']
        if 'outcome' in p: continue
        if 'recipient' not in p: continue
        passer = e['player']['name']
        recipient = p['recipient']['name']
        edges[team][(passer, recipient)] += 1
        locs_start[team][passer].append(tuple(e['location']))
        locs_end[team][recipient].append(tuple(p['end_location']))
        lengths[team][(passer, recipient)].append(p['length'])

# ---------- 3. Filtro 30 minuti e costruzione grafo ----------
MIN_THRESHOLD = 30.0
networks = {}
node_attrs_all = {}

for t in TEAMS:
    # Determine eligible nodes
    eligible = {p for p, m in mins[t].items() if m >= MIN_THRESHOLD}

    G = nx.DiGraph(team=t)
    for (u, v), w in edges[t].items():
        if u in eligible and v in eligible:
            edge_lengths = lengths[t][(u, v)]
            G.add_edge(u, v, weight=w,
                       mean_length=sum(edge_lengths)/len(edge_lengths))

    # Node attributes
    for n in list(G.nodes()):
        positions = positions_log[t].get(n, [])
        if not positions: continue
        np_ = nominal_pos(positions)
        G.nodes[n]['nominal_position'] = np_
        G.nodes[n]['line'] = POS_TO_LINE.get(np_, 'OTHER')
        G.nodes[n]['minutes'] = round(mins[t][n], 1)
        # mean position from pass start+end locations
        starts = locs_start[t].get(n, [])
        ends   = locs_end[t].get(n, [])
        all_pts = starts + ends
        if all_pts:
            mx = sum(x for x, _ in all_pts) / len(all_pts)
            my = sum(y for _, y in all_pts) / len(all_pts)
            G.nodes[n]['x'] = mx
            G.nodes[n]['y'] = my

    networks[t] = G

# ---------- 4. Report ----------
summary_rows = []
for t in TEAMS:
    G = networks[t]
    summary_rows.append({
        'team': t,
        'nodes': G.number_of_nodes(),
        'edges': G.number_of_edges(),
        'total_passes': sum(d['weight'] for _, _, d in G.edges(data=True)),
        'density': round(nx.density(G), 3),
        'reciprocity': round(nx.reciprocity(G), 3),
        'GK': sum(1 for n in G.nodes() if G.nodes[n].get('line')=='GK'),
        'DEF': sum(1 for n in G.nodes() if G.nodes[n].get('line')=='DEF'),
        'MID': sum(1 for n in G.nodes() if G.nodes[n].get('line')=='MID'),
        'ATT': sum(1 for n in G.nodes() if G.nodes[n].get('line')=='ATT'),
    })

df = pd.DataFrame(summary_rows)
print("=== AGGREGATED TEAM-TOURNAMENT NETWORKS (WC 2022 semifinalists) ===")
print(df.to_string(index=False))

# Save
for t, G in networks.items():
    with open(f'{OUT_DIR}/{t}.gpickle', 'wb') as f:
        pickle.dump(G, f)
df.to_csv(f'{OUT_DIR}/summary.csv', index=False)
print(f"\nSaved 4 .gpickle files and summary.csv to {OUT_DIR}")