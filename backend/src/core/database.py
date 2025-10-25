import logging
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Optional, List, Tuple
from src.core.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.config = config.database
        self._pool: Optional[SimpleConnectionPool] = None

    def initialize_pool(self, minconn: int = 1, maxconn: int = 5):
        if not self._pool:
            try:
                self._pool = SimpleConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    **self.config.get_connection_params()
                )
                logger.info("Database connection pool initialized")
            except psycopg2.Error as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise

    def close_pool(self):
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")

    @contextmanager
    def get_connection(self):
        if not self._pool:
            self.initialize_pool()

        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit: bool = True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database operation failed: {e}")
                raise
            finally:
                cursor.close()

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        with self.get_cursor(commit=False) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    def batch_insert(self, query: str, values: List[Tuple], template: Optional[str] = None) -> int:
        with self.get_cursor() as cursor:
            execute_values(cursor, query, values, template=template)
            return cursor.rowcount

    def execute_query_with_batch(self, query: str, values: List[Tuple], template: Optional[str] = None) -> List[Tuple]:
        with self.get_cursor() as cursor:
            result = execute_values(
                cursor,
                query,
                values,
                template=template,
                fetch=True
            )
            return result if result else []

    def table_exists(self, table_name: str) -> bool:
        query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """
        result = self.execute_query(query, (table_name,))
        return result[0][0] if result else False

    def get_table_count(self, table_name: str) -> int:
        query = f"SELECT COUNT(*) FROM {table_name};"
        result = self.execute_query(query)
        return result[0][0] if result else 0


db_manager = DatabaseManager()
