from collections.abc import Callable
from typing import Any

from .subscription import SubscribedTransaction

EventListener = Callable[[SubscribedTransaction, str], None]
"""
A function that takes a SubscribedTransaction and the event name.
"""


class EventEmitter:
    """
    A simple event emitter that allows for the registration of event listeners and the
    emission of events to those listeners.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[EventListener]] = {}
        self._one_time_listeners: dict[str, list[EventListener]] = {}

    def emit(self, event_name: str, event: Any) -> None:  # noqa: ANN401
        """
        Emits an event to all listeners registered for the event name.
        """
        if event_name in self._listeners:
            for listener in self._listeners[event_name]:
                listener(event, event_name)
                if event_name in self._one_time_listeners:
                    self._listeners[event_name].remove(listener)
                    self._one_time_listeners[event_name].remove(listener)

    def on(self, event_name: str, listener: EventListener) -> "EventEmitter":
        """
        Registers a listener for the given event name.
        """
        if event_name not in self._listeners:
            self._listeners[event_name] = []

        self._listeners[event_name].append(listener)
        return self

    def once(self, event_name: str, listener: EventListener) -> "EventEmitter":
        """
        Registers a listener for the given event name that will only be called once.
        """
        if event_name not in self._one_time_listeners:
            self._one_time_listeners[event_name] = []

        self._one_time_listeners[event_name].append(listener)

        return self.on(event_name, listener)

    def remove_listener(
        self, event_name: str, listener: EventListener
    ) -> "EventEmitter":
        """
        Removes a listener for the given event name.
        """
        if event_name in self._listeners:
            self._listeners[event_name].remove(listener)

        if event_name in self._one_time_listeners:
            self._one_time_listeners[event_name].remove(listener)

        return self

    off = remove_listener
