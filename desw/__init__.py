import importlib
import logging
import os
import sys
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy_login_models.model import UserKey, User as SLM_User
import model

import ConfigParser
CFG = ConfigParser.ConfigParser()
CFG.read(os.environ.get('DESW_CONFIG_FILE', 'example_cfg.ini'))

# database stuff
eng = sa.create_engine(CFG.get('db', 'SA_ENGINE_URI'))
ses = orm.sessionmaker(bind=eng)()

def setup_database():
    SLM_User.metadata.create_all(eng)
    UserKey.metadata.create_all(eng)
    for m in model.__all__:
        getattr(model, m).metadata.create_all(eng)

setup_database()

models = model # rename loaded models to avoid ambiguity
models.User = SLM_User
models.UserKey = UserKey

# Setup logging
logfile = CFG.LOGFILE if hasattr(CFG, 'LOGFILE') else 'server.log'
loglevel = CFG.LOGLEVEL if hasattr(CFG, 'LOGLEVEL') else logging.INFO
logging.basicConfig(filename=logfile, level=loglevel)
logger = logging.getLogger(__name__)


def confirm_send(address, amount, ref_id=None):
    """
    Confirm that a send has completed. Does not actually check confirmations,
    but instead assumes that if this is called, the transaction has been
    completed. This is because we assume our own sends are safe.

    :param str ref_id: The updated ref_id for the transaction in question
    :param str address: The address that was sent to
    :param int amount: The amount that was sent, as an INT
    """
    debitq = ses.query(models.Debit)
    debitq.filter(models.Debit.address == address)
    debitq.filter(models.Debit.amount == amount)
    debit = debitq.filter(models.Debit.state == 'unconfirmed').first()
    if not debit:
        logger.info("debit already confirmed or address unknown. returning.")
        return
    debit.state = 'complete'
    if ref_id is not None:
        debit.ref_id = ref_id
    ses.add(debit)
    try:
        ses.commit()
    except Exception as e:
        logger.exception(e)
        ses.rollback()
        ses.flush()


def process_credit(amount, address, currency, network, state, reference,
                   ref_id, user_id):
    credit = models.Credit(amount=amount, address=address,
                           currency=currency, network=network, state=state,
                           reference=reference, ref_id=ref_id,
                           user_id=user_id)

    ses.add(credit)
    bal = ses.query(models.Balance)\
        .filter(models.Balance.user_id == user_id)\
        .filter(models.Balance.currency == currency)\
        .order_by(models.Balance.time.desc()).first()
    if state == 'complete':
        bal.available += amount
    bal.total += amount
    ses.add(bal)
    try:
        ses.commit()
    except Exception as e:
        print e
        logger.exception(e)
        ses.rollback()
        ses.flush()

