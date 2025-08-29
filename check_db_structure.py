"""
Check existing database structure
"""

import sqlite3
import os

def check_database_structure():
    """Check the existing database structure"""
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'mvtraders.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("Existing tables:")
        for table in tables:
            print(f"  - {table}")
        
        # Check if users table exists and get its schema
        if 'users' in tables:
            cursor.execute("PRAGMA table_info(users);")
            columns = cursor.fetchall()
            print(f"\nUsers table schema:")
            for col in columns:
                print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")
        else:
            print("\n❌ Users table not found!")
        
        # Check if vendors table exists
        if 'vendors' in tables:
            cursor.execute("PRAGMA table_info(vendors);")
            columns = cursor.fetchall()
            print(f"\nVendors table schema:")
            for col in columns:
                print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database_structure()
