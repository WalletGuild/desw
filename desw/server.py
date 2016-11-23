import copy
import datetime
import json
import os
from ledger import Amount

from alchemyjsonschema.dictify import jsonify
from flask import Flask, request, current_app
from flask.ext.cors import CORS
from flask.ext.login import login_required, current_user
from flask_bitjws import FlaskBitjws, load_jws_from_request
from sqlalchemy_models import jsonify2

import plugin
from desw import CFG, wm, um, ses, create_user_and_key

ps = plugin.load_plugins()

# get the swagger spec for this server
iml = os.path.dirname(os.path.realpath(__file__))
SWAGGER_SPEC = json.loads(open(iml + '/static/swagger.json').read())


__all__ = ['app', ]


def get_last_nonce(app, key, nonce):
    """
    Get the last_nonce used by the given key from the SQLAlchemy database.
    Update the last_nonce to nonce at the same time.

    :param str key: the public key the nonce belongs to
    :param int nonce: the last nonce used by this key
    """
    uk = ses.query(um.UserKey).filter(um.UserKey.key==key)\
            .filter(um.UserKey.last_nonce<nonce * 1000).first()
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
    user = ses.query(um.User).join(um.UserKey).filter(um.UserKey.key==key).first()
    return user

# Setup flask app and FlaskBitjws
app = Flask(__name__)
app._static_folder = "%s/static" % os.path.realpath(os.path.dirname(__file__))

FlaskBitjws(app, privkey=CFG.get('bitjws', 'PRIV_KEY'), get_last_nonce=get_last_nonce,
            get_user_by_key=get_user_by_key, basepath=CFG.get('bitjws', 'BASEPATH'))

CORS(app)


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
    balsq = ses.query(wm.Balance).filter(wm.Balance.user_id == current_user.id)
    if not balsq:
        return None
    bals = [json.loads(jsonify2(b, 'Balance')) for b in balsq]
    print "returning bals %s" % bals
    response = current_app.bitjws.create_response(bals)
    ses.close()
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
    if network.lower() in ps:
        try:
            addy = ps[network.lower()].get_new_address()
        except Exception as e:
            print type(e)
            print e
            current_app.logger.error(e)
            return 'wallet temporarily unavailable', 500
    else:
        return 'Invalid network', 400
    address = wm.Address(addy, currency, network, state, current_user.id)
    ses.add(address)
    try:
        ses.commit()
    except Exception as ie:
        ses.rollback()
        ses.flush()
        return 'Could not save address', 500
    newaddy = json.loads(jsonify2(address, 'Address'))
    current_app.logger.info("created new address %s" % newaddy)
    ses.close()
    return current_app.bitjws.create_response(newaddy)


@app.route('/address', methods=['GET'])
@login_required
def get_address():
    """
    Get one or more existing address(es) owned by your user.
    ---
    parameters:
      - name: address
        in: body
        description: The address you'd like to get info about.
        required: false
        schema:
          $ref: '#/definitions/Address'
    responses:
      '200':
        description: Your new address
        schema:
          items:
              $ref: '#/definitions/Address'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: getAddress
    """
    address = request.jws_payload['data'].get('address')
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    addysq = ses.query(wm.Address).filter(wm.Address.user_id == current_user.id)
    if address:
        addysq = addysq.filter(wm.Address.address == address)
    elif currency:
        addysq = addysq.filter(wm.Address.currency == currency)
    elif network:
        addysq = addysq.filter(wm.Address.network == network)
    if addysq.count() == 0:
        return "Invalid Request", 400

    addys = [json.loads(jsonify2(a, 'Address')) for a in addysq]
    response = current_app.bitjws.create_response(addys)
    ses.close()
    return response


@app.route('/search/debit', methods=['POST'])
@login_required
def search_debit():
    """
    Get one to ten debit(s) for a single User.
    ---
    parameters:
      - name: searchcd
        in: body
        description: The Debit(s) you'd like to get.
        required: false
        schema:
          $ref: '#/definitions/SearchCD'
    responses:
      '200':
        description: the User's debit(s)
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
    operationId: searchDebits
    """
    sid = request.jws_payload['data'].get('id')
    address = request.jws_payload['data'].get('address')
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    #reference = request.jws_payload['data'].get('reference')
    ref_id = request.jws_payload['data'].get('ref_id')
    page = request.jws_payload['data'].get('page') or 0

    debsq = ses.query(wm.Debit).filter(wm.Debit.user_id == current_user.id)
    if not debsq:
        return None

    if sid:
        debsq = debsq.filter(wm.Debit.id == sid)
    if address:
        debsq = debsq.filter(wm.Debit.address == address)
    if currency:
        debsq = debsq.filter(wm.Debit.currency == currency)
    if network:
        debsq = debsq.filter(wm.Debit.network == network)
    #if reference:
    #    debsq = debsq.filter(wm.Debit.reference == reference)
    if ref_id:
        debsq = debsq.filter(wm.Debit.ref_id == ref_id)
    debsq = debsq.order_by(wm.Debit.time.desc()).limit(10)
    if page and isinstance(page, int):
        debsq = debsq.offset(page * 10)

    debits = [json.loads(jsonify2(d, 'Debit')) for d in debsq]
    response = current_app.bitjws.create_response(debits)
    ses.close()
    return response


