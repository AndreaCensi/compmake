ARG REGISTRY=docker.io
ARG BASE_IMAGE=library/python:3.8
FROM ${REGISTRY}/${BASE_IMAGE}
# Note: after FROM, we cannot access ARG declared before FROM.

ARG PIP_INDEX_URL
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /compmake

COPY requirements.pin.txt .
RUN pip install -r requirements.pin.txt

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .


RUN pipdeptree
RUN python setup.py develop --no-deps
# run it once to see everything OK
# RUN zt-demo --help
