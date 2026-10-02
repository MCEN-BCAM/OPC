from __future__ import annotations

import numpy as np


def crossing_rm(rm: list[float], rin: list[float], target: float) -> tuple[float, bool]:
    """Linear inverse interpolation; reports whether the target was bracketed."""
    x = np.asarray(rm, dtype=float)
    y = np.asarray(rin, dtype=float)
    order = np.argsort(y)
    ys, xs = y[order], x[order]
    bracketed = bool(ys[0] <= target <= ys[-1])
    clipped = float(np.clip(target, ys[0], ys[-1]))
    return float(np.interp(clipped, ys, xs)), bracketed

