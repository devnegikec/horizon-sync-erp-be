"""Database query logging and performance monitoring utilities"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QueryPerformanceMonitor:
    """Monitor and log slow database queries"""
    
    # Threshold in seconds for logging slow queries
    SLOW_QUERY_THRESHOLD = 0.5
    
    def __init__(self, threshold: float = SLOW_QUERY_THRESHOLD):
        """
        Initialize query performance monitor.
        
        Args:
            threshold: Threshold in seconds for logging slow queries (default: 0.5s)
        """
        self.threshold = threshold
        self.enabled = False
    
    def enable(self, engine: Engine):
        """
        Enable query logging for an engine.
        
        Args:
            engine: SQLAlchemy engine to monitor
        """
        if self.enabled:
            return
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time"""
            conn.info.setdefault("query_start_time", []).append(time.time())
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries"""
            total_time = time.time() - conn.info["query_start_time"].pop()
            
            if total_time > self.threshold:
                logger.warning(
                    f"Slow query detected ({total_time:.3f}s): {statement[:200]}..."
                )
        
        self.enabled = True
        logger.info(f"Query performance monitoring enabled (threshold: {self.threshold}s)")
    
    def disable(self, engine: Engine):
        """
        Disable query logging for an engine.
        
        Args:
            engine: SQLAlchemy engine to stop monitoring
        """
        if not self.enabled:
            return
        
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
        
        self.enabled = False
        logger.info("Query performance monitoring disabled")


@contextmanager
def log_query_performance(operation_name: str, threshold: float = 0.1):
    """
    Context manager to log query performance for a specific operation.
    
    Usage:
        with log_query_performance("load_payment_entries"):
            payments = payment_repo.list_with_filters(...)
    
    Args:
        operation_name: Name of the operation being monitored
        threshold: Threshold in seconds for logging (default: 0.1s)
    
    Yields:
        None
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        if elapsed_time > threshold:
            logger.warning(
                f"Operation '{operation_name}' took {elapsed_time:.3f}s (threshold: {threshold}s)"
            )
        else:
            logger.debug(
                f"Operation '{operation_name}' completed in {elapsed_time:.3f}s"
            )


def explain_query(db: Session, query: Any) -> str:
    """
    Get EXPLAIN ANALYZE output for a query.
    
    This is useful for debugging query performance and verifying that indexes
    are being used effectively.
    
    Args:
        db: Database session
        query: SQLAlchemy query object
    
    Returns:
        EXPLAIN ANALYZE output as string
    """
    from sqlalchemy.dialects import postgresql
    
    # Compile query to SQL
    compiled = query.statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True}
    )
    
    # Execute EXPLAIN ANALYZE
    explain_query = f"EXPLAIN ANALYZE {compiled}"
    result = db.execute(explain_query)
    
    # Format output
    lines = [row[0] for row in result]
    return "\n".join(lines)


def log_query_plan(db: Session, query: Any, operation_name: str):
    """
    Log the query execution plan for debugging.
    
    Args:
        db: Database session
        query: SQLAlchemy query object
        operation_name: Name of the operation for logging
    """
    try:
        plan = explain_query(db, query)
        logger.info(f"Query plan for '{operation_name}':\n{plan}")
    except Exception as e:
        logger.error(f"Failed to get query plan for '{operation_name}': {e}")


# Global query performance monitor instance
query_monitor = QueryPerformanceMonitor()


def enable_query_logging(engine: Engine, threshold: float = 0.5):
    """
    Enable query logging for an engine.
    
    Args:
        engine: SQLAlchemy engine to monitor
        threshold: Threshold in seconds for logging slow queries (default: 0.5s)
    """
    query_monitor.threshold = threshold
    query_monitor.enable(engine)


def disable_query_logging(engine: Engine):
    """
    Disable query logging for an engine.
    
    Args:
        engine: SQLAlchemy engine to stop monitoring
    """
    query_monitor.disable(engine)
