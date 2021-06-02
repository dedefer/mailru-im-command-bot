
lint:
	isort -c .
	flake8 .
	mypy .

test:
	coverage run --source=mailru_im_command_bot -m tests.tests
