# Project Report (v3) — Passing Networks of the 2022 World Cup Semifinalists

*Analisi e Visualizzazione delle Reti Complesse — Network Science module, final project.*

> **Status note.** This document supersedes v2 of the proposal. It is no longer
> a forward-looking proposal: the three research questions have been answered
> and the findings are integrated below. The structure follows that of v2 to
> keep the registration-document flow intact, but Sections 4 (Findings) and 7
> (Methodological notes) reflect actual experimental results rather than
> expected ones. Visual design and the interactive deliverable remain forward
> work and are scoped in Section 5.

## Abstract

StatsBomb's open-data release of the 2022 FIFA World Cup provides event-level coverage of all 64 matches, with every on-ball event timestamped to the second and annotated with (x, y) pitch coordinates on a 120 × 80 metre frame. From this stream we extract completed passes and build, for each of the **four semifinalists** — Argentina, France, Croatia, Morocco — a single weighted, directed passing network that aggregates all matches the team played during the tournament. Each network has 20–23 nodes (players who touched the ball and played at least 30 cumulative minutes), 281–314 active edges, and a total edge weight of 2 271–3 813 passes.

The project answers three research questions, each tied to a specific block of the syllabus. **RQ1** (centrality, Lecture 6) identifies the structural pivot of each team, using five centrality measures plus PageRank, and characterises the disagreement between measures into the canonical Terminal / Broker / Metronome triad. **RQ2** (community detection, Lectures 13–15) tests whether algorithmic communities recover the four tactical lines (GK / DEF / MID / ATT) — the answer turns out to be negative, and the project converts that negative result into a positive finding by testing two alternative ground truths and identifying what the algorithms *do* recover. **RQ3** (robustness, Lectures 8–9) simulates targeted removal of each team's structural pivot and compares against 200 random-removal baselines, producing a fragility ranking that correlates with the pivot-dominance measure from RQ1 at Pearson r = +0.89.

The three findings reinforce each other into a single narrative: a team's robustness to losing its key player can be read off the structure of its passing network alone, without any tactical context. France, whose passing depended on Tchouaméni at a top-1 / top-2 betweenness ratio of 3.20, was the most fragile; Croatia, whose midfield consisted of three near-interchangeable hubs (Modrić, Brozović, Kovačić) at ratio 1.12, was the most robust.

## 1. Introduction and motivation

A passing network on an aggregated team-tournament basis sits in the empirical sweet spot of the syllabus: it has enough nodes (20–23) for the centrality, community-detection, and robustness algorithms of Lectures 6, 13–15, and 8 to produce meaningful answers, while remaining small enough that every finding can be checked against the lived experience of the matches. When centrality identifies Otamendi rather than Messi as Argentina's structural pivot, or when Louvain assigns Hakimi and Ziyech to one community and Mazraoui and Boufal to another, a reader who watched the tournament can confirm or contest the result without a separate dataset.

