"""
netsci_utils.py — Shared utilities for the Network Science course tutorials.

Usage:
    from netsci_utils import *          # import everything
    from netsci_utils import draw_graph  # selective import

Students: feel free to read this file — it contains the helper functions
used throughout the tutorials so you don't have to copy-paste them.
"""

import os
import random
import pathlib
import inspect

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib import patheffects
import networkx as nx

# ---------------------------------------------------------------------------
# Constants — course-wide visual defaults
# ---------------------------------------------------------------------------

RANDOM_SEED       = 42
FIGURE_SIZE       = (10, 6)
FIGURE_SIZE_SMALL = (6, 4)
NODE_COLOR        = '#4C72B0'   # muted blue
EDGE_COLOR        = '#888888'
NODE_BORDER_COLOR = '#2F3E53'
NODE_SIZE         = 500
FONT_SIZE         = 10
EDGE_WIDTH        = 1.5
NODE_LINEWIDTH    = 1.2
CMAP              = 'Blues'     # for metric-based node colouring
FIGURE_DPI        = 100
SAVEFIG_DPI       = 300
METRIC_NODE_SIZE_MIN = 500
METRIC_NODE_SIZE_MAX = 2500
CATEGORY_PALETTE  = {
    'blue':   NODE_COLOR,
    'orange': '#DD8452',
    'green':  '#55A868',
    'red':    '#C44E52',
    'purple': '#8172B2',
    'brown':  '#937860',
}
KARATE_CLUB_COLORS = {
    'Mr. Hi': CATEGORY_PALETTE['blue'],
    'Officer': CATEGORY_PALETTE['orange'],
}
DUMBBELL_ROLE_COLORS = {
    'clique_core': CATEGORY_PALETTE['blue'],
    'connector': CATEGORY_PALETTE['orange'],
    'handle': CATEGORY_PALETTE['red'],
}
HIGHLIGHT_COLOR = CATEGORY_PALETTE['red']
TREND_COLOR = NODE_BORDER_COLOR
EMPTY_COLOR = '#F0F0F0'
SCHELLING_CMAP = mcolors.ListedColormap([
    EMPTY_COLOR,
    CATEGORY_PALETTE['blue'],
    CATEGORY_PALETTE['orange'],
])

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

def set_seeds(seed: int = RANDOM_SEED) -> None:
    """Set Python ``random`` and NumPy seeds for reproducible results."""
    random.seed(seed)
    np.random.seed(seed)


# ---------------------------------------------------------------------------
# Matplotlib setup
# ---------------------------------------------------------------------------

def setup_matplotlib() -> None:
    """Apply course-wide rcParams: figure size, font, DPI, grid, tight layout."""
    plt.rcParams.update({
        'figure.figsize':     FIGURE_SIZE,
        'figure.dpi':         FIGURE_DPI,
        'savefig.dpi':        SAVEFIG_DPI,
        'font.size':          FONT_SIZE,
        'axes.grid':          True,
        'grid.alpha':         0.3,
        'figure.autolayout':  True,
    })
    try:
        from matplotlib_inline.backend_inline import set_matplotlib_formats
        set_matplotlib_formats('retina')
    except Exception:
        pass


# Call at import time unless the user opts out via env variable.
if os.environ.get('NETSCI_SETUP', '1') != '0':
    setup_matplotlib()


# ---------------------------------------------------------------------------
# Shared categorical colour helpers
# ---------------------------------------------------------------------------

def colors_from_categories(categories, mapping, default=NODE_COLOR):
    """Return a colour list for *categories* using *mapping*."""
    return [mapping.get(category, default) for category in categories]


def colors_from_node_attribute(G, attribute, mapping, default=NODE_COLOR):
    """Map a node attribute to colours using *mapping* in node iteration order."""
    return colors_from_categories(
        [G.nodes[n].get(attribute) for n in G.nodes()],
        mapping,
        default=default,
    )


# ---------------------------------------------------------------------------
# Graph drawing
# ---------------------------------------------------------------------------

