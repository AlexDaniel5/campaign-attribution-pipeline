# Convenience targets for the campaign attribution pipeline.
# All commands assume the virtualenv is active and run from the repo root.

export DBT_PROFILES_DIR := $(CURDIR)
export DUCKDB_PATH := $(CURDIR)/warehouse.duckdb

.PHONY: install warehouse build test pytest dbt-test all clean

install:
	python -m pip install -r requirements.txt

# Generate synthetic data and load the raw schema into DuckDB.
warehouse:
	python -m campaign_attribution.build_warehouse --db $(DUCKDB_PATH) --seed 42

# Run all dbt models (raw -> staging -> intermediate -> marts).
build: warehouse
	dbt build --exclude-resource-type test

# Run the dbt data-quality tests (schema + singular custom tests).
dbt-test:
	dbt test

# Run the Python unit tests.
pytest:
	python -m pytest

# Full pipeline: warehouse + dbt build + dbt tests + pytest.
all: warehouse
	dbt build
	python -m pytest

clean:
	rm -f $(DUCKDB_PATH) $(DUCKDB_PATH).wal
	rm -rf target dbt_packages logs .pytest_cache
