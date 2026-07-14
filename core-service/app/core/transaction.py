"""Transaction management decorators and utilities"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.orm import Session

F = TypeVar("F", bound=Callable[..., Any])


def transactional(func: F) -> F:
    """
    Decorator for service methods that require database transactions.

    Ensures all multi-step operations use transactions with automatic
    commit on success and rollback on errors.

    The decorated function must have a 'self' parameter with a 'db' attribute
    that is a SQLAlchemy Session.

    Usage:
        class MyService:
            def __init__(self, db: Session):
                self.db = db

            @transactional
            def my_method(self, ...):
                # All database operations here will be in a transaction
                pass

    Requirements: 11.7
    """

    @functools.wraps(func)
    def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        # Get the database session from the service instance
        db: Session = getattr(self, "db", None)

        if db is None:
            raise AttributeError(
                f"Service {self.__class__.__name__} must have a 'db' attribute "
                "to use @transactional decorator"
            )

        # Check if we're already in a transaction
        # If so, don't create a nested transaction, just execute the function
        if db.in_transaction():
            return func(self, *args, **kwargs)

        # Start a new transaction
        try:
            result = func(self, *args, **kwargs)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise

    return wrapper  # type: ignore


def transactional_async(func: F) -> F:
    """
    Async version of the transactional decorator.

    For async service methods that require database transactions.

    Usage:
        class MyAsyncService:
            def __init__(self, db: AsyncSession):
                self.db = db

            @transactional_async
            async def my_method(self, ...):
                # All database operations here will be in a transaction
                pass

    Requirements: 11.7
    """

    @functools.wraps(func)
    async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        # Get the database session from the service instance
        db = getattr(self, "db", None)

        if db is None:
            raise AttributeError(
                f"Service {self.__class__.__name__} must have a 'db' attribute "
                "to use @transactional_async decorator"
            )

        # Check if we're already in a transaction
        if db.in_transaction():
            return await func(self, *args, **kwargs)

        # Start a new transaction
        try:
            result = await func(self, *args, **kwargs)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise

    return wrapper  # type: ignore
