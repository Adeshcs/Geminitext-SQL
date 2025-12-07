"""
Python Implementation Module for Gemini Text-to-SQL
This module provides core functionality for the Streamlit application
"""

import pandas as pd
import sqlite3
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai


class SQLiteDatabase:
    """
    SQLite database manager for handling CSV imports and query execution
    """
    
    def __init__(self, db_path: str = ':memory:'):
        """
        Initialize database connection
        
        Args:
            db_path: Path to database file (default: in-memory)
        """
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.tables: Dict[str, pd.DataFrame] = {}
    
    def load_csv_to_table(self, table_name: str, csv_data: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Load CSV data into a database table
        
        Args:
            table_name: Name for the table
            csv_data: CSV content as string
            
        Returns:
            Tuple of (success, error_message, table_info)
        """
        try:
            from io import StringIO
            df = pd.read_csv(StringIO(csv_data))
            
            # Sanitize table name
            safe_table_name = self._sanitize_table_name(table_name)
            
            # Create table
            df.to_sql(safe_table_name, self.conn, if_exists='replace', index=False)
            self.tables[safe_table_name] = df
            
            # Get table info
            table_info = {
                'name': safe_table_name,
                'rows': len(df),
                'columns': list(df.columns),
                'dtypes': df.dtypes.to_dict()
            }
            
            return True, None, table_info
            
        except Exception as e:
            return False, str(e), None
    
    def load_dataframe_to_table(self, table_name: str, df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """
        Load pandas DataFrame into a database table
        
        Args:
            table_name: Name for the table
            df: Pandas DataFrame
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            safe_table_name = self._sanitize_table_name(table_name)
            df.to_sql(safe_table_name, self.conn, if_exists='replace', index=False)
            self.tables[safe_table_name] = df
            return True, None
        except Exception as e:
            return False, str(e)
    
    def execute_query(self, query: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute SQL query and return results
        
        Args:
            query: SQL query string
            
        Returns:
            Tuple of (result_dataframe, error_message)
        """
        try:
            # Security check: only allow SELECT queries
            if not query.strip().upper().startswith('SELECT'):
                return None, "Only SELECT queries are allowed for security reasons"
            
            result = pd.read_sql_query(query, self.conn)
            return result, None
        except Exception as e:
            return None, str(e)
    
    def get_table_schema(self, table_name: str) -> Optional[List[Dict]]:
        """
        Get schema information for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = self.cursor.fetchall()
            return [
                {
                    'name': col[1],
                    'type': col[2],
                    'nullable': not col[3],
                    'default': col[4],
                    'primary_key': bool(col[5])
                }
                for col in columns
            ]
        except Exception:
            return None
    
    def get_all_schemas(self) -> Dict[str, List[Dict]]:
        """
        Get schema information for all tables
        
        Returns:
            Dictionary mapping table names to their schemas
        """
        schemas = {}
        for table_name in self.tables.keys():
            schema = self.get_table_schema(table_name)
            if schema:
                schemas[table_name] = schema
        return schemas
    
    def _sanitize_table_name(self, name: str) -> str:
        """
        Sanitize table name to be SQL-safe
        
        Args:
            name: Original table name
            
        Returns:
            Sanitized table name
        """
        # Replace spaces and special characters with underscores
        safe_name = ''.join(c if c.isalnum() else '_' for c in name)
        
        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = f"table_{safe_name}"
        
        # Remove consecutive underscores
        while '__' in safe_name:
            safe_name = safe_name.replace('__', '_')
        
        return safe_name.lower()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class GeminiSQLGenerator:
    """
    Google Gemini AI integration for SQL query generation
    """
    
    def __init__(self, api_key: str, model: str = 'gemini-pro'):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google Gemini API key
            model: Model name to use
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def generate_query(
        self, 
        question: str, 
        schemas: Dict[str, List[Dict]], 
        sample_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate SQL query from natural language question
        
        Args:
            question: User's natural language question
            schemas: Database schemas
            sample_data: Optional sample data for context
            
        Returns:
            Tuple of (sql_query, explanation, error_message)
        """
        try:
            # Build schema description
            schema_text = self._build_schema_description(schemas, sample_data)
            
            # Create prompt
            prompt = self._create_prompt(question, schema_text)
            
            # Generate response
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean up the query
            sql_query = self._clean_query(sql_query)
            
            # Validate query
            if not sql_query.upper().startswith('SELECT'):
                return None, None, "Only SELECT queries are allowed"
            
            explanation = f"Generated SQL query for: {question}"
            
            return sql_query, explanation, None
            
        except Exception as e:
            return None, None, f"Error generating query: {str(e)}"
    
    def _build_schema_description(
        self, 
        schemas: Dict[str, List[Dict]], 
        sample_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> str:
        """Build text description of database schema"""
        description = "Database Schema:\n\n"
        
        for table_name, columns in schemas.items():
            description += f"Table: {table_name}\n"
            description += "Columns:\n"
            
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                description += f"  - {col['name']} ({col['type']}) {nullable}\n"
            
            # Add sample data if available
            if sample_data and table_name in sample_data:
                description += f"\nSample rows from {table_name}:\n"
                description += sample_data[table_name].head(3).to_string(index=False)
                description += "\n\n"
        
        return description
    
    def _create_prompt(self, question: str, schema_text: str) -> str:
        """Create prompt for Gemini"""
        return f"""You are an expert SQL query generator. Given a database schema and a user question, 
generate a SQL query that answers the question.

{schema_text}

User Question: {question}

Important Guidelines:
1. Generate ONLY the SQL query, without any explanations or markdown
2. Use proper SQLite syntax
3. Match column names and table names exactly as shown in the schema
4. Use appropriate JOINs if querying multiple tables
5. Include WHERE, GROUP BY, ORDER BY, and LIMIT clauses as needed
6. Only generate SELECT queries (no INSERT, UPDATE, DELETE, DROP)

SQL Query:"""
    
    def _clean_query(self, query: str) -> str:
        """Clean and format SQL query"""
        # Remove markdown code blocks
        query = query.replace('```sql', '').replace('```', '')
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Ensure it ends with semicolon
        query = query.rstrip(';') + ';'
        
        return query.strip()


# Utility functions

def validate_api_key(api_key: str) -> bool:
    """
    Validate Gemini API key
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        model.generate_content("test")
        return True
    except Exception:
        return False


def format_query_result(df: pd.DataFrame, max_rows: int = 100) -> str:
    """
    Format query results as readable text
    
    Args:
        df: Result DataFrame
        max_rows: Maximum rows to display
        
    Returns:
        Formatted string
    """
    if df.empty:
        return "No results found"
    
    result = f"Found {len(df)} rows\n\n"
    result += df.head(max_rows).to_string(index=False)
    
    if len(df) > max_rows:
        result += f"\n\n... and {len(df) - max_rows} more rows"
    
    return result


if __name__ == "__main__":
    # Basic test
    print("Python Implementation Module Loaded Successfully")
    print("Available classes: SQLiteDatabase, GeminiSQLGenerator")
