# See AGENTS.md → Commands.
PY ?= uv run python

.PHONY: setup check test update update-auto harvest build dev

setup:
	uv sync
	cd site && npm install

check:
	$(PY) scripts/validate_registry.py
	$(PY) scripts/check_name.py
	$(PY) -m pytest -q

test:
	$(PY) -m pytest -q

# make update SOURCE=<series id | module path | provider name>
update:
	@test -n "$(SOURCE)" || (echo "usage: make update SOURCE=<series-id-or-source>" && exit 2)
	$(PY) -m pipelines.run $(SOURCE)

update-auto:
	$(PY) -m pipelines.run --fetch auto

harvest: update-auto

build:
	$(PY) -m pipelines.build.site_data
	cd site && npx astro build

dev:
	$(PY) -m pipelines.build.site_data
	cd site && npx astro dev
