import sqlalchemy as sa
import sqlalchemy.orm as orm
from flask.ext.login import UserMixin
from sqlalchemy_login_models.model import Base, UserKey, User as SLM_User
import datetime


__all__ = ['Balance', 'Address', 'Credit', 'Debit', 'HWBalance']


class Balance(Base):
    """A user's balance in a single currency. Only the latest record is valid."""
    __tablename__ = "balance"
    __name__ = "balance"

    id = sa.Column(sa.Integer, primary_key=True, doc="primary key")
    total = sa.Column(sa.BigInteger, nullable=False)
    available = sa.Column(sa.BigInteger, nullable=False)
    currency = sa.Column(sa.String(4), nullable=False)  # i.e. BTC, DASH, USDT
    time = sa.Column(sa.DateTime(), default=datetime.datetime.utcnow)
    reference = sa.Column(sa.String(256), nullable=True)

    # foreign key reference to the owner of this
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('user.id'),
        nullable=False)
    user = orm.relationship("User", foreign_keys=[user_id])

    def __init__(self, total, available, currency, reference, user_id):
        self.total = total
        self.available = available
        self.currency = currency
        self.reference = reference
        self.user_id = user_id


class Address(Base):
    """A payment network Address or account number."""
    __tablename__ = "address"
    __name__ = "address"

    id = sa.Column(sa.Integer, primary_key=True, doc="primary key")
    address = sa.Column(sa.String(64), nullable=False)  # i.e. 1PkzTWAyfR9yoFw2jptKQ3g6E5nKXPsy8r, 	XhwWxABXPVG5Z3ePyLVA3VixPRkARK6FKy
    currency = sa.Column(sa.String(4), nullable=False)  # i.e. BTC, DASH, USDT
    network = sa.Column(sa.String(64), nullable=False)  # i.e. Bitcoin, Dash, Crypto Capital
    state = sa.Column(sa.Enum("pending", "active", "blocked"), nullable=False)

    # foreign key reference to the owner of this
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('user.id'),
        nullable=False)
    user = orm.relationship("User", foreign_keys=[user_id])

    def __init__(self, address, currency, network, state, user_id):
        self.address = address
        self.currency = currency
        self.network = network
        self.state = state
        self.user_id = user_id


class Credit(Base):
    """A Credit, which adds tokens to a User's Balance."""
    __tablename__ = "credit"
    __name__ = "credit"

    id = sa.Column(sa.Integer, primary_key=True, doc="primary key")
    amount = sa.Column(sa.BigInteger, nullable=False)
    address = sa.Column(sa.String(64), nullable=False)  # i.e. 1PkzTWAyfR9yoFw2jptKQ3g6E5nKXPsy8r, XhwWxABXPVG5Z3ePyLVA3VixPRkARK6FKy
    currency = sa.Column(sa.String(4), nullable=False)  # i.e. BTC, DASH, USDT
    network = sa.Column(sa.String(64), nullable=False)  # i.e. Bitcoin, Dash, Crypto Capital
    state = sa.Column(sa.Enum("unconfirmed", "complete", "error"), nullable=False)
    reference = sa.Column(sa.String(256), nullable=True)  # i.e. invoice#1
    ref_id = sa.Column(sa.String(256), nullable=False, unique=True)  # i.e. 4cef42f9ff334b9b11bffbd9da21da54176103d92c1c6e4442cbe28ca43540fd:0

    # foreign key reference to the owner of this
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('user.id'),
        nullable=False)
    user = orm.relationship("User", foreign_keys=[user_id])

    def __init__(self, amount, address, currency, network, state, reference, ref_id, user_id):
        self.amount = amount
        self.address = address
        self.currency = currency
        self.network = network
        self.state = state
        self.reference = reference
        self.ref_id = ref_id
        self.user_id = user_id


class Debit(Base):
    """A Debit, which subtracts tokens from a User's Balance."""
    __tablename__ = "debit"
    __name__ = "debit"

    id = sa.Column(sa.Integer, primary_key=True, doc="primary key")
    amount = sa.Column(sa.BigInteger, nullable=False)
    fee = sa.Column(sa.BigInteger, nullable=False)
    address = sa.Column(sa.String(64), nullable=False)  # i.e. 1PkzTWAyfR9yoFw2jptKQ3g6E5nKXPsy8r,  XhwWxABXPVG5Z3ePyLVA3VixPRkARK6FKy
    currency = sa.Column(sa.String(4), nullable=False)  # i.e. BTC, DASH, USDT
    network = sa.Column(sa.String(64), nullable=False)  # i.e. Bitcoin, Dash, Crypto Capital
    state = sa.Column(sa.Enum("unconfirmed", "complete", "error"), nullable=False)
    reference = sa.Column(sa.String(256), nullable=True)  # i.e. invoice#1
    ref_id = sa.Column(sa.String(256), nullable=False)  # i.e. 4cef42f9ff334b9b11bffbd9da21da54176103d92c1c6e4442cbe28ca43540fd

    # foreign key reference to the owner of this
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('user.id'),
        nullable=False)
    user = orm.relationship("User", foreign_keys=[user_id])

    def __init__(self, amount, fee, address, currency, network, state, reference, ref_id, user_id):
        self.amount = amount
        self.fee = fee
        self.address = address
        self.currency = currency
        self.network = network
        self.state = state
        self.reference = reference
        self.ref_id = ref_id
        self.user_id = user_id


class HWBalance(Base):
    """A Hot Wallet Balance, for internal use only"""
    __tablename__ = "hwbalance"
    __name__ = "hwbalance"

    id = sa.Column(sa.Integer, primary_key=True, doc="primary key")
    available = sa.Column(sa.BigInteger, nullable=False)
    total = sa.Column(sa.BigInteger, nullable=False)
    currency = sa.Column(sa.String(4), nullable=False)  # i.e. BTC, DASH, USDT
    network = sa.Column(sa.String(64), nullable=False)  # i.e. Bitcoin, Dash, Crypto Capital
    time = sa.Column(sa.DateTime(), default=datetime.datetime.utcnow)

    def __init__(self, available, total, currency, network):
        self.available = available
        self.total = total
        self.currency = currency
        self.network = network

