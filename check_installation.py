#!/usr/bin/env python3
from __future__ import annotations
import importlib, platform, sys
REQUIRED=['numpy','pandas','scipy','matplotlib','openpyxl','xlrd','networkx','yaml']
OPTIONAL=['neuron','jupyter','nbconvert']
def check(name):
    try:
        m=importlib.import_module(name); return True,getattr(m,'__version__','available')
    except Exception as e: return False,str(e)
def main():
    print(f'Python {sys.version.split()[0]} | {platform.platform()}')
    failed=[]
    for n in REQUIRED:
        ok,msg=check(n); print(('✓' if ok else '✗'),f'{n}: {msg}'); failed += [] if ok else [n]
    for n in OPTIONAL:
        ok,msg=check(n); print(('✓' if ok else '–'),f'{n}: {msg}')
    if failed:
        print('\nInstallation is incomplete. Missing required packages: '+', '.join(failed)); return 1
    print('\nCore installation is ready. NEURON is required for GM4, GM6, and GM7.')
    return 0
if __name__=='__main__': raise SystemExit(main())
