#!/usr/bin/env python3
import sqlite3

def check_database_schema():
    try:
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        
        # 获取students表的schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='students'")
        result = cursor.fetchone()
        
        if result:
            print("Students table schema:")
            print(result[0])
        else:
            print("Students table not found")
        
        # 获取表的列信息
        cursor.execute("PRAGMA table_info(students)")
        columns = cursor.fetchall()
        
        print("\nColumns in students table:")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - {'PRIMARY KEY' if col[5] else ''}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database_schema()