NODE_DRAW_KEYS = set(inspect.signature(nx.draw_networkx_nodes).parameters)
EDGE_DRAW_KEYS = set(inspect.signature(nx.draw_networkx_edges).parameters)
LABEL_DRAW_KEYS = set(inspect.signature(nx.draw_networkx_labels).parameters)


def _split_draw_kwargs(kwargs):
    """Split kwargs across node, edge, and label drawing helpers."""
    node_kwargs = {}
    edge_kwargs = {}
    label_kwargs = {}

    for key, value in kwargs.items():
        if key in NODE_DRAW_KEYS:
            node_kwargs[key] = value
        elif key in EDGE_DRAW_KEYS:
            edge_kwargs[key] = value
        elif key in LABEL_DRAW_KEYS:
            label_kwargs[key] = value

    return node_kwargs, edge_kwargs, label_kwargs


def _as_color_list(node_color, n_nodes, *, cmap=None, values=None, vmin=None, vmax=None):
    """Resolve node colours into a list of RGBA tuples."""
    if values is not None and cmap is not None:
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        return [cmap(norm(value)) for value in values]

    if isinstance(node_color, str):
        rgba = mcolors.to_rgba(node_color)
        return [rgba] * n_nodes

    try:
        colors = list(node_color)
    except TypeError:
        rgba = mcolors.to_rgba(node_color)
        return [rgba] * n_nodes

    if len(colors) != n_nodes:
        return [mcolors.to_rgba(NODE_COLOR)] * n_nodes

    try:
        return [mcolors.to_rgba(color) for color in colors]
    except ValueError:
        return [mcolors.to_rgba(NODE_COLOR)] * n_nodes


