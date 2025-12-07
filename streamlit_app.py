import streamlit as st
import pandas as pd
import sqlite3
import json
from io import StringIO
import os
import sys

# Check for required packages
try:
    import google.generativeai as genai
except ImportError:
    st.error("⚠️ Missing required package: google-generativeai")
    st.info("Please install it using: pip install google-generativeai")
    st.stop()

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    st.error("⚠️ Missing required package: plotly")
    st.info("Please install it using: pip install plotly")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Gemini Text-to-SQL Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'tables' not in st.session_state:
    st.session_state.tables = {}
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False
if 'db_conn' not in st.session_state:
    st.session_state.db_conn = None

# Database functions
def init_database():
    """Initialize SQLite database connection"""
    try:
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        st.session_state.db_conn = conn
        st.session_state.db_initialized = True
        return conn
    except Exception as e:
        st.error(f"Failed to initialize database: {str(e)}")
        return None

def get_db_connection():
    """Get or create database connection"""
    if not st.session_state.db_initialized or st.session_state.db_conn is None:
        return init_database()
    return st.session_state.db_conn

def create_table_from_csv(df, table_name):
    """Create a table from a pandas DataFrame"""
    try:
        # Sanitize table name
        table_name = table_name.replace('-', '_').replace(' ', '_')
        table_name = ''.join(c for c in table_name if c.isalnum() or c == '_')
        
        conn = get_db_connection()
        if conn is None:
            return False, "Database connection failed"
        
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema = {col[1]: col[2] for col in columns}
        
        st.session_state.tables[table_name] = {
            'columns': schema,
            'row_count': len(df),
            'dataframe': df.head(100)  # Store preview
        }
        return True, f"Table '{table_name}' created successfully with {len(df)} rows!"
    except Exception as e:
        return False, f"Error creating table: {str(e)}"

def get_table_schema():
    """Get formatted schema information for all tables"""
    if not st.session_state.tables:
        return "No tables available. Please upload a CSV file first."
    
    schema_text = "Database Schema:\n\n"
    for table_name, info in st.session_state.tables.items():
        schema_text += f"Table: {table_name}\n"
        schema_text += f"Columns:\n"
        for col, dtype in info['columns'].items():
            schema_text += f"  - {col} ({dtype})\n"
        schema_text += f"Row count: {info['row_count']}\n\n"
    return schema_text

def generate_sql_query(question, api_key):
    """Use Gemini to generate SQL query from natural language"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        schema = get_table_schema()
        prompt = f"""You are an expert SQL query generator. Given the following database schema and a question, generate a valid SQLite SQL query.

{schema}

Question: {question}

Important instructions:
1. Return ONLY the SQL query without any explanation, markdown formatting, or additional text
2. Do not include ```sql or ``` markers
3. The query should be a single line or properly formatted SQL
4. Use proper SQLite syntax
5. Make sure table and column names match exactly with the schema provided
6. For aggregate queries, use appropriate GROUP BY clauses
7. Use LIMIT to restrict large result sets when appropriate

SQL Query:"""

        response = model.generate_content(prompt)
        sql_query = response.text.strip()
        
        # Clean up the query
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
        return sql_query
    except Exception as e:
        raise Exception(f"Error generating SQL query: {str(e)}")

def execute_query(sql_query):
    """Execute SQL query and return results"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None, "Database connection failed"
        
        df = pd.read_sql_query(sql_query, conn)
        return df, None
    except Exception as e:
        return None, str(e)

def create_visualization(df, query):
    """Automatically create visualizations based on query results"""
    if df is None or len(df) == 0:
        return None
    
    try:
        # Determine best chart type based on data
        if len(df.columns) >= 2:
            numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns
            
            if len(numeric_cols) >= 1:
                # If we have one numeric column and one categorical
                if len(numeric_cols) == 1:
                    x_col = df.columns[0]
                    y_col = numeric_cols[0]
                    
                    # Bar chart for aggregated data
                    if len(df) <= 20:
                        fig = px.bar(df, x=x_col, y=y_col, title="Query Results Visualization")
                    else:
                        fig = px.line(df, x=x_col, y=y_col, title="Query Results Visualization")
                    return fig
                
                # Multiple numeric columns - line chart
                elif len(numeric_cols) > 1 and len(df) <= 50:
                    fig = px.line(df, x=df.columns[0], y=numeric_cols.tolist(), 
                                title="Query Results Visualization")
                    return fig
    except Exception as e:
        st.warning(f"Could not create visualization: {str(e)}")
        return None
    
    return None

