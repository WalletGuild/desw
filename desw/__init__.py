import datetime
import importlib
import logging
import os
import sys
import sqlalchemy as sa
import sqlalchemy.orm as orm

# rename for ease and to avoid ambiguity
from sqlalchemy_models.user import UserKey, User as SLM_User
from sqlalchemy_models import (setup_database,
                               create_session_engine, wallet as wm,
                               user as um)

from tapp_config import get_config, setup_logging

CFG = get_config('desw')
ses, eng = create_session_engine(cfg=CFG)
setup_database(eng, modules=[wm, um])

logger = setup_logging('desw', prefix='desw', cfg=CFG)

def confirm_send(address, amount, ref_id=None):
    """
    Confirm that a send has completed. Does not actually check confirmations,
    but instead assumes that if this is called, the transaction has been
    completed. This is because we assume our own sends are safe.

    :param str ref_id: The updated ref_id for the transaction in question
    :param str address: The address that was sent to
    :param int amount: The amount that was sent, as an INT
    """
    debitq = ses.query(wm.Debit)
    debitq.filter(wm.Debit.address == address)
    debitq.filter(wm.Debit.amount == amount)
    debit = debitq.filter(wm.Debit.transaction_state == 'unconfirmed').first()
    if not debit:
        logger.info("debit already confirmed or address unknown. returning.")
        return
    debit.transaction_state = 'complete'
    if ref_id is not None:
        debit.ref_id = ref_id
    ses.add(debit)
    try:
        ses.commit()
    except Exception as e:
        logger.exception(e)
        ses.rollback()
        ses.flush()
    return debit


def process_credit(amount, address, currency, network, transaction_state, reference,
                   ref_id, user_id):
    logger.debug("%s" % amount)
    credit = wm.Credit(amount=amount, address=address,
                       currency=currency, network=network, transaction_state=transaction_state,
                       reference=reference, ref_id=ref_id,
                       user_id=user_id, time=datetime.datetime.utcnow())
    ses.add(credit)
    bal = ses.query(wm.Balance)\
        .filter(wm.Balance.user_id == user_id)\
        .filter(wm.Balance.currency == currency)\
        .order_by(wm.Balance.time.desc()).first()
    if transaction_state == 'complete':
        bal.available = bal.available + amount
    bal.total = bal.total + amount
    ses.add(bal)
    try:
        ses.commit()
    except Exception as e:
        print e
        logger.exception(e)
        ses.rollback()
        ses.flush()
    return credit