@app.route('/search/credit', methods=['POST'])
@login_required
def search_credit():
    """
    Get one to ten credit(s) for a single User.
    ---
    parameters:
      - name: searchcd
        in: body
        description: The Credit(s) you'd like to get.
        required: false
        schema:
          $ref: '#/definitions/SearchCD'
    responses:
      '200':
        description: the User's credit(s)
        schema:
          items:
            $ref: '#/definitions/Credit'
          type: array
      default:
        description: unexpected error
        schema:
          $ref: '#/definitions/errorModel'
    security:
      - kid: []
      - typ: []
      - alg: []
    operationId: searchCredits
    """
    sid = request.jws_payload['data'].get('id')
    address = request.jws_payload['data'].get('address')
    currency = request.jws_payload['data'].get('currency')
    network = request.jws_payload['data'].get('network')
    #reference = request.jws_payload['data'].get('reference')
    ref_id = request.jws_payload['data'].get('ref_id')
    page = request.jws_payload['data'].get('page') or 0

    credsq = ses.query(wm.Credit).filter(wm.Credit.user_id == current_user.id)
    if not credsq:
        return None
    if sid:
        credsq = credsq.filter(wm.Credit.id == sid)
    if address:
        credsq = credsq.filter(wm.Credit.address == address)
    if currency:
        credsq = credsq.filter(wm.Credit.currency == currency)
    if network:
        credsq = credsq.filter(wm.Credit.network == network)
    #if reference:
    #    credsq = credsq.filter(wm.Credit.reference == reference)
    if ref_id:
        credsq = credsq.filter(wm.Credit.ref_id == ref_id)
    credsq = credsq.order_by(wm.Credit.time.desc()).limit(10)
    if page and isinstance(page, int):
        credsq = credsq.offset(page * 10)

    credits = [json.loads(jsonify2(c, 'Credit')) for c in credsq]
    response = current_app.bitjws.create_response(credits)
    ses.close()
    return response


@app.route('/network/<string:network>', methods=['GET'])
def network_info(network):
    """
    Get information about the transaction network indicated.
    Returned info is: enabled/disabled, available hot wallet balance,
    & the transaction fee.
    ---
    description: Get information about the transaction network indicated.
    operationId: getinfo
    produces:
      - application/json
    parameters:
      - name: network
        in: path
        type: string
        required: true
        description: The network name i.e. Bitcoin, Dash
    responses:
      '200':
        description: the network information
        schema:
          $ref: '#/definitions/NetworkInfo'
      default:
        description: an error
        schema:
          $ref: '#/definitions/errorModel'
    """
    lnet = network.lower()
    isenabled = lnet in ps
    fee = float(CFG.get(lnet, 'FEE'))
    roughAvail = str(int(ps[lnet].get_balance()['available'].to_double()))
    available = float(10 ** (len(roughAvail) - 1))
    response = json.dumps({'isenabled': isenabled, 'fee': fee,
                           'available': available})
    ses.close()
    return response


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
          $ref: '#/definitions/Debit'
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
    currency = request.jws_payload['data'].get('currency')
    amount = Amount("%s %s" % (request.jws_payload['data'].get('amount'),
                               currency))
    address = request.jws_payload['data'].get('address')
    network = request.jws_payload['data'].get('network')
    reference = request.jws_payload['data'].get('reference')
    state = 'unconfirmed'
    try:
        debit = plugin.create_debit(current_user, amount, currency, address, network, reference, state='unconfirmed',
                                    plugins=ps, session=ses)
        plugin.process_debit(debit, plugins=ps, session=ses)
    except (IOError, ValueError) as e:
        current_app.logger.exception(e)
        ses.rollback()
        ses.flush()
        return "Unable to send money", 400
    except Exception as e:
        current_app.logger.exception(e)
        ses.rollback()
        ses.flush()
        return "Unable to send money", 500
    result = json.loads(jsonify2(debit, 'Debit'))
    current_app.logger.info("created new debit %s" % result)
    ses.close()
    return current_app.bitjws.create_response(result)


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
          $ref: '#/definitions/User'
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
    userdict = json.loads(jsonify2(current_user.dbuser, 'User'))
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
    last_nonce = request.jws_payload['iat']*1000
    try:
        user, userkey = create_user_and_key(username=username, address=address, last_nonce=last_nonce, session=ses)
    except IOError:
        ses.rollback()
        ses.flush()
        return 'username or key taken', 400
    jresult = json.loads(jsonify2(userkey, 'UserKey'))
    current_app.logger.info("registered user %s with key %s" % (user.id, userkey.key))
    ses.close()
    return current_app.bitjws.create_response(jresult)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8002, debug=True)

