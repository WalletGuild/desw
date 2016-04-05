from desw import CFG, ses, models, logger, process_credit
import importlib
import random
import string


def load_plugins():
    plugins = {}
    for section in CFG.sections():
        if section not in ['db', 'bitjws', 'log', 'test']:
            # assume section refers to a plugin module unless it is 'mock'
            if section == 'mock':
                plugins[section] = MockPlugin()
            else:
                pname = "desw_%s" % section
                plugins[section] = importlib.import_module(pname)
    return plugins


# Mock functions
def _gen_txid():
        return ''.join(random.choice(string.digits) for i in range(20))


def mock_credit(address, amount):
    addyq = ses.query(models.Address)
    addy = addyq.filter(models.Address.address == address).first()
    if not addy:
        logger.warning("address not known. returning.")
        return
    return process_credit(amount, address, 'MCK', 'Mock', 'unconfirmed',
                          'mock credit', _gen_txid(), addy.user_id)


def mock_confirm_credit(txid):
    credq = ses.query(models.Credit)
    credit = addyq.filter(models.Credit.ref_id == txid).first()
    if not addy:
        logger.warning("credit not known. returning.")
        return
    credit.state = 'complete'
    credit.ref_id = "%s:0" % txid


def mock_address():
    addy = "M"
    for i in range(20):
        addy += random.choice(string.digits)
    return addy


class MockPlugin():
    CURRENCY = 'MCK'
    NETWORK = 'Mock'

    def get_new_address(self):
        return mock_address()

    def validate_address(self, address, network=None):
        return address[0:1] == 'M' and len(address) == 21

    def send_to_address(self, address, amount):
        return _gen_txid()


