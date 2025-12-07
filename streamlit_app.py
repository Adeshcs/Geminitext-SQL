import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import io
import json
from typing import Optional, Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Gemini Text-to-SQL Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
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
    }
</style>
""", unsafe_allow_html=True)


class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.tables: Dict[str, pd.DataFrame] = {}
    
    def create_table_from_df(self, table_name: str, df: pd.DataFrame) -> bool:
        """Create a table from a pandas DataFrame"""
        try:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            self.tables[table_name] = df
            return True
        except Exception as e:
            st.error(f"Error creating table: {str(e)}")
            return False
    
    def execute_query(self, query: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Execute SQL query and return results"""
        try:
            result = pd.read_sql_query(query, self.conn)
            return result, None
        except Exception as e:
            return None, str(e)
    
    def get_schema(self) -> Dict[str, List[Dict]]:
        """Get schema information for all tables"""
        schema = {}
        for table_name in self.tables.keys():
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = self.cursor.fetchall()
            schema[table_name] = [
                {
                    "name": col[1],
                    "type": col[2],
                    "nullable": not col[3]
                }
                for col in columns
            ]
        return schema
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> Optional[pd.DataFrame]:
        """Get sample data from a table"""
        if table_name in self.tables:
            return self.tables[table_name].head(limit)
        return None


class GeminiQueryGenerator:
    """Generates SQL queries using Google Gemini AI"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_sql(self, question: str, schema: Dict[str, List[Dict]], 
                     sample_data: Dict[str, pd.DataFrame]) -> Tuple[Optional[str], Optional[str]]:
        """Generate SQL query from natural language question"""
        
        # Build schema description
        schema_desc = "Database Schema:\n\n"
        for table_name, columns in schema.items():
            schema_desc += f"Table: {table_name}\n"
            schema_desc += "Columns:\n"
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                schema_desc += f"  - {col['name']} ({col['type']}) {nullable}\n"
            
            # Add sample data
            if table_name in sample_data:
                schema_desc += f"\nSample data from {table_name}:\n"
                schema_desc += sample_data[table_name].to_string(index=False)
                schema_desc += "\n\n"
        
        prompt = f"""You are a SQL expert. Given the following database schema and sample data, 
generate a SQL query to answer the user's question.

{schema_desc}

User Question: {question}

Important:
- Generate ONLY the SQL query, no explanations
- Use proper SQLite syntax
- Make sure column names and table names match exactly
- Use appropriate JOINs if multiple tables are needed
- Include WHERE, GROUP BY, ORDER BY clauses as needed
- Return only SELECT queries (no INSERT, UPDATE, DELETE, DROP)

