package=compmake

include pypackage.mk

bump-upload:
	bumpversion patch
	git push --tags
	git push --all
	rm -f dist/*
	python setup.py sdist
	twine upload dist/*
	
vulture:


name=compmake-python3

test1:
	docker stop $(name) || true
	docker rm $(name) || true

	docker run -it -v "$(shell realpath $(PWD)):/compmake" -w /compmake --name $(name) python:3 /bin/bash

test1-install:
	pip install -r requirements.txt
	pip install nose
	python setup.py develop --no-deps

