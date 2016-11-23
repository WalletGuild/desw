# Shared Wallet

A shared wallet server, for maintaining a centralized ledger of accounts. Accounts can transfer amounts to each other, deposit and withdraw. Currently supports [Bitcoin](http://bitcoin.org) and [Dash](http://dash.org).

# REST + Bitjws + Swagger

This server provides a REST API for operation as a service. The authentication is done using [bitjws](http://github.com/tappguild/bitjws).

# Installation

Just run `make install`. This will automatically install all prereqs
including ledger-cli and sepc256k1.

Also make will create data directories for storing your logs and
configuration files. Expected to run on *nux systems, these directories will be as follows.

| For           | Location               |
|---------------|------------------------|
| logs          | /var/log/desw  |
| configuration | /etc/tapp/desw |
| pids          | /var/run/              |

If and when you wish to change any configuration settings, edit
the .ini file in the configuration directory.

### Plugins

This package is practically useless without installing one or more wallet plugins. The only wallet backend that it comes with is a mockup. Currently supported plugins are: [desw-bitcoin](http://github.com/walletguild/desw-bitcoin) and [desw-dash](http://github.com/walletguild/desw-dash).

# Bitcoin Examples

For the sake of an example, we'll assume you're starting with the desw-bitcoin plugin, and that you're using [bravado-bitjws](http://github.com/tappguild/bravado-bitjws) Python client.

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
debit = client.debit.sendMoney(debit={'amount': 0.01,
                              'address': addy,
                              'currency': 'BTC',
                              'network': 'Bitcoin',
                              'state': 'unconfirmed', #ignored
                              'reference': 'test send money BTC external',
                              'ref_id': ''}).result()
```