def _luminance(rgba):
    r, g, b = rgba[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _label_style_for_fill(rgba):
    """Choose readable text and outline colours for a node fill."""
    if _luminance(rgba) < 0.5:
        return 'white', NODE_BORDER_COLOR
    return 'black', 'white'


def _node_area_from_pixel_diameter(pixel_diameter, dpi):
    """Convert an approximate on-screen node diameter in pixels to points^2."""
    diameter_points = pixel_diameter * 72.0 / dpi
    radius_points = diameter_points / 2.0
    return np.pi * (radius_points ** 2)


def _draw_labels_with_contrast(
    G,
    pos,
    ax,
    node_colors,
    labels=None,
    font_size=FONT_SIZE,
    font_family='sans-serif',
    font_weight='normal',
    alpha=None,
    horizontalalignment='center',
    verticalalignment='center',
    clip_on=True,
):
    """Draw one label per node with contrast-aware text and outline."""
    label_map = labels if labels is not None else {node: node for node in G.nodes()}

    for node, rgba in zip(G.nodes(), node_colors):
        text_color, outline_color = _label_style_for_fill(rgba)
        x, y = pos[node]
        text = ax.text(
            x,
            y,
            str(label_map.get(node, node)),
            size=font_size,
            color=text_color,
            family=font_family,
            weight=font_weight,
            alpha=alpha,
            horizontalalignment=horizontalalignment,
            verticalalignment=verticalalignment,
            clip_on=clip_on,
            zorder=5,
        )
        text.set_path_effects([
            patheffects.Stroke(linewidth=2.2, foreground=outline_color),
            patheffects.Normal(),
        ])

def draw_graph(
    G,
    pos=None,
    ax=None,
    node_color=NODE_COLOR,
    node_size=NODE_SIZE,
    edge_color=EDGE_COLOR,
    font_size=FONT_SIZE,
    with_labels=True,
    seed=RANDOM_SEED,
    width=EDGE_WIDTH,
    linewidths=NODE_LINEWIDTH,
    edgecolors=NODE_BORDER_COLOR,
    **kwargs,
):
    """Draw *G* with course-standard visual defaults.

    Parameters
    ----------
    G : nx.Graph
        The graph to draw.
    pos : dict, optional
        Node positions.  If *None*, ``spring_layout`` is used.
    ax : matplotlib.axes.Axes, optional
        Target axes.  If *None*, uses the current axes.
    seed : int
        Seed for ``spring_layout`` when *pos* is *None*.
    **kwargs
        Additional keyword arguments forwarded to ``nx.draw``.
    """
    if pos is None:
        pos = nx.spring_layout(G, seed=seed)
    target_ax = ax if ax is not None else plt.gca()
    node_kwargs, edge_kwargs, label_kwargs = _split_draw_kwargs(kwargs)
    node_colors = _as_color_list(node_color, G.number_of_nodes())

    nx.draw_networkx_nodes(
        G,
        pos=pos,
        ax=target_ax,
        node_color=node_color,
        node_size=node_size,
        linewidths=linewidths,
        edgecolors=edgecolors,
        **node_kwargs,
    )
    nx.draw_networkx_edges(
        G,
        pos=pos,
        ax=target_ax,
        edge_color=edge_color,
        width=width,
        node_size=node_size,
        **edge_kwargs,
    )
    if with_labels:
        _draw_labels_with_contrast(
            G,
            pos,
            target_ax,
            node_colors,
            labels=label_kwargs.pop('labels', None),
            font_size=label_kwargs.pop('font_size', font_size),
            font_family=label_kwargs.pop('font_family', 'sans-serif'),
            font_weight=label_kwargs.pop('font_weight', 'normal'),
            alpha=label_kwargs.pop('alpha', None),
            horizontalalignment=label_kwargs.pop('horizontalalignment', 'center'),
            verticalalignment=label_kwargs.pop('verticalalignment', 'center'),
            clip_on=label_kwargs.pop('clip_on', True),
        )
    target_ax.set_axis_off()
    return pos


def draw_graph_metric(
    G,
    metric_dict,
    pos=None,
    ax=None,
    cmap=CMAP,
    edge_color=EDGE_COLOR,
    font_size=FONT_SIZE,
    with_labels=True,
    min_node_size=METRIC_NODE_SIZE_MIN,
    max_node_size=METRIC_NODE_SIZE_MAX,
    min_node_size_px=None,
    max_node_size_px=None,
    seed=RANDOM_SEED,
    colorbar=True,
    width=EDGE_WIDTH,
    linewidths=NODE_LINEWIDTH,
    edgecolors=NODE_BORDER_COLOR,
    **kwargs,
):
    """Draw *G* with nodes sized and coloured by *metric_dict*.

    Parameters
    ----------
    G : nx.Graph
    metric_dict : dict
        Mapping ``{node: value}`` used for both colour and size.
    pos : dict, optional
    ax : matplotlib.axes.Axes, optional
    cmap : str
        Matplotlib colourmap name.
    min_node_size, max_node_size : float
        Node sizes are linearly scaled to this range.
    min_node_size_px, max_node_size_px : float, optional
        Approximate node diameters in screen pixels. If both are provided,
        they override ``min_node_size`` and ``max_node_size``.
    colorbar : bool
        Whether to add a colour bar to *ax* (requires *ax* to be provided
        or the current axes).
    **kwargs
        Forwarded to ``nx.draw``.

    Returns
    -------
    pos : dict
    """
    if pos is None:
        pos = nx.spring_layout(G, seed=seed)

    node_kwargs, edge_kwargs, label_kwargs = _split_draw_kwargs(kwargs)
    values = np.array([metric_dict.get(n, 0) for n in G.nodes()])
    v_min, v_max = values.min(), values.max()
    target_ax = ax if ax is not None else plt.gca()

    if (min_node_size_px is None) != (max_node_size_px is None):
        raise ValueError(
            'Provide both min_node_size_px and max_node_size_px, or neither.'
        )
    if min_node_size_px is not None and max_node_size_px is not None:
        dpi = target_ax.get_figure().dpi
        min_node_size = _node_area_from_pixel_diameter(min_node_size_px, dpi)
        max_node_size = _node_area_from_pixel_diameter(max_node_size_px, dpi)

    if v_max > v_min:
        sizes = min_node_size + (max_node_size - min_node_size) * (
            (values - v_min) / (v_max - v_min)
        )
    else:
        sizes = np.full(len(values), (min_node_size + max_node_size) / 2)

    cmap_obj = plt.get_cmap(cmap)
    nx.draw_networkx_nodes(
        G,
        pos=pos,
        ax=target_ax,
        node_color=values,
        node_size=sizes,
        linewidths=linewidths,
        edgecolors=edgecolors,
        cmap=cmap_obj,
        vmin=v_min,
        vmax=v_max,
        **node_kwargs,
    )
    nx.draw_networkx_edges(
        G,
        pos=pos,
        ax=target_ax,
        edge_color=edge_color,
        width=width,
        node_size=sizes,
        **edge_kwargs,
    )
    if with_labels:
        _draw_labels_with_contrast(
            G,
            pos,
            target_ax,
            _as_color_list(
                None,
                G.number_of_nodes(),
                cmap=cmap_obj,
                values=values,
                vmin=v_min,
                vmax=v_max,
            ),
            labels=label_kwargs.pop('labels', None),
            font_size=label_kwargs.pop('font_size', font_size),
            font_family=label_kwargs.pop('font_family', 'sans-serif'),
            font_weight=label_kwargs.pop('font_weight', 'normal'),
            alpha=label_kwargs.pop('alpha', None),
            horizontalalignment=label_kwargs.pop('horizontalalignment', 'center'),
            verticalalignment=label_kwargs.pop('verticalalignment', 'center'),
            clip_on=label_kwargs.pop('clip_on', True),
        )
    if colorbar:
        sm = plt.cm.ScalarMappable(
            cmap=cmap_obj,
            norm=plt.Normalize(vmin=v_min, vmax=v_max),
        )
        sm.set_array([])
        fig = target_ax.get_figure() if target_ax else plt.gcf()
        fig.colorbar(sm, ax=target_ax)
    target_ax.set_axis_off()
    return pos


def plot_graph(
    G,
    title=None,
    pos=None,
    figure_size=FIGURE_SIZE,
    **kwargs,
):
    """Create a new figure and draw *G* with course-standard defaults.

    This is the high-level convenience wrapper. Use it in notebooks when you
    want a coherent standalone plot without managing axes manually.
    """
    plt.figure(figsize=figure_size)
    draw_graph(G, pos=pos, **kwargs)
    if title is not None:
        plt.title(title)
    plt.show()


def plot_metric(
    G,
    metric_dict,
    title=None,
    pos=None,
    figure_size=FIGURE_SIZE,
    colorbar=False,
    min_node_size=METRIC_NODE_SIZE_MIN,
    max_node_size=METRIC_NODE_SIZE_MAX,
    min_node_size_px=None,
    max_node_size_px=None,
    **kwargs,
):
    """Create a new figure and draw *G* sized/coloured by *metric_dict*.

    This is the high-level counterpart to ``plot_graph``. Use it when the
    structure stays the same but node size/colour should encode a metric.

    ``min_node_size`` / ``max_node_size`` use Matplotlib's native area units
    (points^2). For a more intuitive control, pass ``min_node_size_px`` and
    ``max_node_size_px`` to set approximate node diameters in screen pixels.
    """
    plt.figure(figsize=figure_size)
    draw_graph_metric(
        G,
        metric_dict,
        pos=pos,
        colorbar=colorbar,
        min_node_size=min_node_size,
        max_node_size=max_node_size,
        min_node_size_px=min_node_size_px,
        max_node_size_px=max_node_size_px,
        **kwargs,
    )
    if title is not None:
        plt.title(title)
    plt.show()


# ---------------------------------------------------------------------------
# Non-graph plotting helpers
# ---------------------------------------------------------------------------

def style_axis(
    ax,
    *,
    title=None,
    xlabel=None,
    ylabel=None,
    xscale=None,
    yscale=None,
    legend=False,
    grid=True,
):
    """Apply a coherent course style to a standard Matplotlib axis."""
    if title is not None:
        ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if xscale is not None:
        ax.set_xscale(xscale)
    if yscale is not None:
        ax.set_yscale(yscale)
    if grid:
        ax.grid(True, alpha=0.3)
    else:
        ax.grid(False)
    if legend:
        ax.legend(frameon=False)
    return ax


def plot_heatmap(
    matrix,
    *,
    labels=None,
    x_labels=None,
    y_labels=None,
    title=None,
    figure_size=FIGURE_SIZE_SMALL,
    cmap=CMAP,
    vmin=None,
    vmax=None,
    annotate=True,
    fmt='{:.2f}',
    colorbar=True,
):
    """Plot a course-style heatmap for a small matrix."""
    matrix = np.asarray(matrix)
    fig, ax = plt.subplots(figsize=figure_size)
    im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax)

    if labels is not None and x_labels is None and y_labels is None:
        x_labels = labels
        y_labels = labels

    if x_labels is not None:
        xticks = np.arange(len(x_labels))
        ax.set_xticks(xticks)
        ax.set_xticklabels(x_labels)

    if y_labels is not None:
        yticks = np.arange(len(y_labels))
        ax.set_yticks(yticks)
        ax.set_yticklabels(y_labels)

    if annotate:
        low = matrix.min() if vmin is None else vmin
        high = matrix.max() if vmax is None else vmax
        threshold = (low + high) / 2.0 if high > low else high
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = matrix[i, j]
                text_color = 'white' if value >= threshold else 'black'
                ax.text(
                    j,
                    i,
                    fmt.format(value),
                    ha='center',
                    va='center',
                    color=text_color,
                )

    if colorbar:
        fig.colorbar(im, ax=ax)
    style_axis(ax, title=title, grid=False)
    return fig, ax


