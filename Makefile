
lint:
	isort -c .
	flake8 .
	mypy .

test:
	python3 -m tests.tests
