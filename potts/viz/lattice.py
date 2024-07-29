
import numpy as np
import matplotlib.pyplot as plt
import rustworkx as rx
from functools import reduce
from matplotlib.patches import Rectangle
from itertools import combinations, product


def shortestPath(L, assignment):
    # Construct a graph.
    G = rx.PyGraph(multigraph=False)

    # Add vertices and edges.
    G.add_nodes_from(range(L.skeleta[0]))
    G.add_edges_from_no_data([
        tuple(e) for i, e in enumerate(L.boundary[L.skeleta[0]:len(L.cells)-L.skeleta[2]])
        if assignment[i]
    ])

    # Look through all the cycles to see whether they pass through "antipodal"
    # points.
    w, h = L.corners

    antipodes = {
        0: [w-1, w*(h-1)],
        w-1: [0, (w*h)-1],
        w*(h-1): [0, (w*h)-1],
        (w*h)-1: [w-1, w*(h-1)]
    }

    bottom = set(range(1, w-1))
    left = set(range(w, w*(h-1), w))

    for k in bottom: antipodes.update({ k: [k+w*(h-1)] })
    for k in left: antipodes.update({ k: [k+w-1] })

    antipodes = { k: set(v) for k, v in antipodes.items() }
    boundary = set(antipodes.keys())
    interior = set(range(len(G.nodes())))-boundary

    B = rx.cycle_basis(G)
    B = [c for c in B if len(c) >= min(L.corners)]

    # This *kinda* gets the cycles, but not really.
    B = [
        c for c in B
        if set(c).issubset(boundary) or (any(f in boundary and set(c)&antipodes[f] for f in c) and len(set(c)&interior) >= min(L.corners))
    ]

    # Grab the cycle of shortest length (by default) and get edge tuples; then,
    # get the coordinates of the edges' endpoints, and return.
    if B:
        essential = list(sorted(B, key=lambda L: len(L)))[0]
        edges = list(zip([essential[-1]] + essential[:-1], essential))

        edges = list(zip([essential[-1]] + essential[:-1], essential))
        edges = [(L.cells[u].encoding[0], L.cells[v].encoding[0]) for u, v in edges]
        # X = sum([[ux, vx] for ((ux, _), (vx, __)) in edges], [])
        # Y = sum([[uy, vy] for ((_, uy), (__, vy)) in edges], [])

        return edges
    return []


