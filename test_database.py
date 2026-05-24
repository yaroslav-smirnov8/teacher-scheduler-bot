"""Unit tests for database initialization"""
import pytest
import asyncio
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base


# Test database setup
TEST_DB_URL = 'sqlite+aiosqlite:///:memory:'


@pytest.fixture
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session"""
    TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    session = TestSessionLocal()
    yield session
    await session.close()


class TestDatabaseInitialization:
    """Tests for init_db() function"""
    
    @pytest.mark.asyncio
    async def test_init_db_creates_all_tables(self):
        """Test that init_db() creates all required tables including new recurring tables"""
        # Create engine
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        # Initialize database (same logic as init_db())
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Verify all tables are created
        async with engine.connect() as conn:
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
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_recurring_patterns_table_structure(self):
        """Test that recurring_patterns table has correct columns"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Check table structure
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('recurring_patterns')]
            
            columns = await conn.run_sync(get_columns)
        
        # Verify all required columns exist
        expected_columns = {
            'id',
            'teacher_id',
            'student_id',
            'start_date',
            'end_date',
            'time',
            'frequency',
            'interval',
            'weekday',
            'day_of_month',
            'created_from_lesson_id'
        }
        
        assert expected_columns.issubset(set(columns)), \
            f"Missing columns in recurring_patterns: {expected_columns - set(columns)}"
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_recurring_exceptions_table_structure(self):
        """Test that recurring_exceptions table has correct columns"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Check table structure
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('recurring_exceptions')]
            
            columns = await conn.run_sync(get_columns)
        
        # Verify all required columns exist
        expected_columns = {
            'id',
            'pattern_id',
            'exception_date',
            'reason'
        }
        
        assert expected_columns.issubset(set(columns)), \
            f"Missing columns in recurring_exceptions: {expected_columns - set(columns)}"
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_lessons_table_has_recurring_pattern_id(self):
        """Test that lessons table has the new recurring_pattern_id column"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Check table structure
        async with engine.connect() as conn:
            def get_columns(connection):
                inspector = inspect(connection)
                return [col['name'] for col in inspector.get_columns('lessons')]
            
            columns = await conn.run_sync(get_columns)
        
        # Verify recurring_pattern_id column exists
        assert 'recurring_pattern_id' in columns, \
            "lessons table is missing recurring_pattern_id column"
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints_exist(self):
        """Test that foreign key constraints are properly created"""
        engine = create_async_engine(TEST_DB_URL, echo=False)
        
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Check foreign keys for recurring_patterns
        async with engine.connect() as conn:
            def get_foreign_keys(connection):
                inspector = inspect(connection)
                return inspector.get_foreign_keys('recurring_patterns')
            
            foreign_keys = await conn.run_sync(get_foreign_keys)
        
        # Verify foreign keys exist
        fk_columns = {fk['constrained_columns'][0] for fk in foreign_keys}
        expected_fks = {'teacher_id', 'student_id'}
        
        assert expected_fks.issubset(fk_columns), \
            f"Missing foreign keys in recurring_patterns: {expected_fks - fk_columns}"
        
        await engine.dispose()
