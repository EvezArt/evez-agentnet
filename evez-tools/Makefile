.PHONY: install test run
install:
	python -m pip install -e '.[test]'
test:
	python -m pytest -ra -vv --tb=long
run:
	uvicorn evez_tools.app:app --host 127.0.0.1 --port 8080
