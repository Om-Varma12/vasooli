.PHONY: install test data demo clean

install:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

data:
	python scripts/generate_synthetic_data.py

demo: data
	python scripts/run_demo.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f data/failed_payments_batch.json data/audit_log.jsonl data/dead_letter.jsonl