# Main App
def main():
    # Header
    st.markdown('<p class="main-header">🤖 Gemini Text-to-SQL Pro</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform natural language into SQL queries with AI</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.api_key,
            help="Enter your Google Gemini API key"
        )
        
        if api_key:
            st.session_state.api_key = api_key
            st.success("✅ API Key configured")
        else:
            st.warning("⚠️ API Key required")
        
        st.divider()
        
        # File upload
        st.header("📁 Upload Data")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv'],
            help="Upload a CSV file to create a database table"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                st.success(f"✅ File loaded: {len(df)} rows × {len(df.columns)} columns")
                
                table_name = st.text_input(
                    "Table Name",
                    value=uploaded_file.name.replace('.csv', '').replace(' ', '_').replace('-', '_'),
                    help="Name for your database table (alphanumeric and underscores only)"
                )
                
                if st.button("📊 Create Table", type="primary"):
                    if table_name:
                        with st.spinner("Creating table..."):
                            success, message = create_table_from_csv(df, table_name)
                            if success:
                                st.success(message)
                                st.dataframe(df.head(5), use_container_width=True)
                            else:
                                st.error(message)
                    else:
                        st.error("Please provide a table name")
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")
        
        st.divider()
        
        # Display current tables
        if st.session_state.tables:
            st.header("📋 Current Tables")
            for table_name, info in st.session_state.tables.items():
                with st.expander(f"📊 {table_name}"):
                    st.write(f"**Rows:** {info['row_count']}")
                    st.write("**Columns:**")
                    for col, dtype in info['columns'].items():
                        st.write(f"- `{col}` ({dtype})")
                    
                    if 'dataframe' in info:
                        st.write("**Preview:**")
                        st.dataframe(info['dataframe'], use_container_width=True)
        
        st.divider()
        
        # Clear all data button
        if st.session_state.tables:
            if st.button("🗑️ Clear All Tables", type="secondary"):
                st.session_state.tables = {}
                st.session_state.query_history = []
                st.session_state.db_initialized = False
                st.session_state.db_conn = None
                st.rerun()
    
    # Main content
    if not st.session_state.api_key:
        st.warning("⚠️ Please enter your Gemini API key in the sidebar to get started.")
        st.info("""
        **How to get your API key:**
        1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Sign in with your Google account
        3. Create a new API key
        4. Copy and paste it in the sidebar
        """)
        return
    
    if not st.session_state.tables:
        st.info("📤 Upload a CSV file in the sidebar to create your first table and start querying!")
        
        # Sample CSV download
        st.subheader("Need sample data?")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Sample Employees Dataset**")
            sample_data = pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
                'age': [25, 30, 35, 28, 32],
                'department': ['Engineering', 'Marketing', 'Engineering', 'Sales', 'Marketing'],
                'salary': [75000, 65000, 85000, 60000, 70000]
            })
            
            st.dataframe(sample_data)
            csv = sample_data.to_csv(index=False)
            st.download_button(
                label="📥 Download Sample CSV",
                data=csv,
                file_name="sample_employees.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.write("**Sample Sales Dataset**")
            sample_sales = pd.DataFrame({
                'order_id': [101, 102, 103, 104, 105],
                'product': ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Laptop'],
                'quantity': [1, 3, 2, 1, 2],
                'price': [1200, 25, 75, 350, 1200],
                'date': ['2024-01-15', '2024-01-16', '2024-01-16', '2024-01-17', '2024-01-18']
            })
            
            st.dataframe(sample_sales)
            csv_sales = sample_sales.to_csv(index=False)
            st.download_button(
                label="📥 Download Sales CSV",
                data=csv_sales,
                file_name="sample_sales.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        return
    
    # Query interface
    tab1, tab2, tab3 = st.tabs(["💬 Ask Question", "📝 Direct SQL", "📊 Query History"])
    
    with tab1:
        st.subheader("Ask a Question in Natural Language")
        
        # Example questions
        with st.expander("💡 Example Questions"):
            st.markdown("""
            - Show me all records from the table
            - What is the average age of employees?
            - Count how many people work in each department
            - Who has the highest salary?
            - Show me employees older than 30
            - Calculate the total sales by product
            - What are the top 5 most expensive items?
            """)
        
        question = st.text_area(
            "Your Question",
            height=100,
            placeholder="e.g., Show me the top 5 employees by salary"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            generate_btn = st.button("🚀 Generate & Execute", type="primary", use_container_width=True)
        
        if generate_btn and question:
            with st.spinner("🤖 Generating SQL query..."):
                try:
                    # Generate SQL
                    sql_query = generate_sql_query(question, st.session_state.api_key)
                    st.code(sql_query, language="sql")
                    
                    # Execute query
                    with st.spinner("⚡ Executing query..."):
                        df_result, error = execute_query(sql_query)
                        
                        if error:
                            st.error(f"❌ Query execution error: {error}")
                        else:
                            st.success("✅ Query executed successfully!")
                            
                            # Save to history
                            st.session_state.query_history.append({
                                'question': question,
                                'sql': sql_query,
                                'timestamp': pd.Timestamp.now(),
                                'rows': len(df_result)
                            })
                            
                            # Display results
                            st.subheader("📊 Results")
                            
                            # Show stats
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Rows Returned", len(df_result))
                            col2.metric("Columns", len(df_result.columns))
                            col3.metric("Total Queries", len(st.session_state.query_history))
                            
                            st.dataframe(df_result, use_container_width=True)
                            
                            # Visualization
                            fig = create_visualization(df_result, sql_query)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Download option
                            csv = df_result.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results as CSV",
                                data=csv,
                                file_name="query_results.csv",
                                mime="text/csv"
                            )
                            
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.info("💡 Tip: Make sure your question clearly references table and column names from your schema.")
    
    with tab2:
        st.subheader("Write SQL Query Directly")
        
        sql_input = st.text_area(
            "SQL Query",
            height=150,
            placeholder="SELECT * FROM your_table LIMIT 10;"
        )
        
        if st.button("▶️ Execute Query", type="primary"):
            if sql_input:
                with st.spinner("⚡ Executing query..."):
                    df_result, error = execute_query(sql_input)
                    
                    if error:
                        st.error(f"❌ Query execution error: {error}")
                    else:
                        st.success("✅ Query executed successfully!")
                        
                        # Show stats
                        col1, col2 = st.columns(2)
                        col1.metric("Rows Returned", len(df_result))
                        col2.metric("Columns", len(df_result.columns))
                        
                        st.dataframe(df_result, use_container_width=True)
                        
                        # Visualization
                        fig = create_visualization(df_result, sql_input)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Download option
                        csv = df_result.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Results as CSV",
                            data=csv,
                            file_name="query_results.csv",
                            mime="text/csv"
                        )
            else:
                st.warning("Please enter a SQL query")
    
    with tab3:
        st.subheader("Query History")
        
        if st.session_state.query_history:
            for idx, item in enumerate(reversed(st.session_state.query_history)):
                with st.expander(f"Query {len(st.session_state.query_history) - idx}: {item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"):
                    st.write("**Question:**", item['question'])
                    st.code(item['sql'], language="sql")
                    st.write(f"**Rows returned:** {item['rows']}")
                    
                    # Re-execute button
                    if st.button(f"🔄 Re-execute", key=f"rerun_{idx}"):
                        df_result, error = execute_query(item['sql'])
                        if error:
                            st.error(f"Error: {error}")
                        else:
                            st.dataframe(df_result, use_container_width=True)
        else:
            st.info("No query history yet. Start asking questions!")

if __name__ == "__main__":
    main()
