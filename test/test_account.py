import bitjws
import json
import os
import pytest
import time
from bravado.swagger_model import load_file
from bravado_bitjws.client import BitJWSSwaggerClient
from desw import CFG, ses, eng, wm
from desw.plugin import internal_credit, internal_address, internal_confirm_credit
from ledger import Amount

host = "0.0.0.0"
url = "http://0.0.0.0:8002/"
specurl = os.path.abspath('../desw/desw/static/swagger.json')

privkey = bitjws.PrivateKey()
my_pubkey = privkey.pubkey.serialize()
my_address = bitjws.pubkey_to_addr(my_pubkey)
username = str(my_address)[0:8]
client = BitJWSSwaggerClient.from_spec(load_file(specurl), origin_url=url)
luser = client.get_model('User')(username=username)
user = client.user.addUser(user=luser).result().user

privkey2 = bitjws.PrivateKey()
my_pubkey2 = privkey2.pubkey.serialize()
my_address2 = bitjws.pubkey_to_addr(my_pubkey2)
username2 = str(my_address2)[0:8]
client2 = BitJWSSwaggerClient.from_spec(load_file(specurl), origin_url=url)
luser2 = client2.get_model('User')(username=username2)
user2 = client2.user.addUser(user=luser2).result().user

def test_address():
    addy = client.get_model('Address')(currency='BTC', network='Internal')
    address = client.address.createAddress(address=addy).result()
    assert hasattr(address, 'id')
    assert address.user.id == user.id

    addresses = client.address.getAddress().result()
    assert len(addresses) == 1

    gotaddy = client.address.getAddress(address=addy).result()
    assert gotaddy[0] == address


def test_get_balance():
    balances = client.balance.getBalance().result()
    for bal in balances:
        assert hasattr(bal, 'id')
        assert hasattr(bal, 'total')
        assert hasattr(bal, 'available')
        assert bal.total == 0
        assert bal.available == 0
        assert bal.user.id == user.id


