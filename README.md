# Shared Wallet

A shared wallet server, for maintaining a centralized ledger of accounts. Accounts can transfer amounts to each other, deposit and withdraw. Currently supports [Bitcoin](http://bitcoin.org) and [Dash](http://dash.org).

# REST + Bitjws + Swagger

This server provides a REST API for operation as a service. The authentication is done using [bitjws](http://github.com/deginner/bitjws).

# Plugins

This package is practically useless without installing one or more wallet plugins. The only wallet backend that it comes with is a mockup. Currently supported plugins are: [desw-bitcoin](http://github.com/deginner/desw-bitcoin) and [desw-dash](http://github.com/deginner/desw-dash).

### Bitcoin Examples

For the sake of an example, we'll assume you're starting with the desw-bitcoin plugin, and that you're using Deginner's [bravado-bitjws](http://github.com/deginner/bravado-bitjws) Python client.

##### Register a new user

``` Python
luser = client.get_model('User')(username=username)
user = client.user.addUser(user=luser).result().user
```

##### Get an address

``` Python
addy = client.get_model('Address')(currency='BTC', network='Bitcoin')
address = client.address.createAddress(address=addy).result()
```

##### Get your balances

``` Python
balances = client.balance.getBalance().result()
```

##### Send coins

``` Python
addy = "1Go7y9ZQE3fzkHwWE89n4SbRo1GMEZonLN"
debit = client.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                              'address': addy,
                              'currency': 'BTC',
                              'network': 'Bitcoin',
                              'state': 'unconfirmed', #ignored
                              'reference': 'test send money BTC internal',
                              'ref_id': ''}).result()
```
