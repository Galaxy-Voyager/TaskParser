#!/usr/bin/env python
"""
Script to initialize database tables using SQLAlchemy models.
Run with: poetry run python scripts/init_db.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()


def init_database():
    """Initialize database and create tables."""
    database_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://taskparser:1357@localhost:5432/taskparser'
    )

    print(f"Initializing database: {database_url}")

    try:
        # Create engine with taskparser user
        engine = create_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        print("Database connection successful")

        # Import models and create tables
        from parser.models import Base

        # Drop existing tables if they exist (to ensure clean state)
        print("Dropping existing tables if they exist...")
        Base.metadata.drop_all(engine)

        # Create all tables
        print("Creating tables...")
        Base.metadata.create_all(engine)
        print("Database tables created successfully")

        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            )
            tables = [row[0] for row in result]
            print(f"Created tables: {', '.join(tables)}")

        return True

    except SQLAlchemyError as e:
        print(f"Error creating database tables: {e}")

        error_str = str(e).lower()
        if "insufficientprivilege" in error_str or "permission denied" in error_str:
            print("\nРешение:")
            print("1. Запустите PostgreSQL shell от имени АДМИНИСТРАТОРА:")
            print('   Start-Process powershell -Verb RunAs')
            print('   & "C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe" -U postgres')
            print("\n2. Выполните следующие команды (по одной):")
            print('   ALTER DATABASE taskparser OWNER TO taskparser;')
            print('   \\c taskparser;')
            print('   DROP SCHEMA public CASCADE;')
            print('   CREATE SCHEMA public;')
            print('   GRANT ALL ON SCHEMA public TO taskparser;')
            print('   GRANT CREATE ON SCHEMA public TO taskparser;')
            print('   ALTER SCHEMA public OWNER TO taskparser;')
            print('   GRANT ALL PRIVILEGES ON DATABASE taskparser TO taskparser;')
        elif "does not exist" in error_str:
            print("\nРешение: Сначала создайте базу данных")
            print(
                '   & "C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe" -U postgres -c "CREATE DATABASE taskparser;"')

        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
