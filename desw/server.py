import alchemyjsonschema as ajs
import bitjws
import copy
import imp
import json
import logging
import os
import sys
import sqlalchemy as sa
import sqlalchemy.orm as orm
from alchemyjsonschema.dictify import jsonify
from flask import Flask, request, current_app, make_response
from flask.ext.cors import CORS
from flask.ext.login import login_required, current_user
from flask_bitjws import FlaskBitjws, load_jws_from_request, FlaskUser
from jsonschema import validate, ValidationError
from sqlalchemy_login_models.model import UserKey, User as SLM_User
import model
#import ConfigParser

# configuration
#config = ConfigParser.ConfigParser(os.environ.get('DESW_CONFIG_FILE', 'example_cfg.ini'))

try:
    cfg_loc = os.environ.get('DESW_CONFIG_FILE', 'example_cfg.py')
    cfg_raw = None
    with open(cfg_loc, 'r') as f:
        cfg = imp.load_module("config_as_module", f, cfg_loc,
                              ('.py', 'r', imp.PY_SOURCE))
except Exception as e:
    print e
    print "Unable to configurate application. Exiting."
    sys.exit()

"""
plugin stuff
"""
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# Dash RPC
dashrpc = AuthServiceProxy(cfg.DASH_RPC_URL)
#print "dash info: %s" % dashrpc.getinfo()

# Bitcoin RPC
bitcoinrpc = AuthServiceProxy(cfg.BITCOIN_RPC_URL)
#print "bitcoin info: %s" % bitcoinrpc.getinfo()



# get the swagger spec for this server
iml = os.path.dirname(os.path.realpath(__file__))
SWAGGER_SPEC = json.loads(open(iml + '/static/swagger.json').read())
# invert definitions
def jsonify2(obj, name):
    #TODO replace this with a cached definitions patch
    #this is inefficient to do each time...
    spec = copy.copy(SWAGGER_SPEC['definitions'][name])
    spec['definitions'] = SWAGGER_SPEC['definitions']
    return jsonify(obj, spec)

__all__ = ['app', ]


def get_last_nonce(app, key, nonce):
    """
    Get the last_nonce used by the given key from the SQLAlchemy database.
    Update the last_nonce to nonce at the same time.

    :param str key: the public key the nonce belongs to
    :param int nonce: the last nonce used by this key
    """
    uk = ses.query(UserKey).filter(UserKey.key==key)\
            .filter(UserKey.last_nonce<nonce * 1000).first()
    if not uk:
        return None
    lastnonce = copy.copy(uk.last_nonce)
    # TODO Update DB record in same query as above, if possible
    uk.last_nonce = nonce * 1000
    try:
        ses.commit()
    except Exception as e:
        current_app.logger.exception(e)
        ses.rollback()
        ses.flush()
    return lastnonce


def get_user_by_key(app, key):
    """
    An SQLAlchemy User getting function. Get a user by public key.

    :param str key: the public key the user belongs to
    """
    user = ses.query(SLM_User).join(UserKey).filter(UserKey.key==key).first()
    return user

# Setup flask app and FlaskBitjws
app = Flask(__name__)
app._static_folder = "%s/static" % os.path.realpath(os.path.dirname(__file__))

FlaskBitjws(app, privkey=cfg.PRIV_KEY, get_last_nonce=get_last_nonce,
            get_user_by_key=get_user_by_key, basepath=cfg.BASEPATH)

# Setup logging
logfile = cfg.LOGFILE if hasattr(cfg, 'LOGFILE') else 'server.log'
loglevel = cfg.LOGLEVEL if hasattr(cfg, 'LOGLEVEL') else logging.INFO
logging.basicConfig(filename=logfile, level=loglevel)
logger = logging.getLogger(__name__)

# Setup CORS
CORS(app)

# Setup database
eng = sa.create_engine(cfg.SA_ENGINE_URI)
ses = orm.sessionmaker(bind=eng)()
SLM_User.metadata.create_all(eng)
UserKey.metadata.create_all(eng)
for m in model.__all__:
    getattr(model, m).metadata.create_all(eng)


@app.route('/balance', methods=['GET'])
@login_required
def get_balance():
    """
    Get the latest balance(s) for a single User.
    Currently no search parameters are supported. All balances returned.
    ---
    responses:
      '200':
        description: the User's balance(s)
        schema:
          items:
            $ref: '#/definitions/Balance'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: getBalance
    """
    balsq = ses.query(model.Balance).filter(model.Balance.user_id == current_user.id)
    if not balsq:
        return None
    bals = [jsonify2(b, 'Balance') for b in balsq]
    response = current_app.bitjws.create_response(bals)
    return response