def lattice2D(
        L, assignment,
        padding=0.1,
        vertexArgs=dict(s=40, color="k", zorder=10),
        edgeOccupiedColor="#3B444B",
        edgeOccupiedWidth=1.5,
        edgeVacantColor="#3B444B10",
        edgeVacantWidth=1,
        edgeArgs=dict(zorder=0),
        shortestEdgeArgs=dict(zorder=1, color="#E52B50"),
        squareArgs=dict(alpha=1/2, facecolor="#87A96B", edgecolor="none", zorder=0)
    ):
    """
    Plots the flat torus specified by `L`.

    Args:
        L (Lattice): `potts.structures.Lattice` object.
        assignment (iterable): An iterable of 0s and 1s specifying which edges
            to draw.
        padding (float): Space between the maximum coordinate pair on a given
            axis and the edge of the figure.
        vertexArgs (dict): Arguments passed to `plt.scatter()`.
        edgeOccupiedColor (str): Color of occupied edges.
        edgeOccupiedWidth (float): Width of occupied edges.
        edgeOccupiedColor (str): Color of vacant edges.
        edgeOccupiedWidth (float): Width of vacant edges.
        edgeArgs (dict): Arguments passed to `plt.plot()`.
        squareArgs (dict): Arguments passed to `patches.Rectangle()`.

    Returns:
        `(matplotlib.Figure, matplotlib.Axes)` subplots pair.
    """
    # Get the coordinates for the shortest path.
    shortestEdges = shortestPath(L, assignment)

    # Create subplots, turn axes off, set axis limits.
    fig, ax = plt.subplots()

    xlim, ylim = L.corners
    ax.set_xlim(-padding, xlim+padding)
    ax.set_ylim(-padding, ylim+padding)
    ax.set_axis_off()
    ax.set_aspect("equal")


    # Create a vertex map which specifies the possible embedded points each coordinate
    # can represent.
    vertexmap = {
        (x, y): list(
            product([x, xlim] if x == 0 else [x], [y, xlim] if y == 0 else [y])
        )
        for (x, y) in [c.encoding[0] for c in L.cells if len(c.encoding) < 2]
    }

    # Plot squares *first*. We need to check whether this is a torus (a periodic
    # cubical complex) as well, otherwise we end up plotting weird shit.
    last = np.cumsum(list(L.skeleta.values()))
    squares = [c.encoding for c in L.cells[last[1]:]]

    for square in squares:
        possibleVertices = reduce(lambda A,B: A+B, [vertexmap[v] for v in square])
        possibleSquares = list(combinations(possibleVertices, r=4))

        for possibleSquare in possibleSquares:
            pairs = combinations(possibleSquare, r=2)
            dist = sum(
                1 for ((px, py), (qx, qy)) in pairs
                if (px == qx and abs(py-qy) == 1) or (py == qy and abs(px-qx) == 1)
            )
            
            if dist == 4:
                coordinates = list(sorted(possibleSquare))
                anchor = coordinates[0]
                rect = Rectangle(anchor, width=1, height=1, **squareArgs)
                ax.add_patch(rect)

    # Plot edges next.
    edges = [c.encoding for c in L.cells[last[0]:last[1]]]
    nonzero = (assignment == 1).nonzero()[0]

    for j, ((ux, uy), (vx, vy)) in enumerate(edges):
        # No markers for edge ends.
        edgeArgs.update(dict(marker="none"))

        if j in nonzero:
            edgeArgs.update(dict(color=edgeOccupiedColor))
            edgeArgs.update(dict(linewidth=edgeOccupiedWidth))
        else:
            edgeArgs.update(dict(color=edgeVacantColor))
            edgeArgs.update(dict(linewidth=edgeVacantWidth))

        possibleVertices = list(product(vertexmap[(ux, uy)], vertexmap[(vx, vy)]))
        compatibleEdges = [
            ((ux, vx), (uy, vy)) for ((ux, uy), (vx, vy)) in possibleVertices
            if ((ux == vx and abs(uy-vy) == 1 and max(ux, vx) < L.corners[0])
                or (uy == vy and abs(ux-vx) == 1) and max(uy, vy) < L.corners[1])
        ]

        for x, y in compatibleEdges:
            ax.plot(x, y, **edgeArgs)

    # Do it again for the shortest path.
    for j, ((ux, uy), (vx, vy)) in enumerate(shortestEdges):
        # No markers for edge ends.
        edgeArgs.update(dict(marker="none"))

        if j in nonzero:
            edgeArgs.update(dict(color=edgeOccupiedColor))
            edgeArgs.update(dict(linewidth=edgeOccupiedWidth))
        else:
            edgeArgs.update(dict(color=edgeVacantColor))
            edgeArgs.update(dict(linewidth=edgeVacantWidth))

        possibleVertices = list(product(vertexmap[(ux, uy)], vertexmap[(vx, vy)]))
        compatibleEdges = [
            ((ux, vx), (uy, vy)) for ((ux, uy), (vx, vy)) in possibleVertices
            if ((ux == vx and abs(uy-vy) == 1 and max(ux, vx) < L.corners[0])
                or (uy == vy and abs(ux-vx) == 1) and max(uy, vy) < L.corners[1])
        ]

        for x, y in compatibleEdges:
            ax.plot(x, y, **shortestEdgeArgs)

    # Plot vertices *last*.
    vx, vy = zip(*[c.encoding[0] for c in L.cells[:L.skeleta[0]]])
    ax.scatter(vx, vy, **vertexArgs)

    return fig, ax
