"""Recognize exact rectangular brushes without expanding wedges to bounding boxes."""
from itertools import combinations, product
from math import sqrt
from .geometry import cross, dot, sub


def exact_box(points, tolerance=1e-4):
    """Return center, right-handed axes and full lengths, or None.

    All eight corners must match; orthogonality alone is not sufficient.
    Coordinates and tolerance use the caller's units.
    """
    vertices = []
    for p in points:
        if not any(dot(sub(p, q), sub(p, q)) <= tolerance**2 for q in vertices):
            vertices.append(p)
    if len(vertices) != 8:
        return None
    origin = vertices[0]
    for ends in combinations(vertices[1:], 3):
        edges = [sub(p, origin) for p in ends]
        lengths = [sqrt(dot(e, e)) for e in edges]
        if min(lengths) <= tolerance:
            continue
        axes = [[v / length for v in edge] for edge, length in zip(edges, lengths)]
        if any(abs(dot(axes[i], axes[j])) * max(lengths[i], lengths[j]) > tolerance
               for i, j in combinations(range(3), 2)):
            continue
        corners = [[origin[k] + sum(bit * edge[k] for bit, edge in zip(bits, edges))
                    for k in range(3)] for bits in product((0, 1), repeat=3)]
        if not all(any(dot(sub(c, p), sub(c, p)) <= tolerance**2 for p in vertices) for c in corners):
            continue
        center = [origin[k] + sum(e[k] for e in edges) / 2 for k in range(3)]
        # Negating a centered box axis changes no geometry.
        if dot(cross(axes[0], axes[1]), axes[2]) < 0:
            axes[2] = [-v for v in axes[2]]
        return dict(center=center, axes=axes, size=lengths)
    return None
