from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Any

def read_json(path: str|Path)->Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path: str|Path, value: Any)->None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

def write_csv(path: str|Path, rows: list[dict[str,Any]])->None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    if not rows: p.write_text('', encoding='utf-8'); return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with p.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
