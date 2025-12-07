"""
Test Suite for Gemini Text-to-SQL Application
This file contains basic tests for the streamlit application.
"""

import unittest
import pandas as pd
import sqlite3


class TestDatabaseOperations(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
    
    def tearDown(self):
        """Clean up after tests"""
        self.conn.close()
    
    def test_create_table(self):
        """Test table creation"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'score': [85, 90, 95]
        })
        
        df.to_sql('test_table', self.conn, if_exists='replace', index=False)
        
        # Verify table exists
        result = pd.read_sql_query("SELECT * FROM test_table", self.conn)
        self.assertEqual(len(result), 3)
        self.assertEqual(list(result.columns), ['id', 'name', 'score'])
    
    def test_query_execution(self):
        """Test SQL query execution"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10, 20, 30]
        })
        
        df.to_sql('numbers', self.conn, if_exists='replace', index=False)
        
        # Test SELECT query
        result = pd.read_sql_query("SELECT SUM(value) as total FROM numbers", self.conn)
        self.assertEqual(result['total'][0], 60)


class TestCSVParsing(unittest.TestCase):
    """Test CSV parsing functionality"""
    
    def test_csv_loading(self):
        """Test loading CSV data"""
        csv_data = """name,age,city
Alice,25,New York
Bob,30,Los Angeles
Charlie,35,Chicago"""
        
        from io import StringIO
        df = pd.read_csv(StringIO(csv_data))
        
        self.assertEqual(len(df), 3)
        self.assertEqual(list(df.columns), ['name', 'age', 'city'])
        self.assertEqual(df['age'].sum(), 90)


if __name__ == '__main__':
    print("Running test suite...")
    unittest.main(verbosity=2)
