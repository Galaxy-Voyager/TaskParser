#!/usr/bin/env python
"""
Script to test database connection.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def test_connection():
    """Test database connection with different user roles."""

    # Test with postgres superuser
    postgres_url = "postgresql://postgres@localhost:5432/postgres"
    taskparser_url = os.environ.get('DATABASE_URL', 'postgresql://taskparser:1357@localhost:5432/taskparser')

    print("Testing database connections...")

    # Test postgres superuser connection
    try:
        engine = create_engine(postgres_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        print("✓ PostgreSQL superuser connection successful")
    except Exception as e:
        print(f"✗ PostgreSQL superuser connection failed: {e}")

    # Test taskparser user connection
    try:
        engine = create_engine(taskparser_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        print("✓ Taskparser user connection successful")
    except Exception as e:
        print(f"✗ Taskparser user connection failed: {e}")

        # Check if database exists
        try:
            engine = create_engine("postgresql://postgres@localhost:5432/postgres")
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT datname FROM pg_database WHERE datname = 'taskparser'")
                )
                exists = result.first() is not None
                if exists:
                    print("  Database 'taskparser' exists")
                else:
                    print("  Database 'taskparser' does not exist")
        except:
            pass


if __name__ == "__main__":
    test_connection()
