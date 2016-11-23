import datetime

from sqlalchemy_models import jsonify2

from desw import CFG, ses, wm, logger, process_credit, adjust_user_balance
from ledger import Amount
import importlib
import json
import random
import string


def load_plugins():
    plugins = {}
    for section in CFG.sections():
        if section not in ['db', 'bitjws', 'log', 'test', 'internal']:
            # assume section refers to a plugin module
            pname = "desw_%s" % section
            plugins[section] = importlib.import_module(pname)
    plugins['internal'] = InternalPlugin()
    return plugins


def confirm_credit(credit=None, txid=None, session=ses):
    if credit is None and txid is None:
        raise ValueError("Either credit or txid must be provided for confirm_credit")
    elif credit is None:
        credq = session.query(wm.Credit).filter(wm.Credit.transaction_state == 'unconfirmed')
        credit = credq.filter(wm.Credit.ref_id == txid).first()
    if not credit or credit.transaction_state != 'unconfirmed':
        # logger.warning("credit not known. returning.")
        raise ValueError("credit not known or not unconfirmed: %s" % txid)
        return
    if txid is not None:
        credit.ref_id = txid
    credit.transaction_state = 'complete'
    session.add(credit)
    adjust_user_balance(credit.user_id, credit.currency, available=credit.amount, total=None,
                        reference=credit.ref_id, session=session)
    session.commit()


def create_debit(user, amount, currency, address, network, reference, state='unconfirmed', plugins=None, session=ses):
    if plugins is None:
        plugins = load_plugins()
    if network.lower() not in plugins:
        raise ValueError("Plugin %s not active" % network)

    dbaddy = session.query(wm.Address)\
        .filter(wm.Address.address == address)\
        .filter(wm.Address.currency == currency).first()
    if dbaddy is not None and dbaddy.address == address:
        network = 'internal'
    elif network == 'internal' and dbaddy is None:
        raise ValueError("internal address %s not found" % address)
    fee = Amount("%s %s" % (CFG.get(network.lower(), 'FEE'), currency))

    txid = 'TBD'
    debit = wm.Debit(amount, fee, address,
                     currency, network, state, reference, txid,
                     user.id, datetime.datetime.utcnow())
    session.add(debit)

    bal = session.query(wm.Balance)\
        .filter(wm.Balance.user_id == user.id)\
        .filter(wm.Balance.currency == currency)\
        .order_by(wm.Balance.time.desc()).first()
    if not bal or bal.available < amount + fee:
        session.rollback()
        session.flush()
        raise ValueError("not enough funds")
    else:
        bal.total = bal.total - (amount + fee)
        bal.available = bal.available - (amount + fee)
        bal.time = datetime.datetime.utcnow()
        bal.reference = "debit: %s" % txid
        session.add(bal)
        logger.info("updating balance %s" % jsonify2(bal, 'Balance'))
    try:
        session.commit()
    except Exception as ie:
        logger.exception(ie)
        session.rollback()
        session.flush()
        raise IOError("unable to send funds")
    return debit


def process_debit(debit, plugins=None, session=ses):
    if plugins is None:
        plugins = load_plugins()
    if debit.network.lower() not in plugins:
        raise ValueError("Plugin %s not active" % debit.network)
    # debit.load_commodities()
    if debit.network == 'internal':
        dbaddy = session.query(wm.Address) \
            .filter(wm.Address.address == debit.address) \
            .filter(wm.Address.currency == debit.currency).first()
        adjust_user_balance(dbaddy.user_id, debit.currency, available=-debit.amount, total=-debit.amount,
                            reference=debit.ref_id, session=session)
        credit = wm.Credit(debit.amount, debit.address, debit.currency, debit.network, 'complete', debit.reference,
                           debit.id, dbaddy.user_id, datetime.datetime.utcnow())
        session.add(credit)
        try:
            session.commit()
            debit.ref_id = str(credit.id)
        except Exception as ie:
            session.rollback()
            session.flush()
            raise IOError('unable to send funds')
    else:
        try:
            debit.ref_id = plugins[debit.network.lower()].send_to_address(debit.address, debit.amount)
        except Exception as e:
            logger.error(e)
            raise IOError('wallet temporarily unavailable')

    debit.transaction_state = 'complete'
    session.commit()


# Internal Transaction Network functions
def _gen_txid():
    return ''.join(random.choice(string.digits) for i in range(20))


def internal_credit(address, amount, currency='BTC', state='unconfirmed', session=ses):
    addyq = session.query(wm.Address)
    addy = addyq.filter(wm.Address.address == address).first()
    if not addy:
        logger.warning("address not known. returning.")
        return
    return process_credit(amount, address, currency, 'Internal', state,
                          'internal credit', _gen_txid(), addy.user_id, session=session)


def internal_address():
    addy = "M"
    for i in range(20):
        addy += random.choice(string.digits)
    return addy


class InternalPlugin():
    NETWORK = 'Internal'

    def __init__(self, session=ses):
        for cur in json.loads(CFG.get('internal', 'CURRENCIES')):
            #TODO set this to maximum transaction sizes for each currency
            hwb = wm.HWBalance(Amount("1000 %s" % cur), Amount("1000 %s" % cur), cur, 'internal')
            session.add(hwb)
            try:
                session.commit()
            except Exception as ie:
                session.rollback()
                session.flush()

    def get_new_address(self):
        return internal_address()

    def validate_address(self, address, network=None):
        return address[0:1] == 'M' and len(address) == 21

    def send_to_address(self, address, amount):
        return _gen_txid()

    def get_balance(self, session=ses):
        hwb = session.query(wm.HWBalance).filter(wm.HWBalance.network == self.NETWORK.lower()).order_by(wm.HWBalance.time.desc()).first()
        return {'total': hwb.total, 'available': hwb.available}


