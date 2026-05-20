import pickle
import matplotlib.pyplot as plt
import networkx as nx

# Carica il file
with open("Argentina.gpickle", "rb") as f:
    G = pickle.load(f)

print(f"Grafo caricato correttamente: {G.number_of_nodes()} giocatori trovati.")

# Estraiamo le posizioni x, y memorizzate nei nodi per il disegno
pos = {}
for node, data in G.nodes(data=True):
    if "x" in data and "y" in data:
        # Usiamo le coordinate x e y del file come posizioni nello spazio
        pos[node] = (data["x"], data["y"])
    else:
        # Fallback se qualche nodo non ha le coordinate
        pos = nx.spring_layout(G)

# Disegniamo il grafo
plt.figure(figsize=(12, 8))
nx.draw_networkx_nodes(G, pos, node_size=300, node_color="skyblue")
nx.draw_networkx_edges(G, pos, alpha=0.3, edge_color="gray")
nx.draw_networkx_labels(G, pos, font_size=8, font_family="sans-serif")

plt.title("Rete dei passaggi - Argentina")
plt.axis("off")  # Nasconde gli assi cartesiani
plt.show()
