from collections.abc import Callable
from typing import Any, TypedDict

from typing_extensions import NotRequired  # noqa: UP035

from .indexer import TransactionResult


class Arc28EventArg(TypedDict):
    """
    Represents an argument of an ARC-28 event.
    """

    type: str
    """The type of the argument"""

    name: NotRequired[str]
    """An optional, user-friendly name for the argument"""

    desc: NotRequired[str]
    """An optional, user-friendly description for the argument"""


class Arc28Event(TypedDict):
    """
    The definition of metadata for an ARC-28 event as per the ARC-28 specification.
    """

    name: str
    """The name of the event"""

    desc: NotRequired[str]
    """An optional, user-friendly description for the event"""

    args: list[Arc28EventArg]
    """The arguments of the event, in order"""


class Arc28EventGroup(TypedDict):
    """
    Specifies a group of ARC-28 event definitions along with instructions for when to attempt to process the events.
    """

    group_name: str
    """The name to designate for this group of events."""

    process_for_app_ids: list[int]
    """Optional list of app IDs that this event should apply to."""

    process_transaction: NotRequired[Callable[[TransactionResult], bool]]
    """Optional predicate to indicate if these ARC-28 events should be processed for the given transaction."""

    continue_on_error: bool
    """Whether or not to silently (with warning log) continue if an error is encountered processing the ARC-28 event data; default = False."""

    events: list[Arc28Event]
    """The list of ARC-28 event definitions."""


class Arc28EventToProcess(TypedDict):
    """
    Represents an ARC-28 event to be processed.
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


class EmittedArc28Event(Arc28EventToProcess):
    """
    Represents an ARC-28 event that was emitted.
    """

    args: list[Any]
    """The ordered arguments extracted from the event that was emitted"""

    args_by_name: dict[str, Any]
    """The named arguments extracted from the event that was emitted (where the arguments had a name defined)"""
