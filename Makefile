black:
	black .

isort:
	isort --profile black .

mypy:
	mypy . --install-types

test:
	DJANGO_SETTINGS_MODULE="demo.settings" python -m pytest ./tests -svx

format: black isort

.PHONY: test format