# ---------------------------------------------------------------------------
# Degree distributions / CCDF
# ---------------------------------------------------------------------------

def compute_pmf(sequence):
    """Compute support, counts, and PMF for a discrete sample."""
    values = np.asarray(sequence)
    unique, counts = np.unique(values, return_counts=True)
    pmf = counts / counts.sum()
    return unique, counts, pmf


def compute_cdf(sequence):
    """Compute the empirical CDF for a discrete sample."""
    unique, counts, _ = compute_pmf(sequence)
    cdf = np.cumsum(counts) / counts.sum()
    return unique, cdf


def compute_ccdf(sequence):
    """Compute the Complementary Cumulative Distribution Function (CCDF).

    Parameters
    ----------
    sequence : array-like
        Sequence of values (e.g. node degrees).

    Returns
    -------
    x : np.ndarray
        Sorted unique values.
    y : np.ndarray
        P(X >= x) for each value in *x*.
    """
    values = np.asarray(sequence)
    unique, counts = np.unique(values, return_counts=True)
    probs = counts / counts.sum()
    # P(X >= x) = 1 - CDF(x-1) = reverse cumsum shifted by one
    ccdf = np.cumsum(probs[::-1])[::-1]
    return unique, ccdf


def empirical_continuous_cdf(sequence):
    """Compute the empirical CDF from a continuous sample."""
    values = np.sort(np.asarray(sequence, dtype=float))
    cdf = np.arange(1, len(values) + 1) / len(values)
    return values, cdf


