import datetime
import json
from ledger import Amount

from sqlalchemy_models import (setup_database,
                               create_session_engine, wallet as wm,
                               user as um)
from tapp_config import get_config, setup_logging

CFG = get_config('desw')
ses, eng = create_session_engine(cfg=CFG)
setup_database(eng, modules=[wm, um])

logger = setup_logging('desw', prefix='desw', cfg=CFG)


def confirm_send(address, amount, ref_id=None, session=ses):
    """
    Confirm that a send has completed. Does not actually check confirmations,
    but instead assumes that if this is called, the transaction has been
    completed. This is because we assume our own sends are safe.

    :param session:
    :param str ref_id: The updated ref_id for the transaction in question
    :param str address: The address that was sent to
    :param Amount amount: The amount that was sent
    """
    debitq = session.query(wm.Debit)
    debitq = debitq.filter(wm.Debit.address == address)
    debitq = debitq.filter(wm.Debit.amount == amount)
    debit = debitq.filter(wm.Debit.transaction_state == 'unconfirmed').first()
    if not debit:
        raise ValueError("Debit already confirmed or address unknown.")
    debit.transaction_state = 'complete'
    if ref_id is not None:
        debit.ref_id = ref_id
    session.add(debit)
    session.commit()
    return debit


def process_credit(amount, address, currency, network, transaction_state, reference,
                   ref_id, user_id, session=ses):
    logger.debug("%s" % amount)
    credit = wm.Credit(amount=amount, address=address,
                       currency=currency, network=network, transaction_state=transaction_state,
                       reference=reference, ref_id=ref_id,
                       user_id=user_id, time=datetime.datetime.utcnow())
    session.add(credit)
    avail = amount if transaction_state == 'complete' else Amount("0 %s" % currency)
    adjust_user_balance(user_id, currency, avail, amount, ref_id, ses)
    session.commit()
    return credit


def adjust_user_balance(user_id, currency, available=None, total=None, reference=None, session=ses):
    if available is None and total is None:
        return
    bal = session.query(wm.Balance)\
        .filter(wm.Balance.user_id == user_id)\
        .filter(wm.Balance.currency == currency).first()
    if available is None:
        available = Amount("0 %s" % currency)
    if total is None:
        total = Amount("0 %s" % currency)

    bal.available = bal.available + available
    bal.total = bal.total + total
    assert bal.available <= bal.total
    bal.time = datetime.datetime.utcnow()
    if reference is not None:
        bal.reference = str(reference)
    session.add(bal)


def adjust_hw_balance(currency, network, available=None, total=None, session=ses):
    if available is None and total is None:
        return
    hwb = session.query(wm.HWBalance).filter(wm.HWBalance.network == network).order_by(wm.HWBalance.time.desc()).first()
    if available is None:
        available = Amount("0 %s" % currency)
    if total is None:
        total = Amount("0 %s" % currency)
    available += hwb.available
    total += hwb.total
    new_hwb = wm.HWBalance(available, total, currency, network)
    session.add(new_hwb)


def guess_network_by_currency(currency):
    if currency == "BTC":
        return "Bitcoin"
    elif currency == "DASH":
        return "Dash"
    elif currency == "ETH":
        return "Ethereum"
    elif currency == "LTC":
        return "Litecoin"


def create_user_and_key(username, address, last_nonce, session=ses):
    user = um.User(username=username)
    session.add(user)
    try:
        session.commit()
    except Exception as ie:
        logger.exception(ie)
        session.rollback()
        session.flush()
        raise IOError("username or key taken")
    userkey = um.UserKey(key=address, keytype='public', user_id=user.id,
                         last_nonce=last_nonce)
    session.add(userkey)
    for cur in json.loads(CFG.get('internal', 'CURRENCIES')):
        session.add(wm.Balance(total=Amount("0 %s" % cur), available=Amount("0 %s" % cur), currency=cur, reference='open account', user_id=user.id))
    try:
        session.commit()
    except Exception as ie:
        logger.exception("hmmm unable to create user")
        logger.exception(ie)
        session.rollback()
        session.flush()
        session.delete(user)
        session.commit()
        raise IOError("username or key taken")
    return user, userkey
