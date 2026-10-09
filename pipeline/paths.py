"""Where things live. REPO holds the code; a dataset directory holds one document: its PDF, the raw extractions,
data.json, snippets/ and the document-specific adapter/ code.
BUDGET_DATASET picks datasets/<id> (default kosovo-2026); BUDGET_DATASET_DIR points anywhere else, e.g. a copy."""
import os, json, pathlib
REPO=pathlib.Path(__file__).resolve().parent.parent
DATASET=os.environ.get('BUDGET_DATASET') or 'kosovo-2026'
DATASET_DIR=pathlib.Path(os.environ.get('BUDGET_DATASET_DIR') or REPO/'datasets'/DATASET).resolve()
ADAPTER_DIR=DATASET_DIR/'adapter'
PDF=DATASET_DIR/json.loads((DATASET_DIR/'dataset.json').read_text(encoding='utf-8'))['pdf']
