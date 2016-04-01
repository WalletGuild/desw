import pytest
import bitjws
import json
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


def test_create_address():
    dashaddy = client.get_model('Address')(currency='DASH', network='Dash')
    dashaddress = client.address.createAddress(address=dashaddy).result()
    assert hasattr(dashaddress, 'id')
    assert dashaddress.user.id == user.id

    btcaddy = client.get_model('Address')(currency='BTC', network='Bitcoin')
    btcaddress = client.address.createAddress(address=btcaddy).result()
    assert hasattr(btcaddress, 'id')
    assert btcaddress.user.id == user.id


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