def empirical_continuous_ccdf(sequence):
    """Compute the empirical CCDF P(X >= x) from a sample."""
    values = np.sort(np.asarray(sequence, dtype=float))
    ccdf = np.arange(len(values), 0, -1) / len(values)
    return values, ccdf


def heterogeneity_kappa(G):
    """Compute kappa = <k^2> / <k> for an undirected graph."""
    degrees = np.asarray([degree for _, degree in G.degree()], dtype=float)
    mean_degree = degrees.mean()
    if mean_degree == 0:
        return np.nan
    return np.mean(degrees ** 2) / mean_degree


def largest_component_fraction(G):
    """Return the fraction of nodes in the largest connected component."""
    if G.number_of_nodes() == 0:
        return 0.0
    largest = max(nx.connected_components(G), key=len)
    return len(largest) / G.number_of_nodes()


def largest_component_subgraph(G):
    """Return the largest connected component of *G* as a copied subgraph."""
    if G.number_of_nodes() == 0:
        return G.copy()
    largest = max(nx.connected_components(G), key=len)
    return G.subgraph(largest).copy()


def model_summary_row(G, name):
    """Return a compact summary row for a graph model comparison."""
    degrees = np.asarray([degree for _, degree in G.degree()], dtype=float)
    row = {
        'network': name,
        'n': G.number_of_nodes(),
        'm': G.number_of_edges(),
        '<k>': degrees.mean() if len(degrees) else 0.0,
        'max k': degrees.max() if len(degrees) else 0.0,
        'kappa': heterogeneity_kappa(G),
        'avg clustering': nx.average_clustering(G) if G.number_of_nodes() else np.nan,
        'largest component fraction': largest_component_fraction(G),
    }
    largest = largest_component_subgraph(G)
    if largest.number_of_nodes() > 1:
        row['avg path length in LCC'] = nx.average_shortest_path_length(largest)
    else:
        row['avg path length in LCC'] = np.nan
    return row


