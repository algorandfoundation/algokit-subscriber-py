from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from algokit_abi.abi import ABIType
from algokit_indexer_client.models import Transaction

from algokit_subscriber._utils import method_selector_bytes


@dataclass(kw_only=True, slots=True)
class Arc28EventArg:
    """
    Represents an argument of an ARC-28 event.
    """

    type: str
    """The type of the argument"""

    name: str | None = None
    """An optional, user-friendly name for the argument"""

    desc: str | None = None
    """An optional, user-friendly description for the argument"""


@dataclass(kw_only=True)
class Arc28Event:
    """
    The definition of metadata for an ARC-28 event as per the ARC-28 specification.
    """

    name: str
    """The name of the event"""

    args: list[Arc28EventArg]
    """The arguments of the event, in order"""

    desc: str | None = None
    """An optional, user-friendly description for the event"""

    @cached_property
    def signature(self) -> str:
        """The signature of the event e.g. `EventName(type1,type2)`"""
        return f"{self.name}{self._tuple_str}"

    @cached_property
    def prefix(self) -> bytes:
        """The prefix for the event"""
        return method_selector_bytes(self.signature)

    @cached_property
    def abi_type(self) -> ABIType:
        """The ABI type of the event"""
        return ABIType.from_string(self._tuple_str)

    @cached_property
    def _tuple_str(self) -> str:
        args = ",".join(a.type for a in self.args)
        return f"({args})"


@dataclass(kw_only=True, slots=True)
class Arc28EventGroup:
    """
    Specifies a group of ARC-28 event definitions along with instructions for
    when to attempt to process the events.
    """

    group_name: str
    """The name to designate for this group of events."""

    events: list[Arc28Event] = field(default_factory=list)
    """The list of ARC-28 event definitions."""

    process_for_app_ids: list[int] | None = None
    """Optional list of app IDs that this group should apply to."""

    process_transaction: Callable[[Transaction], bool] | None = None
    """
    Optional predicate to indicate if these ARC-28 events should be processed
    for the given transaction.
    """

    continue_on_error: bool = False
    """
    Whether or not to silently (with warning log) continue if an error is
    encountered processing the ARC-28 event data; default = False.
    """


@dataclass(kw_only=True, slots=True)
class Arc28EventFilter:
    """
    A reference to an ARC-28 group and event, used to filter for transactions that emit it
    """

    group_name: str
    """The name of the ARC-28 event group the event belongs to"""

    event_name: str
    """The name of the ARC-28 event that was triggered"""


@dataclass(kw_only=True, slots=True)
class EmittedArc28Event:
    """
    Represents an ARC-28 event that was emitted.
    """

    group_name: str
    """The name of the ARC-28 event group the event belongs to"""

    event_name: str
    """The name of the ARC-28 event that was triggered"""

    event_signature: str
    """The signature of the event e.g. `EventName(type1,type2)`"""

    event_prefix: str
    """The 4-byte hex prefix for the event"""

    event_definition: Arc28Event
    """The ARC-28 definition of the event"""

    args: list[Any]
    """The ordered arguments extracted from the event that was emitted"""

    args_by_name: dict[str, Any]
    """
    The named arguments extracted from the event that was emitted (where the
    arguments had a name defined)
    """
