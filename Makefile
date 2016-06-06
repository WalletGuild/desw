build:
	if ! [ -d "~/.desw" ]; \
	then \
		mkdir ~/.desw; \
	fi
	python setup.py build

install:
	if ! [ -d "~/.desw" ]; \
	then \
		mkdir ~/.desw; \
	fi
	python setup.py install

clean:
	rm -rf .cache build dist *.egg-info test/__pycache__
	rm -rf test/*.pyc *.egg *~ *pyc test/*~ .eggs
	rm -rf ~/.desw/*

swagger:
	flaskswagger desw.server:app --template desw/static/swagger.json --out-dir desw/static/

