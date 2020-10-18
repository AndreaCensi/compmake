package=compmake

include pypackage.mk

bump-upload:
	$(MAKE) bump
	$(MAKE) upload
bump:
	bumpversion patch
	git push --tags
	git push --all
upload:
	rm -f dist/*
	rm -rf src/*.egg-info
	python3 setup.py sdist
	twine upload dist/*

vulture:


name=compmake-python3

test-python3:
	docker stop $(name) || true
	docker rm $(name) || true

	docker run -it -v "$(shell realpath $(PWD)):/compmake" -w /compmake --name $(name) python:3 /bin/bash

test-python3-install:
	pip install -r requirements.txt
	pip install nose
	python setup.py develop --no-deps

