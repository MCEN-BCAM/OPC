from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd


def _table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "<p>No rows available.</p>"
    return frame.head(max_rows).to_html(index=False, border=0, classes="dataframe", float_format=lambda x: f"{x:.4g}")


def write_cell_report(path: Path, cell_id: str, summary: dict, qc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "".join(f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in summary.items())
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>{escape(cell_id)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1000px;margin:2rem auto;line-height:1.45}}img{{max-width:100%}}th{{text-align:left;padding:.35rem}}td{{padding:.35rem}}table{{border-collapse:collapse}}tr:nth-child(even){{background:#f3f3f3}}.accepted{{color:#176b31}}.excluded{{color:#a32020}}</style></head><body>
<h1>{escape(cell_id)} — passive electrophysiology report</h1>
<p>QC status: <strong class='{escape(qc['qc_status'])}'>{escape(qc['qc_status'])}</strong></p>
<p>Errors: {escape(qc.get('errors','')) or 'none'}<br>Warnings: {escape(qc.get('warnings','')) or 'none'}</p>
<h2>Cell-level metrics</h2><table>{rows}</table>
<h2>Standard current-step trace</h2><img src='../figures/{escape(cell_id)}_soma_trace.png'>
<h2>Attenuation profile</h2><img src='../figures/{escape(cell_id)}_attenuation.png'>
</body></html>"""
    path.write_text(html, encoding="utf-8")


def write_index(path: Path, qc: pd.DataFrame, descriptive: pd.DataFrame, omnibus: pd.DataFrame, pairwise: pd.DataFrame, n_input: int, n_accepted: int) -> None:
    links = "".join(f"<li><a href='cells/{escape(str(row.cell_id))}.html'>{escape(str(row.cell_id))}</a> — {escape(str(row.qc_status))}</li>" for row in qc.itertuples())
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>OPC passive electrophysiology atlas</title>
<style>body{{font-family:Arial,sans-serif;max-width:1200px;margin:2rem auto;line-height:1.45}}img{{max-width:100%}}table{{border-collapse:collapse;width:100%;font-size:.88rem}}th,td{{padding:.35rem;border-bottom:1px solid #ddd;text-align:left}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}</style></head><body>
<h1>OPC passive electrophysiology atlas</h1>
<p>Step-4 cells inspected: <strong>{n_input}</strong>. QC-accepted cells: <strong>{n_accepted}</strong>.</p>
<h2>Population figures</h2><div class='grid'>
<img src='figures/input_resistance.png'><img src='figures/tau.png'>
<img src='figures/attenuation_by_distance.png'><img src='figures/cable_length_vs_rin.png'>
</div>
<h2>Descriptive statistics</h2>{_table(descriptive)}
<h2>Omnibus comparisons</h2>{_table(omnibus)}
<h2>Pairwise comparisons</h2>{_table(pairwise)}
<h2>Per-cell reports</h2><ul>{links}</ul>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
