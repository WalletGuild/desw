PYTHON_VERSION=2.7  # not used...
SHELL = /bin/bash  # for pushd, but would probably be better to avoid this
PREREQDIR=.

makelog = if [ !  -d /var/log/desw/ ]; \
	then \
		sudo mkdir /var/log/desw/; \
		sudo chown $(USER) /var/log/desw/; \
	fi

makerun = if [ !  -d /var/run/desw/ ]; \
	then \
		sudo mkdir /var/run/desw/; \
	fi

installledger = if [ !  -d $(1)/ledger ]; \
	then \
		git clone git://github.com/ledger/ledger.git $(1)/ledger; \
		pushd $(1)/ledger; \
		if [ $(VIRTUAL_ENV) ]; \
			then \
				./acprep --prefix=$(VIRTUAL_ENV) --python update; \
			else \
				./acprep  --python update; \
		fi; \
		make; \
		make install; \
		popd; \
	fi

installsecp256k1 = if [ !  -d $(1)/libsecp256k1 ]; \
	then \
		git clone git://github.com/bitcoin/secp256k1.git $(1)/libsecp256k1; \
		pushd $(1)/libsecp256k1; \
		git checkout d7eb1ae96dfe9d497a26b3e7ff8b6f58e61e400a; \
		./autogen.sh; \
		if [ $(VIRTUAL_ENV) ]; \
			then \
				./configure --enable-module-recovery --enable-module-ecdh --enable-module-schnorr --prefix=$(VIRTUAL_ENV); \
			else \
				./configure --enable-module-recovery --enable-module-ecdh --enable-module-schnorr; \
		fi; \
		make; \
		make install; \
		popd; \
	fi

installlocalgit= if [ -d $(1) ]; \
	then \
		pushd $(1); \
		python setup.py install; \
		popd; \
	else \
		git clone $(2) $(1); \
		pushd $(1); \
		python setup.py install; \
		popd; \
	fi

makeclean = rm -rf .cache build dist *.egg-info test/__pycache__ \
	rm -rf test/*.pyc *.egg *~ *pyc test/*~ .eggs \
	rm -f .coverage*

build:
	python setup.py build

hackpendingPRs:
	$(call installlocalgit, $(shell readlink -f ../../tapp/tappmq/ https://github.com/GitGuild/tappmq.git))
	$(call installlocalgit, $(shell readlink -f ../../tapp/sqlalchemy-models/ https://github.com/GitGuild/sqlalchemy-models.git))

dependencies:
	$(call installledger, $(PREREQDIR))
	$(call installsecp256k1, $(PREREQDIR))

install:
	$(call makelog, "")
	$(call makerun, "")
	python setup.py -v install

clean:
	$(call makeclean, "")

purge:
	$(call makeclean, "")
	sudo rm -rf /var/run/desw
	sudo rm -rf /var/log/desw
	rm -rf $(PREREQDIR)/ledger
	rm -rf $(PREREQDIR)/libsecp256k1


swagger:
	flaskswagger desw.server:app --template desw/static/swagger.json --out-dir desw/static/

