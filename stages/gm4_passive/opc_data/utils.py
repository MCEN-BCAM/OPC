
from __future__ import annotations

import math
import re
from typing import Any, Iterable


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def normalize_header(value: Any, index: int) -> str:
    text = clean_text(value)
    if not text:
        return f"unnamed_{index}"
    text = text.replace("µ", "u")
    text = text.replace("²", "2").replace("³", "3")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()
    return text or f"unnamed_{index}"


def unique_headers(values: Iterable[Any]) -> list[str]:
    used: dict[str, int] = {}
    result: list[str] = []
    for index, value in enumerate(values):
        base = normalize_header(value, index)
        count = used.get(base, 0)
        used[base] = count + 1
        result.append(base if count == 0 else f"{base}_{count + 1}")
    return result


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (str, list, dict)):
        return value
    return str(value)


def first_number(record: dict[str, Any], candidates: Iterable[str]) -> float | None:
    for key in candidates:
        if key in record:
            value = record[key]
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None
