black:
	black .

isort:
	isort --profile black .

mypy:
	mypy . --install-types

tests:
	DJANGO_SETTINGS_MODULE="demo.settings" python -m pytest ./tests -svx

format: black isort

.PHONY: tests format
