import argparse
import os
import sys
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from desw import CFG, models, ses, eng

CONFS = 5  # TODO move to config
# TODO separate logger from flask one


def getNewAddress():
    client = AuthServiceProxy(CFG.get('plugins', 'DASH'))
    return client.getnewaddress()


def validateAddress(address):
    return address[0:1] in 'XxYy'


def sendToAddress(address, amount):
    client = AuthServiceProxy(CFG.get('plugins', 'DASH'))
    return client.sendtoaddress(address, amount)


def confirmSend(txid, details):
    debit = ses.query(models.Debit).filter(models.Debit.address == details['address']).filter(models.Debit.amount == details['amount']).filter(models.Debit.state == 'unconfirmed').first()
    if not debit:
        print "debit already confirmed or address unknown. returning."
        return
    debit.state = 'complete'
    try:
        ses.commit()
    except Exception as ie:
        print ie
        ses.rollback()
        ses.flush()


def processReceive(txid, details, confirmed=False):
    c = ses.query(models.Credit).filter(models.Credit.ref_id == txid)
    if c.count() > 0:
        print "txid already known. returning."
        return
    state = 'complete' if confirmed else 'unconfirmed'
    addy = ses.query(models.Address).filter(models.Address.address == details['address']).first()
    if not addy:
        print "address not known. returning."
        return
    amount = int(float(details['amount']) * 1e8)
    print "crediting txid %s" % txid
    credit = models.Credit(amount=amount, address=details['address'], currency='DASH', network="Dash", state=state, reference='tx received', ref_id=txid, user_id=addy.user_id)
    ses.add(credit)
    bal = ses.query(models.Balance).filter(models.Balance.user_id == addy.user_id).filter(models.Balance.currency == 'DASH').order_by(models.Balance.time.desc()).first()
    if state == 'complete':
        bal.available += amount
    bal.total += amount
    try:
        ses.commit()
    except Exception as ie:
        print ie
        ses.rollback()
        ses.flush()


def main(sys_args=sys.argv[1:]):
    client = AuthServiceProxy(CFG.get('plugins', 'DASH'))
    parser = argparse.ArgumentParser()
    parser.add_argument("type")
    parser.add_argument("data")
    args = parser.parse_args(sys_args)
    typ = args.type
    if typ == 'transaction' and args.data is not None:
        txid = args.data
        txd = client.gettransaction(txid)
        txtype = None
        for p, put in enumerate(txd['details']):
            if put['category'] == 'send':
                confirmSend("%s:%s" % (txid, p), put)
            elif put['category'] == 'receive':
                processReceive("%s:%s" % (txid, p), put, (txd['confirmations'] >= CONFS or txd['bcconfirmations'] >= CONFS))

    elif typ == 'block' and args.data is not None:
        bhash = args.data
        


if __name__ == "__main__":
    main()

