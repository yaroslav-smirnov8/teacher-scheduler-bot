"""Test the actual init_db() function from database.py"""
import pytest
import os
import asyncio
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine
from database import init_db
from models import Base


# Use a temporary test database
TEST_DB_FILE = 'test_init_db.db'
TEST_DB_URL = f'sqlite+aiosqlite:///{TEST_DB_FILE}'


@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up test database before and after each test"""
    # Remove test db if it exists
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    
    yield
    
    # Clean up after test
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


class TestInitDbFunction:
    """Tests for the actual init_db() function"""
    
    @pytest.mark.asyncio
    async def test_init_db_function_creates_all_tables(self):
        """Test that calling init_db() creates all required tables"""
        # Temporarily override the database URL
        import database
        original_url = database.DB_URL
        original_engine = database.engine
        
        try:
            # Set test database
            database.DB_URL = TEST_DB_URL
            database.engine = create_async_engine(TEST_DB_URL, echo=False)
            
            # Call init_db()
            await init_db()
            
            # Verify tables were created
            async with database.engine.connect() as conn:
                def get_table_names(connection):
                    inspector = inspect(connection)
                    return inspector.get_table_names()
                
                table_names = await conn.run_sync(get_table_names)
            
            # Check that all expected tables exist
            expected_tables = {
                'teachers',
                'students',
                'lessons',
                'recurring_patterns',
                'recurring_exceptions'
            }
            
            assert expected_tables.issubset(set(table_names)), \
                f"Missing tables: {expected_tables - set(table_names)}"
            
            # Verify the new tables specifically
            assert 'recurring_patterns' in table_names, \
                "recurring_patterns table was not created by init_db()"
            assert 'recurring_exceptions' in table_names, \
                "recurring_exceptions table was not created by init_db()"
            
            await database.engine.dispose()
            
        finally:
            # Restore original database configuration
            database.DB_URL = original_url
            database.engine = original_engine
    
    @pytest.mark.asyncio
    async def test_init_db_is_idempotent(self):
        """Test that calling init_db() multiple times is safe"""
        import database
        original_url = database.DB_URL
        original_engine = database.engine
        
        try:
            # Set test database
            database.DB_URL = TEST_DB_URL
            database.engine = create_async_engine(TEST_DB_URL, echo=False)
            
            # Call init_db() twice
            await init_db()
            await init_db()  # Should not raise an error
            
            # Verify tables still exist
            async with database.engine.connect() as conn:
                def get_table_names(connection):
                    inspector = inspect(connection)
                    return inspector.get_table_names()
                
                table_names = await conn.run_sync(get_table_names)
            
            expected_tables = {
                'teachers',
                'students',
                'lessons',
                'recurring_patterns',
                'recurring_exceptions'
            }
            
            assert expected_tables.issubset(set(table_names))
            
            await database.engine.dispose()
            
        finally:
            database.DB_URL = original_url
            database.engine = original_engine
