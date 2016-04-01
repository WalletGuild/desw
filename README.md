# Shared Wallet

A shared wallet server, for maintaining a centralized ledger of accounts. Accounts can transfer amounts to each other, deposit and withdraw.

## Message Queue
This server publishes events to an [AMQP](http://www.amqp.org/) queue. Some of these events are published via the [SockJS-mq-server](https://bitbucket.org/deginner/sockjs-mq-server), while others are consumed by servers subscribed to wallet events.