The 2022 World Cup semifinalists were chosen over the 2010 Spanish team that Peña and Touchette analysed in their canonical paper for two reasons. First, the 2022 dataset is more recent and includes more data per match (StatsBomb's annotation depth has increased substantially), which means tactical shifts, substitutions, and positional changes are recoverable in ways that the 2010 dataset did not allow. Second, the four 2022 semifinalists span a wider tactical spectrum than the four 2010 semifinalists did, which makes the comparative analysis richer.

The three research questions form a tight narrative arc:

- **RQ1 identifies the pivot.** For each team, the report names the player whose removal would most reshape the network's structure, and *measures* the gap between the pivot and the second-most-central player.
- **RQ2 places the pivot in its tactical context.** The community-detection partition shows what dimension of the team's organisation the algorithm captures — and, as it turns out, that dimension is *not* the tactical line.
- **RQ3 measures the cost of losing the pivot.** Simulated removal of the top-betweenness player and comparison against 200 random removals converts the structural claim of RQ1 into a quantitative fragility statement. The pivot-dominance measure from RQ1 then *predicts* the fragility z-score with Pearson r = +0.89.

Choosing this project means accepting two methodological commitments. The first is a **scope commitment to four teams**, which precludes statistical generalisations across the tournament but allows depth that a 32-team study cannot match. The second is a **commitment to interpretive rigour**: each metric, each ranking, each algorithmic partition is accompanied by a one-paragraph reading that ties the number to what happened on the pitch.

A useful reference point: **Peña and Touchette (2012)** report on the 2010 World Cup that the betweenness–degree disagreement pattern reliably identifies the team's central midfielder, and that the configuration-model comparison shows passing networks to be significantly more clustered than chance while preserving small-world geometry. The project reproduces the first finding (the pivots identified in §3 RQ1 are face-valid for all four teams) and complicates the second: on the dense aggregated team-tournament networks at issue here, the community-detection question turns out not to be about clustering versus a null at all, but about *which dimension of organisation* the partition reflects.

## 2. The dataset

### 2.1 Source and provenance

The data is released by **StatsBomb** under the *Open Data Licence* and hosted on GitHub at `github.com/statsbomb/open-data`. Within the repository, the FIFA World Cup 2022 has `competition_id = 43, season_id = 106`. Three file types are relevant:

- `data/matches/43/106.json` — one row per match (64 rows total) with team names, score, stage, date, stadium.
- `data/lineups/{match_id}.json` — one file per match; for each team, the squad list with `player_id`, `player_name`, `jersey_number`, a list of `positions` with timestamped from–to ranges, and a list of `cards`.
- `data/events/{match_id}.json` — one file per match (1.5–3.6 MB each); a chronologically ordered list of every on-ball event annotated with player, location, and event-type-specific metadata.

For the four semifinalists, the project consumes 23 event files corresponding to the 23 distinct matches they collectively played (five matches were "internal" to the four-team set: Morocco–Croatia in the group stage, Argentina–Croatia and France–Morocco in the semi-finals, Croatia–Morocco in the third-place playoff, Argentina–France in the final). Total volume of completed passes for the four semifinalists across the tournament: 13 105 passes — the substrate of the networks.

### 2.2 Structure and semantics

A passing event carries the following fields relevant to network construction: `team.name`, `player.name`, `pass.recipient.name`, `location` (start `[x, y]`), `pass.end_location`, `pass.length`, `pass.angle`, `pass.height`, optional `pass.outcome`. The convention is that a pass *without* an `outcome` field is a completed pass, while values like `Incomplete`, `Out`, `Pass Offside`, `Injury Clearance` mark failed passes.

For each of the four semifinalists, the project builds one **aggregated team-tournament network**: nodes are players who touched the ball and played at least 30 minutes for the national team during the tournament; directed edges are weighted by the number of completed passes from passer to recipient summed across all matches the team played.

| Team      | Nodes | Edges | Total passes | Density | Reciprocity |
|-----------|------:|------:|-------------:|--------:|------------:|
| Argentina | 20    | 286   | 3 813        | 0.75    | 0.90        |
| France    | 23    | 314   | 3 225        | 0.62    | 0.88        |
| Croatia   | 20    | 281   | 3 796        | 0.74    | 0.88        |
| Morocco   | 23    | 289   | 2 271        | 0.57    | 0.81        |

The high density (0.57–0.75) and high reciprocity (0.81–0.90) of all four networks are themselves a finding worth flagging: these are nearly complete reciprocal graphs. Morocco's lower density and reciprocity are consistent with its more direct, less circulation-heavy style and its overall lower possession-share.

Each node carries the following attributes from the lineup file: `team`, `nominal_position` (the position with the longest playing time across the tournament), `minutes_played` (summed across matches), and the derived `line` ∈ {GK, DEF, MID, ATT}. Each edge carries `weight` and `mean_length`.

### 2.3 Caveats

- **The substitution effect.** A player who entered the field for ten minutes inflates the node count without contributing meaningfully to passing structure. The project resolves this with a **30-minute aggregate threshold** at the team-tournament level.
- **Tactical shifts within and across matches.** The lineup file records that a player moved between positions with timestamped transitions; over a 7-match campaign, a player can plausibly hold three or four different nominal positions for substantial periods. The project treats the *longest-held position across the tournament* as the canonical ground-truth label, and acknowledges that this simplification underestimates the algorithmic recovery score against the LINE ground truth (§4 RQ2).
- **Goalkeeper outliers.** Goalkeepers receive few passes and make many long ones to the back line. They appear as a structural island in every community-detection partition. This is expected and treated as a fixed feature of the data, not a finding.
- **Failed passes are not edges.** A pass with `pass.outcome` is removed from the network. The networks of *completed* passes and of *attempted* passes are different objects; this project commits to the completed-pass network throughout.
- **Pitch-coordinate orientation.** StatsBomb fixes attacking direction to left-to-right per team's possession. Coordinates are team-relative, not stadium-absolute.
- **StatsBomb player names contain secondary names.** Players like Kylian Mbappé Lottin, Randal Kolo Muani, Benjamin Pavard Pi are tokenised in unintuitive ways; the pipeline includes a hand-built alias table for the four semifinalists' squads.

A reproducible pipeline is included with the deliverables. The pipeline reads 23 event JSONs and 23 lineup JSONs, applies the completeness filter and the 30-minute threshold, and produces 4 NetworkX `DiGraph` objects in approximately 8 seconds on a laptop.

## 3. Research questions and methodology

### RQ1 — Who is the structural pivot of each team, and do different centralities agree?

For each of the four aggregated team-tournament networks, the project computes the five centrality measures of Lecture 6 (in-degree weighted, out-degree weighted, weighted closeness, weighted betweenness, eigenvector) plus PageRank.

The methodological commitment for weighted centralities follows the convention from Peña and Touchette: distance-based measures (closeness, betweenness) use `1/weight`, so that frequent passes correspond to short geodesic distances. This is stated explicitly because the alternative convention (using raw weight as distance) silently produces ranks that are nearly inverted.

Three role signatures are sought across the centrality ranks:

- The **Terminal** — high in-degree and high PageRank, with betweenness disproportionately lower than the degree-based rank. The destination of ball circulation.
- The **Broker** — high betweenness with moderate degree; sits on the geodesics between defensive and offensive sub-networks. Typically a deep midfielder or a ball-playing centre-back.
- The **Metronome** — high eigenvector centrality (connected to other central players) and high out-degree, with betweenness only moderate. Distributes ball without bridging.

Pairwise Spearman rank correlations between the six measures (on the top-12 players by total touches) quantify the disagreement structure. The **top-1 / top-2 betweenness ratio** is also recorded per team, as a measure of how dominant the pivot is relative to the next-most-central player — this is the structural-dominance score that will be used as the RQ3 predictor.

### RQ2 — Do algorithmic communities recover the tactical lines (GK / DEF / MID / ATT)?

Three community-detection algorithms from Lectures 13–14:

- **Louvain** (NetworkX 3.x implementation) on the symmetrised weighted graph, 20 random seeds, best-by-modularity selected as "the" partition. Pairwise NMI across seeds reported as stability.
- **Leiden** (`leidenalg`, RBConfigurationVertexPartition) on the symmetrised weighted graph, 20 seeds, best-by-modularity selected. Pairwise NMI as stability.
- **Infomap** (the `infomap` Python package) natively on the *directed* weighted graph, 5 seeds (Infomap is largely deterministic given a single seed).

Symmetrisation convention for Louvain/Leiden: `w_sym(u,v) = w(u,v) + w(v,u)`. The asymmetry is small (reciprocity 0.81–0.90, see §2.2) and the symmetrised graph captures essentially the same information.

Algorithms are run **unconstrained** — the resolution parameter is the default 1.0 and the number of communities is not pre-set to 4. The unconstrained partition is then **merged** post-hoc: each algorithmic community is assigned, by majority vote, to one of the four tactical lines. The merge is reported transparently alongside the raw partition.

Evaluation against the LINE ground truth: NMI, AMI, per-class F1.

Following the negative results on LINE (see §4 RQ2), three alternative ground truths are also tested, **using the same algorithmic partitions** (no re-fitting):

- **SIDE** (3 classes): LEFT if the player's mean y-coordinate < 27, CENTRE if 27 ≤ y ≤ 53, RIGHT if y > 53. Pitch width is 80, so these thresholds give an approximately equal three-way split.
- **ROLE_SIDE** (up to 12 classes): `LINE × SIDE` combined, e.g. `DEF_LEFT`, `MID_CENTRE`.
- **TENURE** (2 classes): STARTER if minutes > 270 (= about three full matches), SUB otherwise.

This alternative-ground-truth analysis is the methodological response to the unexpected negative result on LINE. The conceptual motivation: a partition that fails to recover one labelling may still be informative if it recovers another — and identifying *what* the algorithm has found is more useful than concluding that it has found nothing.

### RQ3 — How robust is each team's passing network to losing its pivot?

For each team, the project simulates the removal of a single player and measures the resulting damage to the network. Two removal regimes:

- **TARGETED**: remove the top-1 player by weighted betweenness (= the structural pivot identified in RQ1).
- **RANDOM**: remove a uniformly-random outfield player (excluding the goalkeeper), averaged over **N = 200** independent realisations.

Two damage metrics, both reported as **relative damage** (positive = worse):

- **Δ avg path length** = (post − pre) / pre, computed on the largest weakly connected component using `1/weight` distance.
- **Δ efficiency** = (pre − post) / pre, where efficiency is the mean of `1/d_ij` over all reachable directed pairs.

For each (team × metric), the targeted damage is converted to a **z-score within the random-removal distribution**, and a one-sided p-value is reported as `P(random ≥ targeted)`. The **fragility z-score** of a team is the mean of its two metric z-scores; this is the headline RQ3 output.

A second analytical move: an **attack progression curve**, removing the top-1, then the top-2 (after re-computing betweenness on the post-removal graph), then the top-3. This is the standard Albert–Jeong–Barabási targeted-attack experiment, scoped to three steps because on networks of this size the curves stabilise quickly.

A predictor check: **top1/top2 betweenness ratio** (RQ1) vs. **fragility z-score** (RQ3), with Pearson and Spearman correlations. This is not a statistical claim — n = 4 — but a *consistency check* between the two experiments.

#### Methodological notes on RQ3

Two damage metrics were considered and discarded after pilot:

- **LCC size.** Always 0 across all 800 random removals and all 4 targeted removals. The networks are too dense for any single-node removal to disconnect them. Reported as a negative finding in §7.
- **|λ₂| of the symmetrised adjacency.** Behaves non-monotonically with damage on dense networks: removing the top hub flattens the spectrum (the dominant eigenvalue collapses), which can *increase* the spectral gap and produce negative "damage" against intuition. Three of the four teams showed targeted damage below the random mean on λ₂ in pilot runs; the metric was excluded from the final analysis with the rationale recorded.

The two retained metrics are theoretically sound for dense weighted directed networks and produce mutually consistent rankings (Pearson r = 0.81 between the per-team Δ avg-path-length and Δ efficiency rankings across the four teams).

## 4. Findings

### RQ1 — Structural pivots

| Team      | Broker (max betweenness) | Terminal (max in-deg + PR) | Metronome (max eig + out-deg) | top1/top2 ratio |
|-----------|--------------------------|-----------------------------|--------------------------------|----------------:|
| Argentina | **Otamendi** (DEF)       | **De Paul** (MID)          | **Fernandez** (MID)            | **1.45**        |
| France    | **Tchouaméni** (MID)     | **Rabiot** (MID)           | **Upamecano** (DEF)            | **3.20**        |
| Croatia   | **Modrić** (MID)         | **Brozović** (MID)         | **Gvardiol** (DEF)             | **1.12**        |
| Morocco   | **Amrabat** (MID)        | **El Yamiq** (DEF)         | **Hakimi** (DEF)               | **1.07**        |

All four broker identifications pass face validity. The disagreement structure between centralities, measured by pairwise Spearman correlations on the top 12 players per team, ranges from 0.83–0.99 (Argentina, Croatia: all measures largely agree) to 0.46–0.97 (France: betweenness disagrees substantially with degree-based measures, isolating Tchouaméni as a pure broker).

Two readings worth flagging in the report narrative:

- **Argentina's Terminal is De Paul, not Messi.** Messi is third for both in-degree and PageRank — second for in-degree among outfielders, but De Paul is consistently above him. This is a non-trivial finding: De Paul is the player to whom ball-circulation converges, and Messi is the player from whom the *final action* originates. The network distinguishes structural centrality from event-creating centrality.
- **Morocco's nominal Terminal is El Yamiq, a centre-back.** This is partly an artefact: under pressure, Morocco recycled possession via the back line. The "true" attacking terminal is Ziyech (#2 for PageRank and #1 for eigenvector). Worth treating in the report as a *characteristic distortion* of pressed teams: their pagerank Terminal is whoever absorbs the back-passing, not whoever finishes the attack.

The **top1/top2 betweenness ratio** ranges from 1.07 (Morocco: Amrabat barely ahead of Hakimi) to 3.20 (France: Tchouaméni more than three times the second-most-central player's betweenness). This is the structural-dominance score that will appear as the RQ3 predictor.

### RQ2 — Communities do not recover tactical lines, but they recover something else

The negative result on LINE is sharp:

| Team      | Algorithm | n_communities | Q     | NMI(LINE) | AMI(LINE) | F1_macro |
|-----------|-----------|--------------:|------:|----------:|----------:|---------:|
| Argentina | Louvain   | 4             | 0.097 | 0.153     | **−0.07** | 0.32     |
| France    | Louvain   | 3             | 0.128 | 0.095     | **−0.05** | 0.24     |
| Croatia   | Louvain   | 4             | 0.097 | 0.287     | +0.10     | 0.36     |
| Morocco   | Louvain   | 3             | 0.121 | 0.039     | **−0.12** | 0.20     |

Three teams out of four have AMI(LINE) ≤ 0 — communities are *worse than chance* at recovering the tactical line partition. Modularity Q across the board is 0.097–0.129, which on networks this dense (0.57–0.75) is also low in absolute terms.

Leiden produces partitions essentially identical to Louvain (same Q, same number of communities, NMI ≈ 1 between the two on all four teams). **Infomap collapses to a single community for all four teams**: with reciprocity > 0.8 and density > 0.5, the directed random walk does not find an information-theoretic gain from partitioning at all. This is itself a finding: the random-walk-on-flows framework is not the right lens for high-possession passing networks.

Inspection of the Louvain partitions reveals what the algorithm is finding instead. For Croatia: community A contains Lovren, Barišić, Livaković, Gvardiol — the LEFT defensive axis; community C contains Kramarić, Pašalić, Brozović, Modrić, Juranović, Vlašić — RIGHT-side and central; community D contains Oršić, Petković, Perišić, Kovačić, Sosa — LEFT-side attacking. For France: community A contains Tchouaméni, Mbappé, T. Hernández, Upamecano, Griezmann, M. Thuram, Rabiot — players who appeared together in starter lineups; community B contains Konaté, Camavinga, Disasi, Pavard, Mandanda, Coman, Veretout — substitutes and rotation players.

Tested against the three alternative ground truths:

| Team      | AMI(LINE) | AMI(SIDE) | AMI(ROLE_SIDE) | AMI(TENURE) |
|-----------|----------:|----------:|---------------:|------------:|
| Argentina | −0.07     | +0.01     | −0.02          | +0.06       |
| Croatia   | +0.10     | **+0.21** | **+0.20**      | +0.05       |
| France    | −0.05     | +0.19     | +0.09          | **+0.37**   |
| Morocco   | −0.12     | **+0.31** | +0.06          | +0.10       |

Four readings:

- **Morocco's communities are organised by side of pitch** (AMI 0.31): Hakimi–Ziyech form the right circuit, Mazraoui–Attiyat-Allah–Boufal the left. This is the most asymmetric of the four teams, and the strongest SIDE signal.
- **France's communities are organised by starter/substitute status** (AMI 0.37). Deschamps rotated heavily, and starters and substitutes form near-disjoint sub-networks because they were rarely on the pitch together.
- **Croatia recovers both LINE and SIDE weakly.** The team has the most coherent overall structure, but no single ground-truth dimension dominates.
- **Argentina is the structural outlier.** No ground truth scores positively at AMI > 0.06. The network is too centralised on Fernandez–Otamendi for community structure to be meaningful — it is a *star-like* topology, where peripheral assignments to communities are nearly arbitrary. This is also reflected in the modularity Q = 0.097, the lowest of the four.

The Argentina finding makes a *testable prediction* for RQ3: if Argentina's structure is centralised on a small number of hubs and lacks modular substructure to fall back on, then removing the top-betweenness pivot should produce damage that exceeds the random baseline by a substantial z-score. This is the prediction RQ3 tests in the next section.

### RQ3 — Fragility ranking and the pivot-dominance predictor

The fragility z-scores, averaged across the two damage metrics:

| Team      | z(Δpath) | z(Δefficiency) | **Fragility z** | top1/top2 ratio (from RQ1) |
|-----------|---------:|---------------:|----------------:|---------------------------:|
| France    | **4.65** | **3.11**       | **3.72**        | 3.20                       |
| Argentina | 1.77     | 3.48           | **2.62**        | 1.45                       |
| Morocco   | 1.33     | 1.95           | 1.64            | 1.07                       |
| Croatia   | 0.51     | 1.35           | **0.93**        | 1.12                       |

The **Pearson correlation between the RQ1 dominance score and the RQ3 fragility z-score is r = +0.89** (Spearman ρ = +0.80, n = 4). The two experiments — one structural, one dynamic — converge on the same ordering of fragility.

Three readings from the headline table:

- **France is the most fragile by a substantial margin.** Removing Tchouaméni produces a +22.6% increase in average path length, against a random-removal mean of +1.2% (z = 4.65, p ≈ 0). Tchouaméni is not just France's best player by centrality — his removal genuinely fractures the team's passing graph.
- **Argentina's fragility z = 2.62 is higher than its top1/top2 ratio would predict** under the linear fit. The team is the outlier above the regression line. The interpretation: Otamendi is the broker in the *spatial* sense (deep left-centre defender bridging defence and midfield), but the other top centralities (De Paul, Messi, Fernandez) work in the attacking third — they do not provide a redundant fall-back for the bridging role. Top1/top2 ratio under-counts the dominance of a pivot whose role is geometrically unique within the team.
- **Croatia is the most robust because the top three centralities — Modrić, Brozović, Kovačić — are near-interchangeable midfielders.** Removing Modrić causes only a +7.1% path-length increase, indistinguishable from random (z = 0.51, p = 0.18). Brozović and Kovačić absorb the broker role immediately.

The **attack progression curves** (cumulative removal of top-1, then top-2, then top-3 by re-computed betweenness) add a second-order observation: by step 3, all four teams' average path lengths have grown by 40–60% and efficiency has collapsed by 40–45%. The fragility ordering at step 1 — France >> Argentina > Morocco > Croatia — partially homogenises by step 3. The structural pivot matters; the structural top-3 matter much more, and roughly equally across teams.

A final tactical reading, optional in the report: the predictor correlation (r = 0.89) maps to the tournament outcomes in a suggestive way. France lost the final to Argentina on penalties after Argentina pressured Tchouaméni's side of the pitch heavily in extra time. Croatia, the most network-robust team, also lost both knockout matches it played against the eventual finalists — but on metrics other than passing-network fragility (they were outscored on chances, not out-structured on possession). The fragility experiment correctly identifies France as the team whose passing structure depended most precariously on a single player, which is consistent with — though not causally responsible for — the tournament outcome.

## 5. Visualization plan

Visual design is the group's responsibility — the dataviz module covers the *how*. This section sketches the *what*: the report will produce visualisations that carry the three findings, organised in two tiers.

**Tier 1 — Static deliverables (committed).** A 2×2 hero figure showing each team's passing network drawn on the pitch with node positions at empirical mean (x, y), node size proportional to weighted betweenness, node colour by tactical line, edge width by pass count above a threshold. A side-by-side comparison figure showing the same pitch portraits coloured (left) by tactical-line ground truth and (right) by Louvain community, demonstrating visually the RQ2 finding that the two partitions diverge. An AMI heatmap across the four teams and four ground truths showing where each algorithm finds structure. A 4×2 small-multiples grid of random-removal damage distributions with the targeted-removal line overlaid, per team and per metric. An attack-progression curve overlaying the four teams' damage trajectories across removal steps 0–3. A scatter plot of the RQ1 top1/top2 ratio against the RQ3 fragility z-score, showing the r = +0.89 alignment between the two experiments.

Prototype versions of all six static figures have been produced during the analysis phase and are available as `.png` deliverables. The final report version will rebuild them with a unified typographic style, considered colour palettes, and edge-case label placement.

**Tier 2 — Interactive deliverable (best-effort).** A single Streamlit application: side panel listing the four teams and their 23 collective matches; main panel rendering the chosen passing network on the pitch with hover-tooltips showing per-player centralities, line, minutes played, and community assignment. Toggle controls for aggregate-vs-single-match, completed-vs-attempted passes, edge-weight threshold, and centrality-based node sizing. The app is deliberately minimal; its purpose is exploration, not presentation. If time pressure forces a cut, the Tier 1 static deliverables alone constitute a self-contained report.

## 6. Possible extensions

- **Pass-difficulty weighting via expected-threat.** StatsBomb provides the data necessary to compute an expected-threat (xT) value for every pitch zone. Weighting each edge by the increase in xT the pass produces converts the count-weighted topology into a value-flow network, in which the pivot of the value-flow network is not necessarily the pivot of the count-weighted network.
- **Replacement-substitute simulation in RQ3.** Rather than simply removing the top-betweenness player, simulate his replacement by redistributing his passes proportionally to the other players in his tactical line, weighted by existing pass partnerships. This models the realistic scenario of an injury substitution.
- **Higher-order targeted attack.** The progression curve in §4 RQ3 stops at top-3. Extending to top-5 / top-7 to see when each network's giant component collapses gives the Albert–Jeong–Barabási curve in its full form.
- **Temporal evolution within the campaign.** A multi-layer network framework in the sense of Mucha et al. (2010); each match is one layer, intra-layer edges are within-match passes, inter-layer edges connect a player to himself across matches. The multi-layer centrality of a player tracks how his tactical role evolved across the tournament.

## 7. Methodological notes and common pitfalls

This section consolidates what was learned during the analysis — the decisions that have to be defended if questioned.

- **The 30-minute aggregate threshold.** A player who entered for ten minutes has a depressed centrality and inflates the node count without contributing meaningfully. The 30-minute threshold removes ~3–5 players per team. The choice is defended in §2.3; an alternative would be per-90-minute normalisation, which the project did not adopt because the centrality rankings are stable to threshold choice in the 20–60 minute range.
- **The `1/weight` distance convention.** For weighted closeness and betweenness, distance is `1/weight` (frequent passes = short paths). Pilot runs with the alternative convention produced rank inversions in three of the four teams.
- **Symmetrisation for Louvain/Leiden, directed for Infomap.** Louvain and Leiden are defined on undirected graphs; symmetrisation `w_sym(u,v) = w(u,v) + w(v,u)` is the standard treatment and the asymmetry is small given reciprocity > 0.81. Infomap supports directed graphs natively and is run on the original directed network. The fact that Infomap collapses to a single community on all four teams is therefore *not* a symmetrisation artefact.
- **Algorithms run unconstrained, then merged.** The resolution parameter is the default 1.0; the number of communities is *not* pre-set to 4. The unconstrained partition is then merged post-hoc into the four tactical lines by majority vote. The alternative (forcing 4 communities via the resolution parameter) was tested in pilot and produced lower modularity Q and identical NMI scores; the unconstrained-then-merged approach is theoretically cleaner and was retained.
- **lcc_size and λ₂ excluded from RQ3.** Both metrics were considered and discarded. lcc_size: 0 across 804 single-node removals (the networks are too dense to disconnect with one removal). λ₂: non-monotonic with damage on dense networks; removing the top hub *flattens* the spectrum and can produce negative damage scores. The two retained metrics — avg_path_length and efficiency — are theoretically sound for dense weighted directed networks.
- **n = 4 statistical caveat.** The Pearson r = 0.89 correlation between RQ1 dominance and RQ3 fragility is presented as a *consistency check* between two experiments on the same dataset, not as a discovery on a sample of teams. Generalising the predictor across all 32 nations is listed as a possible extension.
- **NMI = 1 was never the ceiling on RQ2.** Ground-truth tactical positions are themselves noisy: most semifinalist players held more than one position during the campaign. The expected ceiling on LINE-recovery NMI was therefore in the 0.55–0.80 range, but the observed values were 0.04–0.29. This was treated not as failure but as a finding that motivated the SIDE / TENURE / ROLE_SIDE re-evaluation.
- **The Argentina outlier in RQ3.** Argentina's z = 2.62 lies above the regression line through France, Morocco, Croatia. The interpretation in §4 RQ3 is that top1/top2 betweenness ratio is a one-dimensional measure that under-counts the spatial uniqueness of a pivot's role; Otamendi is structurally unique in the deep left-centre position, with no fall-back. A more sophisticated dominance measure would weight by spatial separation.
- **Library mixing.** `networkx` (centralities, Louvain, base graph), `igraph` (Leiden via leidenalg), `infomap` (Infomap), `scikit-learn` (NMI / AMI / F1), `scipy.stats` (Pearson, Spearman). A `player_id → row_index` mapping is asserted whenever a centrality is computed and re-attached to nodes.

## References

- **Peña, J. L., and Touchette, H. (2012).** *A network theory analysis of football strategies.* arXiv:1206.6904 — the canonical application of network science to international football; this project's methodological template.
- **Albert, R., Jeong, H., and Barabási, A.-L. (2000).** *Error and attack tolerance of complex networks.* Nature 406, 378–382 — the reference for RQ3's targeted-vs-random framework.
- **Blondel, V. D., Guillaume, J.-L., Lambiotte, R., and Lefebvre, E. (2008).** *Fast unfolding of communities in large networks.* J. Stat. Mech.
- **Traag, V. A., Waltman, L., and van Eck, N. J. (2019).** *From Louvain to Leiden: guaranteeing well-connected communities.* Scientific Reports.
- **Rosvall, M., and Bergstrom, C. T. (2008).** *Maps of random walks on complex networks reveal community structure.* PNAS 105, 1118–1123.
- **Buldú, J. M., Busquets, J., Echegoyen, I., and Seirul·lo, F. (2019).** *Defining a historic football team: Using network science to analyze Guardiola's F.C. Barcelona.* Scientific Reports 9, 13602.
- **Cintia, P., Rinzivillo, S., and Pappalardo, L. (2015).** *A network-based approach to evaluate the performance of football teams.* MLSA workshop, ECML-PKDD.
- **Newman, M. E. J. (2003).** *Mixing patterns in networks.* Phys. Rev. E 67, 026126.
- **Vinh, N. X., Epps, J., and Bailey, J. (2010).** *Information theoretic measures for clusterings comparison: variants, properties, normalization and correction for chance.* JMLR 11, 2837–2854 — the AMI reference.
- **StatsBomb Open Data Licence and repository.** `https://github.com/statsbomb/open-data`.
- **Course syllabus and lecture slides:** `netsci/ns_syllabus.md`, `netsci/pdfs/`.
