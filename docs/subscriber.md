# `AlgorandSubscriber`

`AlgorandSubscriber` is a class that allows you to easily subscribe to the Algorand Blockchain, define a series of events that you are interested in, and react to those events.

## Creating a subscriber

To create an {py:class}`~algokit_subscriber.AlgorandSubscriber` you can use the constructor, passing in an {py:class}`~algokit_subscriber.AlgorandSubscriberConfig`:

```python
import algokit_subscriber as sub
from algokit_utils import AlgorandClient

algorand = AlgorandClient.testnet()

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="my-filter",
                type="pay",
                sender="ABC...",
            ),
        ],
        watermark_persistence=sub.in_memory_watermark(),
        sync_behaviour="skip-sync-newest",
    ),
    algod_client=algorand.client.algod,
)
```

See the full API reference for:
- {py:class}`~algokit_subscriber.AlgorandSubscriber` - the subscriber class
- {py:class}`~algokit_subscriber.AlgorandSubscriberConfig` - the configuration dataclass

## Subscribing to events

Once you have created the `AlgorandSubscriber`, you can register handlers/listeners for the filters you have defined, or each poll as a whole batch.

You can do this via the following methods:

- {py:meth}`~algokit_subscriber.AlgorandSubscriber.on` - Register an event handler to run on every subscribed transaction matching the given filter name
- {py:meth}`~algokit_subscriber.AlgorandSubscriber.on_batch` - Register an event handler to run on all subscribed transactions matching the given filter name for each subscription poll
- {py:meth}`~algokit_subscriber.AlgorandSubscriber.on_before_poll` - Register an event handler to run before each subscription poll
- {py:meth}`~algokit_subscriber.AlgorandSubscriber.on_poll` - Register an event handler to run after each subscription poll
- {py:meth}`~algokit_subscriber.AlgorandSubscriber.on_error` - Register an event handler to run when an error occurs

When you define an event listener it will be called, one-by-one in the order the registrations occur.

If you call `on_batch` it will be called first, with the full set of transactions that were found in the current poll (0 or more). Following that, each transaction in turn will then be passed to the listener(s) that subscribed with `on` for that event.

The default type that will be received is a {py:class}`~algokit_subscriber.SubscribedTransaction`, which is a dataclass that extends the indexer `Transaction` model with additional fields like `filters_matched`, `arc28_events`, `balance_changes`, and `parent_transaction_id`.

See the [detail about this type](subscriptions.md#subscribedtransaction).

Alternatively, if you defined a mapper against the filter then it will be applied before passing the objects through.

If you call `on_poll` it will be called last (after all `on` and `on_batch` listeners) for each poll, with the full set of transactions for that poll and [metadata about the poll result](./subscriptions.md#transactionsubscriptionresult). This allows you to process the entire poll batch in one transaction or have a hook to call after processing individual listeners (e.g. to commit a transaction).

If you want to run code before a poll starts (e.g. to log or start a transaction) you can do so with `on_before_poll`.

## Poll the chain

There are two methods to poll the chain for events:

- {py:meth}`~algokit_subscriber.AlgorandSubscriber.poll_once` - Execute a single subscription poll and return the result
- {py:meth}`~algokit_subscriber.AlgorandSubscriber.start` - Start the subscriber in a loop until `stop` is called

`poll_once` is useful when you want to take control of scheduling the different polls, such as when running a Lambda on a schedule or a process via cron, etc. - it will do a single poll of the chain and return the result of that poll.

`start` is useful when you have a long-running process or container and you want it to loop infinitely at the specified polling frequency from the constructor config. If you want to inspect or log what happens under the covers you can pass in an `inspect` lambda that will be called for each poll.

If you use `start` then you can stop the polling by calling {py:meth}`~algokit_subscriber.AlgorandSubscriber.stop`, which will ensure everything is cleaned up nicely.

## Handling errors

To handle errors, you can register error handlers/listeners using the {py:meth}`~algokit_subscriber.AlgorandSubscriber.on_error` method. This works in a similar way to the other `on*` methods.

When no error listeners have been registered, a default listener is used to re-throw any exception, so they can be caught by global uncaught exception handlers.
Once an error listener has been registered, the default listener is removed and it's the responsibility of the registered error listener to perform any error handling.

## Examples

See the [main README](../README.md#examples).
