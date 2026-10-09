"""PDF -> raw/*.csv: runs the four parsers, each in its own process like `make extract` always did."""
import os as _os, sys as _sys; _sys.path.insert(0,_os.environ.get('BUDGET_ROOT') or _os.path.abspath(__file__+'/../../../..'))
from pipeline.paths import REPO, ADAPTER_DIR, DATASET_DIR
import subprocess
(DATASET_DIR/'raw').mkdir(exist_ok=True)
# BUDGET_ROOT lets an adapter that lives in a copied dataset directory find pipeline/
env=dict(_os.environ,BUDGET_ROOT=str(REPO))
for s in ('parse_tree.py','parse_41.py','parse_cap.py','parse_summary.py','parse_annex_names.py'):
    subprocess.run([_sys.executable,str(ADAPTER_DIR/s)],env=env,check=True)
