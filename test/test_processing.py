import time

from ledger import Amount

from desw import create_user_and_key, ses, um, wm, adjust_user_balance, process_credit, confirm_send
from desw.plugin import create_debit, internal_credit, confirm_credit, _gen_txid, process_debit
from . import create_username_address


def test_create_user_and_key():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    assert isinstance(user, um.User)
    assert isinstance(userkey, um.UserKey)


def test_create_user_used_name():
    username, address = create_username_address()
    create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    username2, address2 = create_username_address()
    try:
        create_user_and_key(username=username, address=address2, last_nonce=time.time() * 1000,
                                            session=ses)
        assert not "username was already used, but did not throw IOError as expected"
    except IOError:
        pass


def test_create_user_used_address():
    username, address = create_username_address()
    create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    username2, address2 = create_username_address()
    try:
        create_user_and_key(username=username2, address=address, last_nonce=time.time() * 1000,
                                            session=ses)
        assert not "address was already used, but did not throw IOError as expected"
    except IOError:
        pass
    dbuser = ses.query(um.User).filter(um.User.username == username2).first()
    assert dbuser is None


def test_adjust_user_balance():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    adjust_user_balance(user.id, 'BTC', available=Amount("0 BTC"), total=Amount("0.01 BTC"), session=ses)
    ses.commit()
    bal2 = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal2.available == Amount("0 BTC")
    assert bal2.total == Amount("0.01 BTC")

    adjust_user_balance(user.id, 'BTC', available=Amount("0.01 BTC"), total=Amount("0 BTC"), session=ses)
    ses.commit()
    bal3 = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    bal3.load_commodities()
    assert bal3.available == Amount("0.01 BTC")
    assert bal3.total == Amount("0.01 BTC")

    adjust_user_balance(user.id, 'BTC', available=Amount("-0.01 BTC"), total=Amount("-0.01 BTC"), session=ses)
    ses.commit()
    bal4 = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    bal4.load_commodities()
    assert bal4.available == Amount("0 BTC")
    assert bal4.total == Amount("0 BTC")


def test_adjust_user_balance_uneven():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    try:
        adjust_user_balance(user.id, 'BTC', available=Amount("1 BTC"), total=Amount("0.01 BTC"), session=ses)
        assert not "uneven user balance used, but did not throw AssertionError as expected"
    except AssertionError:
        pass


def test_process_unconfirmed_credit():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    ses.commit()
    # process_credit(Amount("0.01 BTC"), address, "BTC", 'Internal', 'unconfirmed', '', )
    credit = internal_credit(caddress.address, Amount("0.01 BTC"), session=ses)
    assert isinstance(credit, wm.Credit)
    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.available == Amount("0 BTC")
    assert bal.total == Amount("0.01 BTC")


def test_process_credit():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    ses.commit()
    # process_credit(Amount("0.01 BTC"), address, "BTC", 'Internal', 'unconfirmed', '', )
    credit = internal_credit(caddress.address, Amount("0.01 BTC"), state='complete', session=ses)
    assert isinstance(credit, wm.Credit)
    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.available == Amount("0.01 BTC")
    assert bal.total == Amount("0.01 BTC")
    try:
        confirm_credit(credit=credit, session=ses)
        assert not "confirming complete credit, but did not throw ValueError as expected"
    except ValueError:
        pass


def test_confirm_credit():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    ses.commit()
    # process_credit(Amount("0.01 BTC"), address, "BTC", 'Internal', 'unconfirmed', '', )
    credit = internal_credit(caddress.address, Amount("0.01 BTC"), session=ses)
    confirm_credit(credit=credit, session=ses)
    bal2 = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal2.available == Amount("0.01 BTC")
    assert bal2.total == Amount("0.01 BTC")


def test_confirm_credit_by_txid():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    ses.commit()
    credit = internal_credit(caddress.address, Amount("0.01 BTC"), session=ses)
    confirm_credit(txid=credit.ref_id, session=ses)
    bal2 = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal2.available == Amount("0.01 BTC")
    assert bal2.total == Amount("0.01 BTC")


def test_create_debit():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    username2, address2 = create_username_address()
    user2, userkey2 = create_user_and_key(username=username2, address=address2, last_nonce=time.time() * 1000,
                                          session=ses)
    caddress2 = wm.Address(_gen_txid(), "BTC", "Internal", "active", user2.id)
    ses.add(caddress2)
    ses.commit()
    internal_credit(caddress.address, Amount("0.01 BTC"), state='complete', session=ses)
    debit = create_debit(user, Amount("0.001 BTC"), "BTC", caddress2.address, 'Internal', "", session=ses)
    assert isinstance(debit, wm.Debit)
    assert debit.network == 'internal'
    assert debit.transaction_state == 'unconfirmed'
    txid = _gen_txid()
    cdebit = confirm_send(caddress2.address, 0.001, ref_id=txid, session=ses)
    assert cdebit.transaction_state == 'complete'
    assert cdebit.ref_id == txid
    dbdebit = ses.query(wm.Debit).filter(wm.Debit.id == debit.id).first()
    assert dbdebit.transaction_state == 'complete'
    assert dbdebit.ref_id == txid


def test_create_debit_no_funds():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    username2, address2 = create_username_address()
    user2, userkey2 = create_user_and_key(username=username2, address=address2, last_nonce=time.time() * 1000,
                                          session=ses)
    caddress2 = wm.Address(_gen_txid(), "BTC", "Internal", "active", user2.id)
    ses.add(caddress2)
    ses.commit()
    try:
        create_debit(user, Amount("0.001 BTC"), "BTC", caddress2.address, 'Internal', "", session=ses)
        assert not "debit created even though not enough funds were available"
    except ValueError:
        pass


def test_process_internal_debit():
    username, address = create_username_address()
    user, userkey = create_user_and_key(username=username, address=address, last_nonce=time.time() * 1000,
                                        session=ses)
    caddress = wm.Address(_gen_txid(), "BTC", "Internal", "active", user.id)
    ses.add(caddress)
    username2, address2 = create_username_address()
    user2, userkey2 = create_user_and_key(username=username2, address=address2, last_nonce=time.time() * 1000,
                                          session=ses)
    caddress2 = wm.Address(_gen_txid(), "BTC", "Internal", "active", user2.id)
    ses.add(caddress2)
    ses.commit()
    internal_credit(caddress.address, Amount("0.01 BTC"), state='complete', session=ses)
    debit = create_debit(user, Amount("0.001 BTC"), "BTC", caddress2.address, 'Internal', "", session=ses)
    process_debit(debit, session=ses)
    credit = ses.query(wm.Credit).filter(wm.Credit.ref_id == str(debit.id)).first()
    assert credit.amount == Amount("0.001 BTC")
    assert credit.transaction_state == 'complete'
    dbdebit = ses.query(wm.Debit).filter(wm.Debit.id == debit.id).first()
    assert dbdebit.transaction_state == 'complete'
    assert dbdebit.ref_id == str(credit.id)
