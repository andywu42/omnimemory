"""
ModelOnexContainer - compatibility stub.

This is a local implementation of ModelOnexContainer until
omnibase_core.core.model_onex_container is available.
"""

from __future__ import annotations

from typing import Type, TypeVar, Dict, Any, Callable, Optional

T = TypeVar('T')


class ModelOnexContainer:
    """
    Simple dependency injection container for ONEX nodes.

    Provides singleton and transient registration patterns
    for service resolution.
    """

    def __init__(self) -> None:
        """Initialize the container with empty registries."""
        self._singletons: Dict[Type[Any], Any] = {}
        self._singleton_factories: Dict[Type[Any], Callable[[], Any]] = {}
        self._transient_factories: Dict[Type[Any], Callable[[], Any]] = {}

    def register_singleton(
        self,
        interface: Type[T],
        implementation: Type[T] | Callable[[], T],
    ) -> None:
        """
        Register a singleton service.

        The same instance will be returned for all resolve calls.

        Args:
            interface: The interface/protocol type to register
            implementation: The implementation class or factory function
        """
        if callable(implementation) and isinstance(implementation, type):
            # It's a class, create a factory
            self._singleton_factories[interface] = implementation
        else:
            # It's already a factory function
            self._singleton_factories[interface] = implementation

    def register_transient(
        self,
        interface: Type[T],
        implementation: Type[T] | Callable[[], T],
    ) -> None:
        """
        Register a transient service.

        A new instance will be created for each resolve call.

        Args:
            interface: The interface/protocol type to register
            implementation: The implementation class or factory function
        """
        if callable(implementation) and isinstance(implementation, type):
            self._transient_factories[interface] = implementation
        else:
            self._transient_factories[interface] = implementation

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a registered service.

        Args:
            interface: The interface/protocol type to resolve

        Returns:
            The resolved service instance

        Raises:
            KeyError: If the interface is not registered
        """
        # Check if we have a cached singleton
        if interface in self._singletons:
            return self._singletons[interface]

        # Check if we have a singleton factory
        if interface in self._singleton_factories:
            factory = self._singleton_factories[interface]
            instance = factory()
            self._singletons[interface] = instance
            return instance

        # Check if we have a transient factory
        if interface in self._transient_factories:
            factory = self._transient_factories[interface]
            return factory()

        raise KeyError(f"No registration found for {interface}")

    def is_registered(self, interface: Type[Any]) -> bool:
        """
        Check if an interface is registered.

        Args:
            interface: The interface/protocol type to check

        Returns:
            True if the interface is registered
        """
        return (
            interface in self._singletons
            or interface in self._singleton_factories
            or interface in self._transient_factories
        )

    def clear(self) -> None:
        """Clear all registrations and cached instances."""
        self._singletons.clear()
        self._singleton_factories.clear()
        self._transient_factories.clear()
