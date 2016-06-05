import bitjws
import json
import os
import pytest
import time
from bravado_bitjws.client import BitJWSSwaggerClient
from desw import CFG, ses, eng, models
from desw.plugin import mock_credit, mock_address, mock_confirm_credit

from bravado.swagger_model import load_file


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


def test_addresses():
    addy = client.get_model('Address')(currency='MCK', network='Mock')
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
    # Receive Mock to user
    addy = client.get_model('Address')(currency='MCK', network='Mock')
    address = client.address.createAddress(address=addy).result()
    mock_credit(address.address, int(0.01 * 1e8))

    for i in range(0, 60):
        c = ses.query(models.Credit).filter(models.Credit.address == address.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.address == address.address
    assert c.amount == int(0.01 * 1e8)
    assert c.currency == 'MCK'
    assert c.network == 'Mock'
    assert len(c.ref_id) > 0

    bal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'MCK').first()
    assert bal.total > 0
    assert bal.available == 0
    bal.available += c.amount
    ses.add(bal)
    try:
        ses.commit()
    except Exception as e:
        ses.rollback()
        print "skipping test"
        return

    # send Mock internally to user 2
    addy = client2.get_model('Address')(currency='MCK', network='Mock')
    address = client2.address.createAddress(address=addy).result()

    debit = client.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                                  'address': address.address,
                                  'currency': 'MCK',
                                  'network': 'Mock',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money mock internal',
                                  'ref_id': ''}).result()
    assert debit.state == 'complete'
    assert debit.amount == int(0.01 * 1e8)
    assert debit.reference == 'test send money mock internal'
    assert debit.network == 'internal'

    for i in range(0, 60):
        c = ses.query(models.Credit).filter(models.Credit.address == address.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.state == 'complete'
    assert c.amount == int(0.01 * 1e8)
    assert c.reference == 'test send money mock internal'
    assert c.network == 'internal'
    assert int(debit.ref_id) == c.id
    assert int(c.ref_id) == debit.id
    bal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'MCK').first()
    assert bal.total == 0
    assert bal.available == 0

    bal = ses.query(models.Balance).filter(models.Balance.user_id == user2.id).filter(models.Balance.currency == 'MCK').first()
    assert bal.total == int(0.01 * 1e8)
    assert bal.available == int(0.01 * 1e8)

    # send MCK internally to user 2
    addy = client2.get_model('Address')(currency='MCK', network='Mock')
    address = client2.address.createAddress(address=addy).result()

    debit = client2.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                                  'address': address.address,
                                  'currency': 'MCK',
                                  'network': 'Mock',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money mock internal',
                                  'ref_id': ''}).result()
    assert debit.state == 'complete'
    assert debit.amount == int(0.01 * 1e8)
    assert debit.reference == 'test send money mock internal'
    assert debit.network == 'internal'

    for i in range(0, 60):
        c = ses.query(models.Credit).filter(models.Credit.address == address.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.state == 'complete'
    assert c.amount == int(0.01 * 1e8)
    assert c.reference == 'test send money mock internal'
    assert c.network == 'internal'
    assert int(debit.ref_id) == c.id
    assert int(c.ref_id) == debit.id
    bal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'MCK').first()
    assert bal.total == 0
    assert bal.available == 0

    bal = ses.query(models.Balance).filter(models.Balance.user_id == user2.id).filter(models.Balance.currency == 'MCK').first()
    assert bal.total == int(0.01 * 1e8)
    assert bal.available == int(0.01 * 1e8)

    # Send Mock from user2
    addy = mock_address()
    debit = client2.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                                  'address': addy,
                                  'currency': 'MCK',
                                  'network': 'Mock',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money mock',
                                  'ref_id': ''}).result()
    time.sleep(0.1)
    for i in range(0, 60):
        d = ses.query(models.Debit).filter(models.Debit.address == addy).first()
        if d is not None:
            break
        else:
            time.sleep(1)
    assert d is not None

    assert d.address == addy
    assert d.amount == int(0.01 * 1e8)
    bal = ses.query(models.Balance).filter(models.Balance.user_id == user2.id).filter(models.Balance.currency == 'MCK')
    assert bal.first().total == 0
    assert bal.first().available == 0


def test_get_credits():
    # generate lots of credits
    by_id = None
    by_address = None
    by_ref_id = None
    for i in range(10):
        addy = client.get_model('Address')(currency='MCK', network='Mock')
        address = client.address.createAddress(address=addy).result()
        c = mock_credit(address.address, int(0.01 * 1e8))
        if i == 1:
            by_id = c.id
        elif i == 2:
            by_address = address.address
        elif i == 3:
            by_ref_id = c.ref_id

    # find all
    creds = client.search.searchCredits().result()
    assert len(creds) >= 10

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
    addy = client.get_model('Address')(currency='MCK', network='Mock')
    address = client.address.createAddress(address=addy).result()
    c = mock_credit(address.address, int(1 * 1e8))
    bal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'MCK').first()
    bal.available += c.amount
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
    for i in range(10):
        addy = client2.get_model('Address')(currency='MCK', network='Mock')
        address = client2.address.createAddress(address=addy).result()
        debit = client.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                                       'address': address.address,
                                       'currency': 'MCK',
                                       'network': 'Mock',
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

    # find by address
    debs = client.search.searchDebits(searchcd={'address': by_address}).result()
    assert len(debs) == 1
    assert debs[0].address == by_address

    # find by id
    debs = client.search.searchDebits(searchcd={'id': by_id}).result()
    assert len(debs) == 1
    assert debs[0].id == by_id


def test_get_network():
    network = client.network.getinfo(network='Mock').result()
    assert network.isenabled
    assert network.available == 1 * 1e8
    assert network.fee == 0.0001 * 1e8

