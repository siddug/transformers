#!/usr/bin/env python3
import sys
from database import create_tables, drop_tables, engine, repo_table, file_table
from sqlalchemy import inspect, select
from datetime import datetime

def test_table_creation():
    print("Testing database table creation...")
    
    # Create tables
    try:
        create_tables()
        print("✓ Tables created successfully")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return False
    
    # Check if tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if "repos" in tables:
        print("✓ 'repos' table exists")
    else:
        print("✗ 'repos' table not found")
        return False
        
    if "files" in tables:
        print("✓ 'files' table exists")
    else:
        print("✗ 'files' table not found")
        return False
    
    # Check table structure
    print("\nTable structures:")
    for table_name in ["repos", "files"]:
        print(f"\n{table_name}:")
        columns = inspector.get_columns(table_name)
        for col in columns:
            print(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")
    
    # Test inserting data
    print("\nTesting data insertion...")
    try:
        with engine.connect() as conn:
            # Insert a repo
            result = conn.execute(
                repo_table.insert().values(
                    owner="test_owner",
                    name="test_repo",
                    branch="main"
                )
            )
            repo_id = result.inserted_primary_key[0]
            print(f"✓ Inserted repo with ID: {repo_id}")
            
            # Insert a file
            result = conn.execute(
                file_table.insert().values(
                    repo_id=repo_id,
                    path="/test/file.py",
                    raw_content="print('hello')",
                    summary="Test file",
                    summary_status="pending",
                    chunks_status="pending"
                )
            )
            file_id = result.inserted_primary_key[0]
            print(f"✓ Inserted file with ID: {file_id}")
            
            # Query back
            repo_query = select(repo_table).where(repo_table.c.id == repo_id)
            repo_result = conn.execute(repo_query).first()
            print(f"✓ Retrieved repo: owner={repo_result.owner}, name={repo_result.name}")
            
            conn.commit()
    except Exception as e:
        print(f"✗ Error testing data operations: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_table_creation():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)