#!/usr/bin/env python3
"""Audit the corrected GM6 spatial-summation normalisation."""
from __future__ import annotations
import argparse
import csv
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', required=True, help='GM6 result directory')
    parser.add_argument('--tolerance', type=float, default=1e-10)
    args = parser.parse_args()

    root = Path(args.output_root)
    tables = sorted((root / 'cells').glob('*/*_synaptic_protocols.csv'))
    if not tables:
        raise SystemExit(f'No synaptic protocol tables found below {root / "cells"}')

    n_rows = 0
    failures: list[str] = []
    for table in tables:
        with table.open(newline='', encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                if row.get('protocol') != 'spatial':
                    continue
                n_rows += 1
                n = int(float(row['n_synapses']))
                observed = float(row['soma_epsp_mV'])
                predicted = float(row['linear_prediction_mV'])
                ratio = float(row['summation_ratio'])
                recomputed = observed / predicted
                if not math.isclose(ratio, recomputed, rel_tol=args.tolerance, abs_tol=args.tolerance):
                    failures.append(f'{table}: stored ratio {ratio} != {recomputed}')
                if n == 1 and not math.isclose(ratio, 1.0, rel_tol=args.tolerance, abs_tol=args.tolerance):
                    failures.append(f'{table}: N=1 ratio is {ratio}, expected 1')

    print(f'Inspected {n_rows} spatial rows from {len(tables)} cells')
    if failures:
        print(f'FAILED: {len(failures)} issue(s)')
        for msg in failures[:20]:
            print(' -', msg)
        return 1
    print('PASS: exact matched-site spatial normalisation verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
