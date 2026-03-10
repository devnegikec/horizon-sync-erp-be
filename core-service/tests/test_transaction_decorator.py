"""Tests for transaction decorator"""

import pytest
from sqlalchemy.orm import Session

from app.core.transaction import transactional
from app.database import SessionLocal


class MockService:
    """Mock service for testing transaction decorator"""

    def __init__(self, db: Session):
        self.db = db
        self.call_count = 0

    @transactional
    def successful_operation(self):
        """Operation that succeeds"""
        self.call_count += 1
        return "success"

    @transactional
    def failing_operation(self):
        """Operation that raises an exception"""
        self.call_count += 1
        raise ValueError("Test error")

    @transactional
    def nested_transactional_operation(self):
        """Operation that calls another transactional method"""
        self.call_count += 1
        self.another_transactional_operation()
        return "nested success"

    @transactional
    def another_transactional_operation(self):
        """Another transactional operation"""
        self.call_count += 1
        return "inner success"


class TestTransactionalDecorator:
    """Test suite for @transactional decorator"""

    def test_successful_operation_commits(self):
        """Test that successful operations commit the transaction"""
        db = SessionLocal()
        try:
            service = MockService(db)

            # Execute operation
            result = service.successful_operation()

            # Verify result
            assert result == "success"
            assert service.call_count == 1

            # Verify transaction was committed (no active transaction)
            assert not db.in_transaction()
        finally:
            db.close()

    def test_failing_operation_rolls_back(self):
        """Test that failing operations rollback the transaction"""
        db = SessionLocal()
        try:
            service = MockService(db)

            # Execute operation that fails
            with pytest.raises(ValueError, match="Test error"):
                service.failing_operation()

            # Verify call was made
            assert service.call_count == 1

            # Verify transaction was rolled back (no active transaction)
            assert not db.in_transaction()
        finally:
            db.close()

    def test_nested_transactional_operations(self):
        """Test that nested transactional operations don't create nested transactions"""
        db = SessionLocal()
        try:
            service = MockService(db)

            # Execute nested operation
            result = service.nested_transactional_operation()

            # Verify result
            assert result == "nested success"
            assert service.call_count == 2  # Both methods called

            # Verify transaction was committed (no active transaction)
            assert not db.in_transaction()
        finally:
            db.close()

    def test_decorator_requires_db_attribute(self):
        """Test that decorator raises error if service doesn't have db attribute"""

        class BadService:
            @transactional
            def operation(self):
                return "should fail"

        service = BadService()

        with pytest.raises(AttributeError, match="must have a 'db' attribute"):
            service.operation()

    def test_multiple_operations_in_sequence(self):
        """Test that multiple operations can be executed in sequence"""
        db = SessionLocal()
        try:
            service = MockService(db)

            # Execute multiple operations
            result1 = service.successful_operation()
            result2 = service.successful_operation()
            result3 = service.successful_operation()

            # Verify results
            assert result1 == "success"
            assert result2 == "success"
            assert result3 == "success"
            assert service.call_count == 3

            # Verify no active transaction
            assert not db.in_transaction()
        finally:
            db.close()

    def test_rollback_after_failure_allows_new_transaction(self):
        """Test that after a rollback, new transactions can be started"""
        db = SessionLocal()
        try:
            service = MockService(db)

            # First operation fails
            with pytest.raises(ValueError):
                service.failing_operation()

            # Second operation succeeds
            result = service.successful_operation()

            # Verify both operations were called
            assert service.call_count == 2
            assert result == "success"

            # Verify no active transaction
            assert not db.in_transaction()
        finally:
            db.close()