@app.route('/address', methods=['POST'])
@login_required
def create_address():
    """
    Create a new address owned by your user.
    ---
    parameters:
      - name: address
        in: body
        description: The pseudo-address you would like to create. i.e. currency and network
        required: true
        schema:
          $ref: '#/definitions/Address'
    responses:
      '200':
        description: Your new address
        schema:
          $ref: '#/definitions/Address'
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: createAddress
    """
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    state = 'active'
    if network == "Dash":
        addy = dashrpc.getnewaddress()
    elif network == "Bitcoin":
        addy = bitcoinrpc.getnewaddress()
    print jsonify2(current_user, 'User')
    print current_user.id
    address = model.Address(addy, currency, network, state, current_user.id)
    ses.add(address)
    try:
        ses.commit()
    except Exception as ie:
        ses.rollback()
        ses.flush()
        return 'Could not create address', 500
    newaddy = jsonify2(address, 'Address')
    current_app.logger.info("created new address %s" % newaddy)
    return current_app.bitjws.create_response(newaddy)


@app.route('/debit', methods=['POST'])
@login_required
def create_debit():
    """
    Create a new debit, sending tokens out of your User's account.
    ---
    parameters:
      - name: debit
        in: body
        description: The debit you would like to create.
        required: true
        schema:
          $ref: '#/definitions/Debit'
    responses:
      '200':
        description: The Debit record
        schema:
          items:
            $ref: '#/definitions/Debit'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: sendMoney
    """
    amount = request.jws_payload['data'].get('amount')
    address = request.jws_payload['data'].get('address')
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    reference = request.jws_payload['data'].get('reference')
    ref_id = request.jws_payload['data'].get('ref_id')
    state = 'unconfirmed'
    debit = model.Debit(amount, address, currency, network, state, reference, ref_id, current_user.id)
    ses.add(debit)
    try:
        ses.commit()
    except Exception as ie:
        ses.rollback()
        ses.flush()
        return 'Could not create debit', 500
    current_app.logger.info("created new debit %s" % debit)
    newdebit = jsonify2(debit, 'Debit')
    return current_app.bitjws.create_response(newdebit)


@app.route('/user', methods=['GET'])
@login_required
def get_user():
    """
    Get your user object.

    Users may only get their own info, not others'.
    ---
    responses:
      '200':
        description: user response
        schema:
          items:
            $ref: '#/definitions/User'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    description: get your user record
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: getUserList
    """
    userdict = jsonify2(current_user.db_user, 'User')
    return current_app.bitjws.create_response(userdict)


@app.route('/user', methods=['POST'])
def add_user():
    """
    Register a new User.
    Create a User and a UserKey based on the JWS header and payload.
    ---
    operationId:
      addUser
    parameters:
      - name: user
        in: body
        description: A new User to add
        required: true
        schema:
          $ref: '#/definitions/User'
    responses:
      '200':
        description: "user's new key"
        schema:
          $ref: '#/definitions/UserKey'
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    """
    load_jws_from_request(request)
    if not hasattr(request, 'jws_header') or request.jws_header is None:
        return "Invalid Payload", 401
    username = request.jws_payload['data'].get('username')
    address = request.jws_header['kid']
    user = SLM_User(username=username)
    ses.add(user)
    try:
        ses.commit()
    except Exception as ie:
        current_app.logger.exception(ie)
        ses.rollback()
        ses.flush()
        return 'username taken', 400
    userkey = UserKey(key=address, keytype='public', user_id=user.id,
                      last_nonce=request.jws_payload['iat']*1000)
    ses.add(userkey)
    ses.add(model.Balance(total=0, available=0, currency='BTC', reference='open account', user_id=user.id))
    ses.add(model.Balance(total=0, available=0, currency='DASH', reference='open account', user_id=user.id))
    try:
        ses.commit()
    except Exception as ie:
        current_app.logger.exception(ie)
        ses.rollback()
        ses.flush()
        #ses.delete(user)
        #ses.commit()
        return 'username taken', 400
    jresult = jsonify2(userkey, 'UserKey')
    current_app.logger.info("registered user %s with key %s" % (user.id, userkey.key))

    return current_app.bitjws.create_response(jresult)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8002, debug=True)
