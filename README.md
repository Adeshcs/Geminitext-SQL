# Gemini Text-to-SQL Pro

A complete, production-ready Text-to-SQL application powered by Google Gemini. This project provides two implementations:
1. **React Web App**: A modern, client-side Single Page Application (SPA) using `AlaSQL` for in-browser database simulation.
2. **Python Streamlit App**: A robust backend-capable application using `SQLite` and `Streamlit`.

## Features
- 📊 **CSV to SQL**: Instantly turn CSV files into queryable SQL tables.
- 🧠 **Schema Awareness**: The AI understands your table structure automatically.
- 🛡️ **Safe Execution**: Sandbox environments (In-browser or SQLite) prevent system-level SQL injection.
- 📈 **Visualization**: Automatic charting of query results.

---

## 🚀 Quick Start (React Web App)

The React app is the primary interface. It runs entirely in the browser.

### Prerequisites
- Node.js (v18+)
- NPM or Yarn

### Installation & Run
1. Install dependencies:
   ```bash
   npm install react react-dom lucide-react recharts @google/genai tailwindcss
   ```
   *(Note: Since this is a raw source output, ensure you have a standard Vite or Create-React-App structure)*

2. Run the development server (if using Vite):
   ```bash
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173`.
4. Enter your **Gemini API Key** and a username to start.

---

## 🐍 Python Streamlit Implementation

For users preferring a Python environment or server-side deployment.

### Prerequisites
- Python 3.9+
- Gemini API Key

### Installation
1. Install required packages:
   ```bash
   pip install streamlit pandas google-generativeai
   ```

2. Run the application:
   ```bash
   streamlit run streamlit_app.py
   ```

3. The app will open in your default browser at `http://localhost:8501`.

---

## 🧪 Testing

A comprehensive test suite is provided in `test_suite.py`.

Run tests using:
```bash
python test_suite.py
```

## 📂 Project Structure

- `index.html`, `index.tsx`, `App.tsx`: React Frontend core.
- `services/`: Database and AI integration services.
- `streamlit_app.py`: Standalone Python application.
- `test_suite.py`: Python Unit tests.