SQL Query:"""
        
        try:
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean up the query
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            # Security check: only allow SELECT queries
            if not sql_query.upper().startswith("SELECT"):
                return None, "Only SELECT queries are allowed for safety reasons."
            
            return sql_query, None
            
        except Exception as e:
            return None, f"Error generating query: {str(e)}"


def visualize_results(df: pd.DataFrame, query: str):
    """Automatically visualize query results based on data types"""
    
    if df.empty:
        st.info("No data to visualize")
        return
    
    # Determine chart type based on data structure
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    st.subheader("📊 Visualization")
    
    # If there's one categorical and one or more numeric columns
    if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
        chart_type = st.selectbox(
            "Select Chart Type",
            ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot"],
            key="chart_type"
        )
        
        x_col = st.selectbox("X-axis", categorical_cols + numeric_cols, key="x_axis")
        y_col = st.selectbox("Y-axis", numeric_cols, key="y_axis") if numeric_cols else None
        
        if y_col:
            try:
                if chart_type == "Bar Chart":
                    fig = px.bar(df, x=x_col, y=y_col, title="Bar Chart")
                elif chart_type == "Line Chart":
                    fig = px.line(df, x=x_col, y=y_col, title="Line Chart")
                elif chart_type == "Pie Chart" and x_col in categorical_cols:
                    fig = px.pie(df, names=x_col, values=y_col, title="Pie Chart")
                elif chart_type == "Scatter Plot":
                    fig = px.scatter(df, x=x_col, y=y_col, title="Scatter Plot")
                else:
                    fig = px.bar(df, x=x_col, y=y_col, title="Default Bar Chart")
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating visualization: {str(e)}")
    
    elif len(numeric_cols) >= 2:
        # Multiple numeric columns - show correlation heatmap
        st.write("**Correlation Heatmap**")
        corr_matrix = df[numeric_cols].corr()
        fig = px.imshow(corr_matrix, text_auto=True, aspect="auto",
                       title="Correlation Matrix")
        st.plotly_chart(fig, use_container_width=True)


def init_session_state():
    """Initialize session state variables"""
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    if 'query_generator' not in st.session_state:
        st.session_state.query_generator = None
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'api_key_set' not in st.session_state:
        st.session_state.api_key_set = False


def main():
    init_session_state()
    
    # Header
    st.markdown('<div class="main-header">🔍 Gemini Text-to-SQL Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Transform natural language into SQL queries with AI</div>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Enter your Google Gemini API key",
            value=st.session_state.get('api_key', '')
        )
        
        if api_key and not st.session_state.api_key_set:
            try:
                st.session_state.query_generator = GeminiQueryGenerator(api_key)
                st.session_state.api_key_set = True
                st.session_state.api_key = api_key
                st.success("✅ API Key configured!")
            except Exception as e:
                st.error(f"Invalid API Key: {str(e)}")
        
        st.divider()
        
        # File upload
        st.header("📁 Upload Data")
        uploaded_files = st.file_uploader(
            "Upload CSV files",
            type=['csv'],
            accept_multiple_files=True,
            help="Upload one or more CSV files to create tables"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    df = pd.read_csv(uploaded_file)
                    table_name = uploaded_file.name.replace('.csv', '').replace(' ', '_').lower()
                    
                    if st.session_state.db_manager.create_table_from_df(table_name, df):
                        st.success(f"✅ Loaded: {table_name}")
                except Exception as e:
                    st.error(f"Error loading {uploaded_file.name}: {str(e)}")
        
        st.divider()
        
        # Display loaded tables
        if st.session_state.db_manager.tables:
            st.header("📊 Loaded Tables")
            for table_name in st.session_state.db_manager.tables.keys():
                with st.expander(f"📋 {table_name}"):
                    sample = st.session_state.db_manager.get_sample_data(table_name)
                    if sample is not None:
                        st.dataframe(sample, use_container_width=True)
        
        st.divider()
        
        # Query History
        if st.session_state.query_history:
            st.header("📜 Query History")
            for i, item in enumerate(reversed(st.session_state.query_history[-5:])):
                with st.expander(f"Query {len(st.session_state.query_history) - i}"):
                    st.text(f"Question: {item['question']}")
                    st.code(item['query'], language='sql')
    
    # Main content area
    if not st.session_state.api_key_set:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar to get started.")
        st.info("""
        **How to get a Gemini API Key:**
        1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Sign in with your Google account
        3. Create a new API key
        4. Copy and paste it in the sidebar
        """)
        return
    
    if not st.session_state.db_manager.tables:
        st.info("📁 Please upload CSV files in the sidebar to begin querying.")
        st.markdown("""
        **Features:**
        - 📊 Upload multiple CSV files to create queryable tables
        - 🤖 Ask questions in natural language
        - 📈 Automatic data visualization
        - 🔒 Safe query execution (read-only)
        - 📜 Query history tracking
        """)
        return
    
    # Query interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("💬 Ask a Question")
        question = st.text_area(
            "Enter your question",
            height=100,
            placeholder="e.g., What are the top 10 customers by total sales?",
            help="Ask any question about your data in natural language"
        )
    
    with col2:
        st.header("🎯 Actions")
        generate_btn = st.button("🚀 Generate Query", type="primary", use_container_width=True)
        show_schema_btn = st.button("📋 Show Schema", use_container_width=True)
    
    # Show schema
    if show_schema_btn:
        st.subheader("📋 Database Schema")
        schema = st.session_state.db_manager.get_schema()
        for table_name, columns in schema.items():
            with st.expander(f"Table: {table_name}", expanded=True):
                schema_df = pd.DataFrame(columns)
                st.dataframe(schema_df, use_container_width=True)
    
    # Generate and execute query
    if generate_btn and question:
        with st.spinner("🤔 Generating SQL query..."):
            schema = st.session_state.db_manager.get_schema()
            sample_data = {
                table_name: st.session_state.db_manager.get_sample_data(table_name, 3)
                for table_name in st.session_state.db_manager.tables.keys()
            }
            
            sql_query, error = st.session_state.query_generator.generate_sql(
                question, schema, sample_data
            )
            
            if error:
                st.error(f"❌ {error}")
                return
            
            st.success("✅ Query generated successfully!")
            
            # Display generated query
            st.subheader("📝 Generated SQL Query")
            st.code(sql_query, language='sql')
            
            # Execute query
            col1, col2 = st.columns([1, 1])
            with col1:
                execute_btn = st.button("▶️ Execute Query", type="primary")
            with col2:
                modify_btn = st.button("✏️ Modify Query")
            
            if modify_btn:
                modified_query = st.text_area(
                    "Modify the query",
                    value=sql_query,
                    height=150,
                    key="modified_query"
                )
                if st.button("▶️ Execute Modified Query"):
                    sql_query = modified_query
                    execute_btn = True
            
            if execute_btn:
                with st.spinner("⚡ Executing query..."):
                    result_df, error = st.session_state.db_manager.execute_query(sql_query)
                    
                    if error:
                        st.error(f"❌ Query execution error: {error}")
                    else:
                        # Save to history
                        st.session_state.query_history.append({
                            'question': question,
                            'query': sql_query,
                            'result_rows': len(result_df)
                        })
                        
                        st.success(f"✅ Query executed successfully! Found {len(result_df)} rows.")
                        
                        # Display results
                        st.subheader("📊 Query Results")
                        st.dataframe(result_df, use_container_width=True)
                        
                        # Download button
                        csv = result_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Results (CSV)",
                            data=csv,
                            file_name="query_results.csv",
                            mime="text/csv"
                        )
                        
                        # Visualize results
                        if len(result_df) > 0:
                            visualize_results(result_df, sql_query)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>Built with ❤️ using Streamlit and Google Gemini AI</p>
        <p>Safe, sandbox SQL execution • No data stored • Privacy first</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
