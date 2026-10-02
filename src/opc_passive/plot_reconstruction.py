
from __future__ import annotations

from pathlib import Path
import json

import matplotlib.pyplot as plt


def plot_reconstruction(
    reconstruction_json: str | Path,
    output_path: str | Path,
) -> None:
    data = json.loads(Path(reconstruction_json).read_text(encoding="utf-8"))
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")

    for segment in data["segments"]:
        if segment["end"] is None:
            continue
        start = segment["start"]
        end = segment["end"]
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            [start[2], end[2]],
            linewidth=0.8,
        )

    centroid = data.get("soma_centroid")
    if centroid is not None:
        ax.scatter([centroid[0]], [centroid[1]], [centroid[2]], s=45)

    ax.set_xlabel("X (um)")
    ax.set_ylabel("Y (um)")
    ax.set_zlabel("Z (um)")
    ax.set_title(data["cell_id"])
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