def naive_ccdf_slope(sequence, kmin):
    """Fit a simple log-log slope to the CCDF tail as a teaching diagnostic."""
    x, y = compute_ccdf(sequence)
    mask = (x >= kmin) & (y > 0)
    if mask.sum() < 3:
        return np.nan
    slope, _ = np.polyfit(np.log10(x[mask]), np.log10(y[mask]), 1)
    return slope


def plot_ccdf(
    sequence,
    ax=None,
    label=None,
    color=None,
    marker='o',
    markersize=3,
    linestyle='None',
    loglog=True,
    xlabel='Value',
    ylabel='P(X ≥ x)',
    **kwargs,
):
    """Plot the CCDF of *sequence* on log-log axes.

    Parameters
    ----------
    sequence : array-like
    ax : matplotlib.axes.Axes, optional
        If *None*, uses the current axes.
    label : str, optional
        Legend label.
    loglog : bool
        Whether to use log-log scale (default *True*).
    **kwargs
        Forwarded to ``ax.plot``.

    Returns
    -------
    ax : matplotlib.axes.Axes
    """
    if ax is None:
        ax = plt.gca()
    x, y = compute_ccdf(sequence)
    ax.plot(x, y, marker=marker, markersize=markersize,
            linestyle=linestyle, label=label, color=color, **kwargs)
    if loglog:
        ax.set_xscale('log')
        ax.set_yscale('log')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which='both', ls='--', alpha=0.3)
    return ax


def rank_size(sequence):
    """Return ranks and values sorted from largest to smallest."""
    values = np.sort(np.asarray(sequence, dtype=float))[::-1]
    ranks = np.arange(1, len(values) + 1)
    return ranks, values


def normalized_shares(sequence):
    """Return non-negative values normalized to sum to 1."""
    values = np.asarray(sequence, dtype=float)
    values = np.clip(values, a_min=0.0, a_max=None)
    total = values.sum()
    if total == 0:
        return np.zeros_like(values, dtype=float)
    return values / total


def cumulative_share(sequence):
    """Return rank and cumulative share after sorting from largest to smallest."""
    _, values = rank_size(sequence)
    shares = normalized_shares(values)
    return np.arange(1, len(values) + 1), np.cumsum(shares)


def head_tail_share(sequence, head_fraction=0.1):
    """Return the head and tail shares after sorting values descending."""
    _, values = rank_size(sequence)
    shares = normalized_shares(values)
    cutoff = max(1, int(np.ceil(head_fraction * len(values))))
    head = shares[:cutoff].sum()
    tail = shares[cutoff:].sum()
    return {
        'head_fraction': head_fraction,
        'head_items': cutoff,
        'head_share': head,
        'tail_share': tail,
    }


def herfindahl_index(sequence):
    """Return the Herfindahl-Hirschman concentration index."""
    shares = normalized_shares(sequence)
    return np.sum(shares ** 2)


