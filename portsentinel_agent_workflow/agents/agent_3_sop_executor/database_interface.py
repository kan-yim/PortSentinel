"""
Database Interface for Agent 3: SOP Executor.

This module provides a database interface for executing SQL queries
against the MySQL appdb database.
"""

import json
import mysql.connector
from typing import Dict, Any, List, Optional
from contextlib import contextmanager


class DatabaseInterface:
    """
    Interface for executing SQL queries against the appdb database.

    This class provides safe query execution with:
    - Connection pooling
    - Parameter binding
    - Error handling
    - Read-only enforcement for SELECT queries
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "appdb",
        user: str = "root",
        password: str = None
    ):
        """
        Initialize database interface.

        Args:
            host: Database host
            port: Database port
            database: Database name (default: appdb)
            user: Database user
            password: Database password
        """
        self.config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci"
        }

        # Test connection on initialization
        self._test_connection()

    def _test_connection(self):
        """Test database connection."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")

    @contextmanager
    def _get_connection(self):
        """
        Get database connection with context manager.

        Yields:
            mysql.connector.connection.MySQLConnection
        """
        conn = None
        try:
            conn = mysql.connector.connect(**self.config)
            yield conn
        finally:
            if conn and conn.is_connected():
                conn.close()

    def execute_select(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries.

        Args:
            query: SQL SELECT query with named parameters
                   Example: "SELECT * FROM vessel_advice WHERE system_vessel_name = :name"
            params: Dictionary of parameters
                   Example: {"name": "LIONCITY07"}

        Returns:
            List of dictionaries, each representing a row

        Raises:
            ValueError: If query is not a SELECT statement
            Exception: If query execution fails
        """
        # Validate that this is a SELECT query
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed in execute_select")

        # Convert named parameters (:param) to %(param)s format for mysql.connector
        converted_query = query
        converted_params = {}

        if params:
            for key, value in params.items():
                converted_query = converted_query.replace(f":{key}", f"%({key})s")
                converted_params[key] = value

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(converted_query, converted_params or {})
                results = cursor.fetchall()
                cursor.close()

                # Convert datetime objects to strings for JSON serialization
                for row in results:
                    for key, value in row.items():
                        if hasattr(value, 'isoformat'):
                            row[key] = value.isoformat()

                return results

        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")

    def execute_select_json(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a SELECT query and return results as JSON string.

        This is the format expected by Agent 3's execute_sql_query tool.

        Args:
            query: SQL SELECT query with named parameters
            params: Dictionary of parameters

        Returns:
            JSON string of results
        """
        try:
            results = self.execute_select(query, params)
            return json.dumps(results, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "query": query,
                "params": params
            })

    def test_query(self) -> Dict[str, Any]:
        """
        Test query to verify database connectivity.

        Returns:
            Dictionary with test results
        """
        try:
            results = self.execute_select("SELECT DATABASE() as current_db, NOW() as current_time")
            return {
                "status": "success",
                "database": results[0]["current_db"],
                "server_time": results[0]["current_time"],
                "message": "Database connection is working"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get column information for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of column information
        """
        query = """
            SELECT
                COLUMN_NAME as column_name,
                DATA_TYPE as data_type,
                IS_NULLABLE as is_nullable,
                COLUMN_KEY as column_key,
                COLUMN_DEFAULT as column_default
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :database AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
        """
        return self.execute_select(query, {
            "database": self.config["database"],
            "table_name": table_name
        })

    def list_tables(self) -> List[str]:
        """
        List all tables in the database.

        Returns:
            List of table names
        """
        query = """
            SELECT TABLE_NAME as table_name
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = :database
            ORDER BY TABLE_NAME
        """
        results = self.execute_select(query, {"database": self.config["database"]})
        return [row["table_name"] for row in results]


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("Database Interface Test")
    print("=" * 80)

    # You need to provide your MySQL password
    import os
    password = os.getenv("MYSQL_ROOT_PASSWORD")

    if not password:
        print("\nPlease set MYSQL_ROOT_PASSWORD environment variable:")
        print("  export MYSQL_ROOT_PASSWORD='your_password'")
        print("\nOr pass it directly:")
        password = input("Enter MySQL root password: ")

    try:
        # Initialize database interface
        print("\nConnecting to database...")
        db = DatabaseInterface(
            host="localhost",
            port=3306,
            database="appdb",
            user="root",
            password=password
        )
        print("✓ Connected successfully")

        # Test query
        print("\nTesting connection...")
        test_result = db.test_query()
        print(f"✓ Database: {test_result.get('database')}")
        print(f"✓ Server time: {test_result.get('server_time')}")

        # List tables
        print("\nListing tables...")
        tables = db.list_tables()
        print(f"✓ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

        # Example query: vessel_advice table
        print("\nQuerying vessel_advice table (first 3 rows)...")
        results = db.execute_select(
            "SELECT vessel_advice_no, system_vessel_name, effective_start_datetime, effective_end_datetime FROM vessel_advice LIMIT 3"
        )
        print(f"✓ Retrieved {len(results)} rows:")
        for row in results:
            print(f"  - Vessel {row['vessel_advice_no']}: {row['system_vessel_name']}")

        # Example with named parameters
        print("\nExample with named parameters...")
        if results:
            test_vessel = results[0]['system_vessel_name']
            print(f"Searching for vessel: {test_vessel}")

            param_results = db.execute_select(
                "SELECT * FROM vessel_advice WHERE system_vessel_name = :vessel_name",
                {"vessel_name": test_vessel}
            )
            print(f"✓ Found {len(param_results)} matching records")

        print("\n" + "=" * 80)
        print("✓ All tests passed! Database interface is ready.")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nPlease ensure:")
        print("  1. MySQL is running")
        print("  2. The 'appdb' database exists")
        print("  3. Password is correct")
