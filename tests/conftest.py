"""
Shared pytest fixtures.
"""

import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from parser.models import Base

# Load environment variables
load_dotenv()


@pytest.fixture(scope='session')
def engine():
    """Create PostgreSQL engine for testing."""
    database_url = os.environ.get(
        'TEST_DATABASE_URL',
        'postgresql://taskparser:1357@localhost:5432/taskparser_test'
    )

    engine = create_engine(database_url)

    # Create tables
    Base.metadata.drop_all(engine)  # Clean start
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Create a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
