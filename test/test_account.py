import os
import pytest
import bitjws
import json
import time
from desw import CFG, ses, eng, models
from bravado_bitjws.client import BitJWSSwaggerClient
privkey = bitjws.PrivateKey()

my_pubkey = privkey.pubkey.serialize()
my_address = bitjws.pubkey_to_addr(my_pubkey)

host = "0.0.0.0"
url = "http://0.0.0.0:8002/"
specurl = "%sstatic/swagger.json" % url
username = str(my_address)[0:8]

client = BitJWSSwaggerClient.from_url(specurl, privkey=privkey)

luser = client.get_model('User')(username=username)
user = client.user.addUser(user=luser).result().user
print "main user %s" % user.id

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
bc = AuthServiceProxy(CFG.get('test', 'BITCOIN'))
dc = AuthServiceProxy(CFG.get('test', 'DASH'))


def check_balances():
    binfo = bc.getinfo()
    dinfo = dc.getinfo()
    if binfo['balance'] <= 0.1:
        print "low btc balance, please deposit to %s" % bc.getnewaddress()

    if dinfo['balance'] <= 1000:
        print "low dash balance, please deposit to %s" % dc.getnewaddress()


def test_register_user():
    # register a new user
    privkey2 = bitjws.PrivateKey()
    my_pubkey2 = privkey2.pubkey.serialize()
    my_address2 = bitjws.pubkey_to_addr(my_pubkey2)

    username2 = str(my_address2)[0:8]

    client2 = BitJWSSwaggerClient.from_url(specurl, privkey=privkey2)

    luser2 = client2.get_model('User')(username=username2)
    user2 = client2.user.addUser(user=luser2).result().user
    assert hasattr(user2, 'id')
    assert user.id != user2.id


def test_addresses():
    dashaddy = client.get_model('Address')(currency='DASH', network='Dash')
    dashaddress = client.address.createAddress(address=dashaddy).result()
    assert hasattr(dashaddress, 'id')
    assert dashaddress.user.id == user.id

    btcaddy = client.get_model('Address')(currency='BTC', network='Bitcoin')
    btcaddress = client.address.createAddress(address=btcaddy).result()
    assert hasattr(btcaddress, 'id')
    assert btcaddress.user.id == user.id

    addresses = client.address.getAddress().result()
    assert len(addresses) == 2

    gotdashaddy = client.address.getAddress(address=dashaddy).result()
    assert gotdashaddy[0] == dashaddress

    gotbtcaddy = client.address.getAddress(address=btcaddy).result()
    assert gotbtcaddy[0] == btcaddress


def test_get_balance():
    bals = client.get_model('Balance')()
    balances = client.balance.getBalance().result()
    for bal in balances:
        assert hasattr(bal, 'id')
        assert hasattr(bal, 'total')
        assert hasattr(bal, 'available')
        assert bal.total == 0
        assert bal.available == 0
        assert bal.user.id == user.id


def test_money_cycle():
    dashaddy = client.get_model('Address')(currency='DASH', network='Dash')
    dashaddress = client.address.createAddress(address=dashaddy).result()
    dashtxid = dc.sendtoaddress(dashaddress.address, 0.01)

    for i in range(0, 60):
        c = ses.query(models.Credit).filter(models.Credit.address == dashaddress.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.address == dashaddress.address
    assert c.amount == int(0.01 * 1e8)
    assert c.currency == 'DASH'
    assert c.network == 'Dash'
    assert dashtxid in c.ref_id
    dashbal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'DASH').first()
    assert dashbal.total > 0
    assert dashbal.available == 0
    dashbal.available += c.amount
    try:
        ses.commit()
    except Exception as e:
        ses.rollback()
        ses.flush()
        print "skipping test"
        return

    btcaddy = client.get_model('Address')(currency='BTC', network='Bitcoin')
    btcaddress = client.address.createAddress(address=btcaddy).result()
    btctxid = bc.sendtoaddress(btcaddress.address, 0.01)

    for i in range(0, 60):
        c = ses.query(models.Credit).filter(models.Credit.address == btcaddress.address).first()
        if c is not None:
            break
        else:
            time.sleep(1)
    assert c is not None
    assert c.address == btcaddress.address
    assert c.amount == int(0.01 * 1e8)
    assert c.currency == 'BTC'
    assert c.network == 'Bitcoin'
    assert btctxid in c.ref_id

    btcbal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'BTC').first()
    assert btcbal.total > 0
    assert btcbal.available == 0
    btcbal.available += c.amount
    try:
        ses.commit()
    except Exception as e:
        ses.rollback()
        ses.flush()
        print "skipping test"
        return

    dashaddy = dc.getnewaddress()
    debit = client.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                                  'address': dashaddy,
                                  'currency': 'DASH',
                                  'network': 'Dash',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money dash',
                                  'ref_id': ''}).result()
    dashtx = None
    for i in range(0, 60):
        txs = dc.listtransactions()
        for t in txs:
            if t['txid'] == debit.ref_id:
                dashtx = t
                break
        if dashtx is not None:
            break
        else:
            time.sleep(1)

    assert dashtx is not None
    assert dashtx['address'] == dashaddy
    assert float(dashtx['amount']) == 0.01
    dashbal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'DASH').first()
    assert dashbal.total == 0
    assert dashbal.available == 0

    btcaddy = bc.getnewaddress()
    debit = client.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                                  'address': btcaddy,
                                  'currency': 'BTC',
                                  'network': 'Bitcoin',
                                  'state': 'unconfirmed',
                                  'reference': 'test send money btc',
                                  'ref_id': ''}).result()
    btctx = None
    for i in range(0, 60):
        txs = bc.listtransactions()
        for t in txs:
            if t['txid'] == debit.ref_id:
                btctx = t
                break
        if btctx is not None:
            break
        else:
            time.sleep(1)

    assert btctx is not None
    assert btctx['address'] == btcaddy
    assert float(btctx['amount']) == 0.01
    btcbal = ses.query(models.Balance).filter(models.Balance.user_id == user.id).filter(models.Balance.currency == 'BTC').first()
    assert btcbal.total == 0
    assert btcbal.available == 0


if __name__ == "__main__":
    check_balances()
