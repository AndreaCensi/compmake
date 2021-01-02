package=compmake_tests

include pypackage.mk


bump:
	bumpversion patch
	git push --tags
	git push --all

upload:
	rm -f dist/*
	rm -rf src/*.egg-info
	python3 setup.py sdist
	devpi use $(TWINE_REPOSITORY_URL)
	devpi login $(TWINE_USERNAME) --password $(TWINE_PASSWORD)
	devpi upload --verbose dist/*

COVERAGE_FILE=out/cov/data

nosequick:
	coverage erase
	mkdir -p out/cov
	COVERAGE_FILE=$(COVERAGE_FILE) \
	nosetests compmake_tests --with-coverage --cover-html --cover-html-dir out/cov \
		--cover-package compmake,compmake_plugins,compmake_tests --cover-tests --cover-erase --cover-branches



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


build2:
	dts build_utils aido-container-build --ignore-dirty --ignore-untagged