def gini_coefficient(sequence):
    """Return the Gini coefficient of a non-negative sample."""
    values = np.sort(np.asarray(sequence, dtype=float))
    values = np.clip(values, a_min=0.0, a_max=None)
    if len(values) == 0 or values.sum() == 0:
        return 0.0
    cumulative = np.cumsum(values)
    n = len(values)
    return (n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n


def plot_rank_size(
    sequence,
    ax=None,
    label=None,
    color=None,
    marker='o',
    markersize=3,
    linewidth=1.8,
    loglog=True,
    xlabel='Rank',
    ylabel='Value',
    **kwargs,
):
    """Plot a rank-size curve with course-style defaults."""
    if ax is None:
        ax = plt.gca()
    ranks, values = rank_size(sequence)
    ax.plot(
        ranks,
        values,
        marker=marker,
        markersize=markersize,
        linewidth=linewidth,
        color=color,
        label=label,
        **kwargs,
    )
    if loglog:
        ax.set_xscale('log')
        ax.set_yscale('log')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which='both', ls='--', alpha=0.3)
    return ax


def plot_cumulative_share(
    sequence,
    ax=None,
    label=None,
    color=None,
    linewidth=2.0,
    xlabel='Top-ranked items kept',
    ylabel='Cumulative share',
    **kwargs,
):
    """Plot the cumulative share after sorting values descending."""
    if ax is None:
        ax = plt.gca()
    ranks, shares = cumulative_share(sequence)
    ax.plot(ranks, shares, linewidth=linewidth, color=color, label=label, **kwargs)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.3)
    return ax


# ---------------------------------------------------------------------------
# Network statistics
# ---------------------------------------------------------------------------

def network_stats(G):
    """Return a dict of common network statistics for *G*.

    Keys: ``n_nodes``, ``n_edges``, ``density``, ``avg_degree``,
    ``avg_clustering``, ``diameter`` (or ``None`` if disconnected).
    """
    n = G.number_of_nodes()
    L = G.number_of_edges()
    density = nx.density(G)
    avg_deg = (2 * L / n) if n > 0 else 0.0
    avg_clust = nx.average_clustering(G)
    try:
        diameter = nx.diameter(G)
    except nx.NetworkXError:
        diameter = None
    return {
        'n_nodes':       n,
        'n_edges':       L,
        'density':       density,
        'avg_degree':    avg_deg,
        'avg_clustering': avg_clust,
        'diameter':      diameter,
    }


def print_network_stats(G) -> None:
    """Print a short summary of key network statistics for *G*."""
    stats = network_stats(G)
    print(f"Nodes          : {stats['n_nodes']}")
    print(f"Edges          : {stats['n_edges']}")
    print(f"Density        : {stats['density']:.6f}")
    print(f"Average degree : {stats['avg_degree']:.4f}")
    print(f"Avg clustering : {stats['avg_clustering']:.4f}")
    if stats['diameter'] is not None:
        print(f"Diameter       : {stats['diameter']}")
    else:
        print("Diameter       : N/A (graph is disconnected)")


def positions_from_node_attributes(G, x_attr='longitude', y_attr='latitude'):
    """Build a position dictionary from numeric node attributes."""
    pos = {}
    for node, data in G.nodes(data=True):
        if x_attr in data and y_attr in data:
            pos[node] = (float(data[x_attr]), float(data[y_attr]))
    return pos


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

_HERE = pathlib.Path(__file__).parent   # tutorials/src/
_DATASETS = _HERE / '..' / 'datasets'   # tutorials/datasets/


def load_openflights_usa() -> nx.Graph:
    """Load the US OpenFlights airport network.

    Returns
    -------
    nx.Graph
        Nodes are IATA codes with ``name``, ``latitude``, ``longitude``
        attributes.  Edges represent direct flight routes.
    """
    path = (_DATASETS / 'openflights' / 'openflights_usa.graphml.gz').resolve()
    return nx.read_graphml(str(path))


def load_openflights_world() -> nx.Graph:
    """Load the world OpenFlights airport network.

    Returns
    -------
    nx.Graph
    """
    path = (_DATASETS / 'openflights' / 'openflights_world.graphml.gz').resolve()
    return nx.read_graphml(str(path))


def load_friends() -> nx.Graph:
    """Load the ``friends.adjlist`` social graph.

    Returns
    -------
    nx.Graph
    """
    path = (_DATASETS / 'friends.adjlist').resolve()
    return nx.read_adjlist(str(path))
