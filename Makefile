# Everything is rebuilt from pinned inputs. Raw and derived data live in data/ (gitignored).
PY = uv run python

.PHONY: all setup fetch parse derive data describe test clean

all: data describe test

setup:
	uv sync

fetch: setup            ## clone pinned Retrosheet + build pinned Chadwick tools
	$(PY) -m pce.fetch

parse: fetch            ## Retrosheet event files -> data/interim/*.parquet
	$(PY) -m pce.parse

derive: parse           ## derived tables -> data/processed/*.parquet
	$(PY) -m pce.derive

data: derive

describe:               ## every figure and table in reports/
	@for s in scripts/tab*.py scripts/fig*.py; do echo "== $$s"; $(PY) $$s || exit 1; done

test:
	uv run pytest -q

clean:
	rm -rf data/interim data/processed
