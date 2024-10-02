import time
from collections.abc import Callable
from typing import Any, cast

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from .subscription import get_subscribed_transactions
from .types.event_emitter import EventEmitter, EventListener
from .types.subscription import (
    AlgorandSubscriberConfig,
    TransactionSubscriptionParams,
    TransactionSubscriptionResult,
)
from .utils import logger


class AlgorandSubscriber:
    """
    A subscriber for Algorand transactions.
    """

    def __init__(
        self,
        config: AlgorandSubscriberConfig,
        algod_client: AlgodClient,
        indexer_client: IndexerClient | None = None,
    ):
        """
        Create a new `AlgorandSubscriber`.
        :param config: The subscriber configuration
        :param algod_client: An algod client
        :param indexer_client: An (optional) indexer client; only needed if `subscription.syncBehaviour` is `catchup-with-indexer`
        """
        self.algod = algod_client
        self.indexer = indexer_client
        self.config = config
        self.event_emitter = EventEmitter().on("error", self.default_error_handler)
        self.started = False
        self.stop_requested = False

        self.filter_names = [f["name"] for f in self.config["filters"]]

        if config["sync_behaviour"] == "catchup-with-indexer" and not indexer_client:
            raise ValueError(
                "Received sync behaviour of catchup-with-indexer, but didn't receive an indexer instance."
            )

    def default_error_handler(
        self, error: Any, _str: str | None = None  # noqa: ANN401
    ) -> None:
        raise error

    def poll_once(self) -> TransactionSubscriptionResult:
        """
        Execute a single subscription poll.
        """
        watermark = self.config["watermark_persistence"]["get"]() or 0
        current_round = cast(dict, self.algod.status())["last-round"]

        self.event_emitter.emit(
            "before:poll", {"watermark": watermark, "current_round": current_round}
        )

        poll_result = get_subscribed_transactions(
            subscription=cast(
                TransactionSubscriptionParams,
                {"watermark": watermark, "current_round": current_round, **self.config},
            ),
            algod=self.algod,
            indexer=self.indexer,
        )

        try:
            for filter_name in self.filter_names:
                mapper = next(
                    (
                        f.get("mapper")
                        for f in self.config["filters"]
                        if f["name"] == filter_name
                    ),
                    None,
                )
                matched_transactions = [
                    t
                    for t in poll_result["subscribed_transactions"]
                    if filter_name in t.get("filters_matched", [])
                ]
                mapped_transactions = (
                    mapper(matched_transactions) if mapper else matched_transactions
                )

                self.event_emitter.emit(f"batch:{filter_name}", mapped_transactions)
                for transaction in mapped_transactions:
                    self.event_emitter.emit(filter_name, transaction)

            self.event_emitter.emit("poll", poll_result)
        except Exception as e:
            logger.info(f"Error processing event emittance: {e}")
            raise e

        self.config["watermark_persistence"]["set"](poll_result["new_watermark"])
        return poll_result

    def start(  # noqa: C901
        self, inspect: Callable | None = None, *, suppress_log: bool = False
    ) -> None:
        """
        Start the subscriber in a loop until `stop` is called.

        This is useful when running in the context of a long-running process / container.

        If you want to inspect or log what happens under the covers you can pass in an `inspect` callable that will be called for each poll.
        """
        if self.started:
            return
        self.started = True
        self.stop_requested = False

        while not self.stop_requested:
            start_time = time.time()
            try:
                result = self.poll_once()
                duration_in_seconds = time.time() - start_time

                if not suppress_log:
                    logger.info(
                        f"Subscription poll completed in {duration_in_seconds:.2f}s"
                    )
                    logger.info(f"Current round: {result['current_round']}")
                    logger.info(f"Starting watermark: {result['starting_watermark']}")
                    logger.info(f"New watermark: {result['new_watermark']}")
                    logger.info(f"Synced round range: {result['synced_round_range']}")
                    logger.info(
                        f"Subscribed transactions: {len(result['subscribed_transactions'])}"
                    )

                if inspect:
                    inspect(result)

                # Check if there was a stop requested during one of the event handlers or inspect
                if self.stop_requested:
                    break  # type: ignore[unreachable]

                if result["current_round"] > result[
                    "new_watermark"
                ] or not self.config.get("wait_for_block_when_at_tip", False):
                    sleep_time = self.config.get("frequency_in_seconds", 1)
                    if not suppress_log:
                        logger.info(f"Sleeping for {sleep_time}s")
                    time.sleep(sleep_time)
                else:
                    next_round = result["current_round"] + 1
                    if not suppress_log:
                        logger.info(f"Waiting for round {next_round}")
                    wait_start = time.time()
                    self.algod.status_after_block(result["current_round"])
                    if not suppress_log:
                        logger.info(
                            f"Waited for {time.time() - wait_start:.2f}s until next block"
                        )
            except Exception as e:
                self.event_emitter.emit("error", e)
        self.started = False

    def stop(self, reason: str | None = None) -> None:
        if not self.started:
            return
        self.stop_requested = True
        logger.info(f"Stopping subscriber: {reason}")

    def on(self, filter_name: str, listener: EventListener) -> "AlgorandSubscriber":
        """
        Register an event handler to run on every subscribed transaction matching the given filter name.
        """
        if filter_name == "error":
            raise ValueError(
                "'error' is reserved, please supply a different filter_name."
            )
        self.event_emitter.on(filter_name, listener)
        return self

    def on_batch(
        self, filter_name: str, listener: EventListener
    ) -> "AlgorandSubscriber":
        """
        Register an event handler to run on all subscribed transactions matching the given filter name
        for each subscription poll.
        """
        self.event_emitter.on(f"batch:{filter_name}", listener)
        return self

    def on_before_poll(self, listener: EventListener) -> "AlgorandSubscriber":
        """
        Register an event handler to run before each subscription poll.
        """
        self.event_emitter.on("before:poll", listener)
        return self

    def on_poll(self, listener: EventListener) -> "AlgorandSubscriber":
        """
        Register an event handler to run after each subscription poll.
        """
        self.event_emitter.on("poll", listener)
        return self

    def on_error(self, listener: EventListener) -> "AlgorandSubscriber":
        """
        Register an event handler to run when an error occurs.
        """
        self.event_emitter.off("error", self.default_error_handler)
        self.event_emitter.on("error", listener)
        return self
