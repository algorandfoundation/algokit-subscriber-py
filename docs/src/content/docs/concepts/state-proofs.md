---
title: State Proof Support
description: Subscribe to state proof transactions using algokit-subscriber.
---

You can subscribe to [state proof](https://dev.algorand.co/concepts/protocol/stateproofs) transactions using this subscriber library. At the time of writing state proof transactions are not supported by algosdk v2 and custom handling has been added to ensure this valuable type of transaction can be subscribed to.

The field level documentation of the [returned state proof transaction](../../guide/subscriptions/#subscribedtransaction) follows the Algorand Indexer transaction model.

By exposing this functionality, this library can be used to create a [light client](https://dev.algorand.co/concepts/protocol/stateproofs).