def test_money_cycle():
    fee = Amount("%s BTC" % CFG.get('internal', 'FEE'))
    amount = Amount("%s BTC" % 0.01)
    # Receive Internal to user
    addy = client.get_model('Address')(currency='BTC', network='Internal')
    address = client.address.createAddress(address=addy).result()
    internal_credit(address.address, amount + fee)

    for i in range(0, 60):
        c = ses.query(wm.Credit).filter(wm.Credit.address == address.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.address == address.address
    assert c.amount == amount + fee
    assert c.currency == 'BTC'
    assert c.network == 'Internal'
    assert len(c.ref_id) > 0

    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.total > Amount("0 BTC")
    assert bal.available == Amount("0 BTC")
    bal.available = bal.available + c.amount
    ses.add(bal)
    try:
        ses.commit()
    except Exception as e:
        ses.rollback()
        print "skipping test"
        return
    ses.close()
    # send Internal internally to user 2
    addy = client2.get_model('Address')(currency='BTC', network='Internal')
    address = client2.address.createAddress(address=addy).result()

    debit = client.debit.sendMoney(debit={'amount': 0.01,
                                  'fee': fee.to_double(),
                                  'address': address.address,
                                  'currency': 'BTC',
                                  'network': 'Internal',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money internal internal',
                                  'ref_id': ''}).result()
    assert debit.state == 'complete'
    assert debit.amount == 0.01
    assert debit.reference == 'test send money internal internal'
    assert debit.network == 'internal'

    for i in range(0, 60):
        c = ses.query(wm.Credit).filter(wm.Credit.address == address.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.state == 'complete'
    assert c.amount == Amount("0.01 BTC")
    assert c.reference == 'test send money internal internal'
    assert c.network == 'internal'
    assert int(debit.ref_id) == c.id
    assert int(c.ref_id) == debit.id
    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.total == Amount("0 BTC")
    assert bal.available == Amount("0 BTC")

    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user2.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.total == Amount("0.01 BTC")
    assert bal.available == Amount("0.01 BTC")
    ses.close()
    # send BTC internally to user 2
    addy = client2.get_model('Address')(currency='BTC', network='Internal')
    address = client2.address.createAddress(address=addy).result()

    debit = client2.debit.sendMoney(debit={'amount': 0.0099,
                                  'fee': CFG.get('internal', 'FEE'),
                                  'address': address.address,
                                  'currency': 'BTC',
                                  'network': 'Internal',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money internal internal',
                                  'ref_id': ''}).result()
    assert debit.state == 'complete'
    assert debit.amount == 0.0099
    assert debit.reference == 'test send money internal internal'
    assert debit.network == 'internal'

    for i in range(0, 60):
        c = ses.query(wm.Credit).filter(wm.Credit.address == address.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.state == 'complete'
    assert c.amount == Amount("0.0099 BTC")
    assert c.reference == 'test send money internal internal'
    assert c.network == 'internal'
    assert int(debit.ref_id) == c.id
    assert int(c.ref_id) == debit.id
    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.total == Amount("0 BTC")
    assert bal.available == Amount("0 BTC")

    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user2.id).filter(wm.Balance.currency == 'BTC').first()
    assert bal.total == Amount("0.0099 BTC")
    assert bal.available == Amount("0.0099 BTC")
    ses.close()
    # Send Internal from user2
    addy = internal_address()
    debit = client2.debit.sendMoney(debit={'amount': 0.0098,
                                   'fee': CFG.get('internal', 'FEE'),
                                  'address': addy,
                                  'currency': 'BTC',
                                  'network': 'Internal',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money internal',
                                  'ref_id': ''}).result()
    time.sleep(0.1)
    for i in range(0, 60):
        d = ses.query(wm.Debit).filter(wm.Debit.address == addy).first()
        if d is not None:
            break
        else:
            time.sleep(1)
    assert d is not None

    assert d.address == addy
    assert d.amount == Amount("0.0098 BTC")
    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user2.id).filter(wm.Balance.currency == 'BTC')
    assert bal.first().total == Amount("0 BTC")
    assert bal.first().available == Amount("0 BTC")


def test_get_credits():
    # generate lots of credits
    by_id = None
    by_address = None
    by_ref_id = None
    for i in range(30):
        addy = client.get_model('Address')(currency='BTC', network='Internal')
        address = client.address.createAddress(address=addy).result()
        c = internal_credit(address.address, Amount("0.01 BTC"))
        if i == 1:
            by_id = c.id
        elif i == 2:
            by_address = address.address
        elif i == 3:
            by_ref_id = c.ref_id

    # find all
    creds = client.search.searchCredits().result()
    assert len(creds) == 10

    # find second page
    creds2 = client.search.searchCredits(searchcd={'page': 1}).result()
    assert len(creds2) == 10
    # assure that there is no overlap
    for c2 in creds2:
        for c in creds:
            assert c.id != c2.id

    # find third page
    creds3 = client.search.searchCredits(searchcd={'page': 2}).result()
    assert len(creds3) == 10
    # assure that there is no overlap
    for c3 in creds3:
        for c in creds:
            assert c.id != c3.id
        for c2 in creds2:
            assert c2.id != c3.id

    # find by address
    creds = client.search.searchCredits(searchcd={'address': by_address}).result()
    assert len(creds) == 1
    assert creds[0].address == by_address

    # find by ref_id
    creds = client.search.searchCredits(searchcd={'ref_id': by_ref_id}).result()
    assert len(creds) == 1
    assert creds[0].ref_id == by_ref_id

    # find by id
    creds = client.search.searchCredits(searchcd={'id': by_id}).result()
    assert len(creds) == 1
    assert creds[0].id == by_id


def test_get_debits():
    # generate a big credit
    addy = client.get_model('Address')(currency='BTC', network='Internal')
    address = client.address.createAddress(address=addy).result()
    c = internal_credit(address.address, Amount("1 BTC"))
    bal = ses.query(wm.Balance).filter(wm.Balance.user_id == user.id).filter(wm.Balance.currency == 'BTC').first()
    bal.available = bal.available + c.amount
    ses.add(bal)
    try:
        ses.commit()
    except Exception as e:
        ses.rollback()
        print "skipping test"
        return

    # send lots of debits
    by_id = None
    by_address = None
    for i in range(30):
        addy = client2.get_model('Address')(currency='BTC', network='Internal')
        address = client2.address.createAddress(address=addy).result()
        debit = client.debit.sendMoney(debit={'amount': 0.01,
                                        'fee': CFG.get('internal', 'FEE'),
                                       'address': address.address,
                                       'currency': 'BTC',
                                       'network': 'Internal',
                                       'state': 'unconfirmed',
                                       'reference': 'test get debits',
                                       'ref_id': ''}).result()
        if i == 1:
            by_id = debit.id
        elif i == 2:
            by_address = address.address

    time.sleep(0.2) # db write time... should really check to avoid race

    # find all
    debs = client.search.searchDebits().result()
    assert len(debs) >= 10


    # find second page
    debs2 = client.search.searchDebits(searchcd={'page': 1}).result()
    assert len(debs2) == 10
    # assure that there is no overlap
    for d2 in debs2:
        for d in debs:
            assert d.id != d2.id

    # find third page
    debs3 = client.search.searchDebits(searchcd={'page': 2}).result()
    assert len(debs3) == 10
    # assure that there is no overlap
    for d3 in debs3:
        for d in debs:
            assert d.id != d3.id
        for d2 in debs2:
            assert d2.id != d3.id

    # find by address
    debs = client.search.searchDebits(searchcd={'address': by_address}).result()
    assert len(debs) == 1
    assert debs[0].address == by_address

    # find by id
    debs = client.search.searchDebits(searchcd={'id': by_id}).result()
    assert len(debs) == 1
    assert debs[0].id == by_id


def test_get_network():
    network = client.network.getinfo(network='Internal').result()
    assert network.isenabled
    assert network.available == 1000
    assert network.fee == 0.0001

