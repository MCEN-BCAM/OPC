#!/usr/bin/env python3
"""Collect validated products, regenerate calibrated figures, or execute notebooks."""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--mode',choices=['reference','figures','execute'],default='reference')
 p.add_argument('--output',type=Path,default=ROOT/'results/paper')
 p.add_argument('--timeout',type=int,default=1800)
 a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
 if a.mode=='reference':
  report_figures=ROOT/'docs/report/latest/figures'
  shutil.copytree(report_figures,a.output/'figures',dirs_exist_ok=True)
  shutil.copytree(ROOT/'analysis/reference_outputs/calibrated',
                  a.output/'source_data',dirs_exist_ok=True)
  print(f'Validated manuscript figures and calibrated source tables copied to {a.output}')
  return 0
 if a.mode=='figures':
  figure_dir=(a.output/'figures').resolve(); figure_dir.mkdir(parents=True,exist_ok=True)
  notebook=ROOT/'analysis/notebooks/Figure1_morphological_diversity_analysis.ipynb'
  executed=a.output/'Figure1_morphological_diversity_analysis_executed.ipynb'
  command=[sys.executable,'-m','jupyter','nbconvert','--to','notebook','--execute',
           str(notebook),'--output',executed.name,'--output-dir',str(a.output),
           f'--ExecutePreprocessor.timeout={a.timeout}']
  environment=os.environ.copy()
  environment['OPC_REPO_ROOT']=str(ROOT)
  environment['OPC_FIGURE1_WORK']=str((a.output/'figure1_work').resolve())
  environment['OPC_FIGURE1_OUTPUT']=str(figure_dir)
  print(' '.join(command)); result=subprocess.run(command,cwd=ROOT,env=environment)
  if result.returncode: return result.returncode
  command=[sys.executable,str(ROOT/'analysis/scripts/calibrated_figures.py'),
           '--figure','all','--output-dir',str(figure_dir)]
  print(' '.join(command))
  return subprocess.run(command,cwd=ROOT).returncode
 for nb in sorted((ROOT/'analysis/notebooks').glob('Figure[1-4]*_analysis.ipynb')):
  out=a.output/(nb.stem+'_executed.ipynb')
  cmd=[sys.executable,'-m','jupyter','nbconvert','--to','notebook','--execute',str(nb),'--output',out.name,'--output-dir',str(a.output),f'--ExecutePreprocessor.timeout={a.timeout}']
  print(' '.join(cmd)); r=subprocess.run(cmd,cwd=ROOT)
  if r.returncode: return r.returncode
 return 0
if __name__=='__main__': raise SystemExit(main())
