from desw import CFG, ses, models, logger, process_credit
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


# Internal Transaction Network functions
def _gen_txid():
    return ''.join(random.choice(string.digits) for i in range(20))


def internal_credit(address, amount, currency='BTC'):
    addyq = ses.query(models.Address)
    addy = addyq.filter(models.Address.address == address).first()
    if not addy:
        logger.warning("address not known. returning.")
        return
    return process_credit(amount, address, currency, 'Internal', 'unconfirmed',
                          'internal credit', _gen_txid(), addy.user_id)


def internal_confirm_credit(txid):
    credq = ses.query(models.Credit)
    credit = credq.filter(models.Credit.ref_id == txid).first()
    if not credit:
        logger.warning("credit not known. returning.")
        return
    credit.state = 'complete'
    credit.ref_id = "%s:0" % txid


def internal_address():
    addy = "M"
    for i in range(20):
        addy += random.choice(string.digits)
    return addy


class InternalPlugin():
    NETWORK = 'Internal'

    def __init__(self):
        for cur in json.loads(CFG.get('internal', 'CURRENCIES')):
            #TODO set this to maximum transaction sizes for each currency
            hwb = models.HWBalance(100000000000, 100000000000, cur, 'internal')
            ses.add(hwb)
            try:
                ses.commit()
            except Exception as ie:
                ses.rollback()
                ses.flush()

    def get_new_address(self):
        return internal_address()

    def validate_address(self, address, network=None):
        return address[0:1] == 'M' and len(address) == 21

    def send_to_address(self, address, amount):
        return _gen_txid()

    def get_balance(self):
        hwb = ses.query(models.HWBalance).filter(models.HWBalance.network == self.NETWORK.lower()).order_by(models.HWBalance.time.desc()).first()
        return {'total': hwb.total, 'available': hwb.available}


