#
# Pyrseas Makefile
#

PYTHON = python3

.PHONY: all build docs install installcheck check clean

all:
	$(PYTHON) setup.py build

build:
	$(PYTHON) setup.py sdist --format=gztar,zip
	$(PYTHON) setup.py bdist_wheel

docs:
	$(MAKE) -C docs html

install:
	$(PYTHON) setup.py install

installcheck check:
	$(PYTHON) setup.py test

clean:
	$(MAKE) -C docs clean
	$(PYTHON) setup.py clean
