# One dataset at a time: DATASET=kosovo-2026 by default (datasets/<DATASET>/). `make help` lists the targets.
# Pipeline targets need Python (requirements.txt) and poppler for `verify`; viewer targets need Node 22 (npm ci).
DATASET ?= kosovo-2026
PY ?= $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
ADAPTER = datasets/$(DATASET)/adapter
export BUDGET_DATASET = $(DATASET)

.PHONY: all extract data snippets verify site single test dev serve clean help

all: extract data snippets test verify            ## full rebuild from the PDF, then every check and test

extract:                                          ## PDF -> datasets/$(DATASET)/raw/*.csv (pdfplumber, word positions)
	$(PY) $(ADAPTER)/extract.py

data:                                             ## raw/ -> datasets/$(DATASET)/data.json (nodes, flows, refs, checks, findings, tours)
	$(PY) $(ADAPTER)/normalize.py

snippets:                                         ## highlighted page crops for key references -> datasets/$(DATASET)/snippets/<rid>.jpg
	$(PY) $(ADAPTER)/snippets.py

verify:                                           ## re-read values from the PDF with a second extractor (needs poppler pdftotext)
	$(PY) $(ADAPTER)/spotcheck.py

site:                                             ## -> dist/ (GitHub Pages build: data fetched in chunks)
	npm run build

single:                                           ## -> dist-single/index.html (one file, everything inline; works offline)
	npm run build:single

test:                                             ## typecheck, validate the dataset, build both targets, browser tests
	npm run check

dev:                                              ## live-reloading viewer on the dataset
	npm run dev

serve: site                                       ## preview dist/ at http://localhost:4173
	npm run preview

clean:
	rm -rf dist dist-single tests/shots test-results datasets/$(DATASET)/spotcheck.json

help:
	@grep -E '^[a-z]+:.*## ' Makefile | sed -E 's/:[^#]*## /\t/'
