#!/usr/bin/env python3
"""
ChatterFix AI Platform
======================
Simple. Powerful. AI-driven CMMS analysis.

Upload your data. Ask questions. Get insights.

Run: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import json
import os
import csv
from datetime import datetime
from pathlib import Path

# AI Clients
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="ChatterFix AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .chat-user {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .chat-ai {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATA STORAGE
# =============================================================================
DATA_DIR = Path.home() / ".chatterfix"
DATA_DIR.mkdir(exist_ok=True)


def get_client_dir(client_name: str) -> Path:
    """Get storage directory for a client."""
    safe_name = client_name.replace(' ', '_').replace('/', '_')
    client_dir = DATA_DIR / "clients" / safe_name
    client_dir.mkdir(parents=True, exist_ok=True)
    (client_dir / "data").mkdir(exist_ok=True)
    (client_dir / "reports").mkdir(exist_ok=True)
    return client_dir


def list_clients() -> list:
    """List all clients with data."""
    clients = set()

    # Check clients folder
    clients_dir = DATA_DIR / "clients"
    if clients_dir.exists():
        for d in clients_dir.iterdir():
            if d.is_dir():
                clients.add(d.name.replace('_', ' '))

    # Check ai_reports folder for existing analyses
    reports_dir = DATA_DIR / "ai_reports"
    if reports_dir.exists():
        for f in reports_dir.glob("*.json"):
            # Extract client name from filename (e.g., "Queso_Queso_20260201_194559.json")
            parts = f.stem.rsplit('_', 2)  # Split off timestamp
            if len(parts) >= 3:
                client_name = parts[0].replace('_', ' ')
                clients.add(client_name)

    return sorted(list(clients))


def load_client_data(client_name: str) -> dict:
    """Load all data for a client."""
    client_dir = get_client_dir(client_name)
    data_dir = client_dir / "data"

    result = {
        'files': [],
        'records': [],
        'metrics': {},
        'analysis': None,
        'executive_summary': None,
        'csv_path': None  # Path to CSV for code execution
    }

    # Load all CSV files from client data folder
    for csv_file in data_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            result['files'].append({
                'name': csv_file.name,
                'rows': len(df),
                'columns': list(df.columns),
                'path': str(csv_file)
            })
            result['records'].extend(df.to_dict('records'))
            # Use the first/largest CSV as the main file
            if result['csv_path'] is None or len(df) > 1000:
                result['csv_path'] = str(csv_file)
        except Exception as e:
            pass

    # Load metrics if available
    metrics_file = client_dir / "metrics.json"
    if metrics_file.exists():
        try:
            with open(metrics_file) as f:
                result['metrics'] = json.load(f)
        except:
            pass

    # Also check ai_reports folder for existing analyses
    reports_dir = DATA_DIR / "ai_reports"
    if reports_dir.exists():
        safe_name = client_name.replace(' ', '_')
        for json_file in sorted(reports_dir.glob(f"{safe_name}_*.json"), reverse=True):
            try:
                with open(json_file) as f:
                    analysis_data = json.load(f)
                    # Load metrics from analysis if we don't have them
                    if not result['metrics'] and 'metrics' in analysis_data:
                        result['metrics'] = analysis_data['metrics']
                    # Load the analysis text
                    if 'full_analysis' in analysis_data:
                        result['analysis'] = analysis_data['full_analysis']
                    if 'executive_summary' in analysis_data:
                        result['executive_summary'] = analysis_data['executive_summary']
                    # Get original file path if available
                    if 'file_path' in analysis_data and not result['csv_path']:
                        orig_path = analysis_data['file_path']
                        if Path(orig_path).exists():
                            result['csv_path'] = orig_path
                    break  # Use most recent analysis
            except:
                pass

    return result


def save_client_data(client_name: str, df: pd.DataFrame, filename: str):
    """Save data file for a client."""
    client_dir = get_client_dir(client_name)
    data_path = client_dir / "data" / filename
    df.to_csv(data_path, index=False)
    return data_path


def save_client_metrics(client_name: str, metrics: dict):
    """Save metrics for a client."""
    client_dir = get_client_dir(client_name)
    with open(client_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2)


def save_report(client_name: str, report_content: str, report_type: str = "analysis"):
    """Save a report for a client."""
    client_dir = get_client_dir(client_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = client_dir / "reports" / f"{report_type}_{timestamp}.md"
    with open(report_path, 'w') as f:
        f.write(report_content)
    return report_path


# =============================================================================
# AI FUNCTIONS
# =============================================================================
def get_ai_client():
    """Get available AI client."""
    if CLAUDE_AVAILABLE and os.environ.get('ANTHROPIC_API_KEY'):
        return ('claude', anthropic.Anthropic())
    if OPENAI_AVAILABLE and os.environ.get('OPENAI_API_KEY'):
        return ('openai', openai.OpenAI())
    return (None, None)


# =============================================================================
# LOCAL CODE EXECUTION (Works with any model - much cheaper!)
# =============================================================================
import io
import sys
import traceback
import signal

def execute_python_safely(code: str, df: pd.DataFrame, timeout: int = 30) -> dict:
    """Execute Python code with pandas DataFrame available."""
    # Capture output
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    result = {
        'success': False,
        'output': '',
        'error': '',
        'result': None
    }

    # Allow full builtins but with the dataframe pre-loaded
    import numpy as np
    exec_globals = {
        '__builtins__': __builtins__,  # Full builtins needed for pandas
        'pd': pd,
        'np': np,
        'df': df.copy(),  # Copy to prevent modifications to original
    }

    try:
        exec(code, exec_globals)
        result['success'] = True
        result['output'] = sys.stdout.getvalue()

        # Try to get any result variable
        if 'result' in exec_globals:
            result['result'] = str(exec_globals['result'])

    except Exception as e:
        result['error'] = f"{type(e).__name__}: {str(e)}"
        result['output'] = sys.stdout.getvalue()

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result


def get_code_from_ai(client_type, client, question: str, columns: list, sample_data: str) -> str:
    """Ask AI to generate pandas code for the question."""
    prompt = f"""You are a Python/pandas expert. Generate ONLY executable Python code to answer this question.

DATAFRAME INFO:
- Variable name: df (already loaded)
- Columns: {columns}
- Sample data:
{sample_data}

QUESTION: {question}

RULES:
1. Output ONLY Python code, no markdown, no explanations
2. Use print() to show results
3. The dataframe is already loaded as 'df'
4. Handle missing values and type conversions
5. For costs, clean $ and , from strings before converting to float
6. End with printing the key findings

Generate the Python code:"""

    if client_type == 'claude':
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        code = response.content[0].text
    else:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for code gen
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        code = response.choices[0].message.content

    # Clean up code (remove markdown if present)
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]

    return code.strip()


def interpret_results(client_type, client, question: str, code: str, output: str, error: str) -> str:
    """Have AI interpret the code execution results."""
    if error:
        context = f"""The code execution had an error.

Question: {question}

Code that was run:
```python
{code}
```

Error: {error}
Output before error: {output}

Please explain what went wrong and provide insights from any partial results."""
    else:
        context = f"""Analyze these results and provide insights.

Question: {question}

Code that was run:
```python
{code}
```

Results:
{output}

Provide a clear, business-focused interpretation of these results. Use specific numbers. Format with markdown."""

    if client_type == 'claude':
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": context}]
        )
        return response.content[0].text
    else:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=2000,
            messages=[{"role": "user", "content": context}]
        )
        return response.choices[0].message.content


def run_local_analysis(client_type, client, df: pd.DataFrame, question: str) -> str:
    """Run complete local analysis pipeline."""
    # Get column info and sample
    columns = list(df.columns)
    sample = df.head(5).to_string()

    # Step 1: Get code from AI
    code = get_code_from_ai(client_type, client, question, columns, sample)

    # Step 2: Execute code locally
    exec_result = execute_python_safely(code, df)

    # Step 3: Interpret results
    interpretation = interpret_results(
        client_type, client, question, code,
        exec_result['output'], exec_result['error']
    )

    # Format final response
    response = interpretation

    # Add code block if user might want to see it
    if exec_result['success']:
        response += f"\n\n<details><summary>View Python Code</summary>\n\n```python\n{code}\n```\n</details>"

    return response


def ask_ai(client_type, client, prompt: str, max_tokens: int = 4000) -> str:
    """Send prompt to AI and get response."""
    try:
        if client_type == 'claude':
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        elif client_type == 'openai':
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"
    return "No AI available"


def load_csv_smart(file_content: bytes) -> list:
    """Load CSV with smart header detection."""
    csv.field_size_limit(10 * 1024 * 1024)

    lines = file_content.decode('utf-8-sig').splitlines()

    # Find header row (row with most columns and keywords)
    header_idx = 0
    max_score = 0
    keywords = ['date', 'asset', 'cost', 'hour', 'work', 'order', 'status', 'description', 'id', 'name']

    for i, line in enumerate(lines[:20]):
        cols = [c.strip() for c in line.split(',') if c.strip()]
        score = len(cols) + sum(2 for kw in keywords if kw in line.lower())
        if score > max_score:
            max_score = score
            header_idx = i

    # Parse data
    content = '\n'.join(lines[header_idx:])
    reader = csv.DictReader(content.splitlines())
    rows = [row for row in reader]

    # Filter empty rows
    data = [r for r in rows if sum(1 for v in r.values() if v and str(v).strip()) >= 3]

    return data


def get_data_summary(data: list, sample_size: int = 30) -> str:
    """Create data summary for AI."""
    if not data:
        return "No data"

    headers = list(data[0].keys())
    sample = data[:sample_size]

    summary = f"""
CMMS DATA SUMMARY
=================
Total Records: {len(data):,}
Columns ({len(headers)}): {', '.join(headers)}

SAMPLE DATA (first {len(sample)} rows):
"""
    for i, row in enumerate(sample[:10]):
        summary += f"\nRow {i+1}:\n"
        for k, v in row.items():
            if v and str(v).strip():
                summary += f"  {k}: {str(v)[:80]}\n"

    summary += "\n\nCOLUMN STATISTICS:\n"
    for col in headers:
        values = [str(r.get(col, '')) for r in data if str(r.get(col, '')).strip()]
        unique = len(set(values))
        summary += f"  {col}: {len(values):,} filled, {unique:,} unique\n"

    return summary


def calculate_metrics(data: list) -> dict:
    """Calculate basic metrics from data."""
    if not data:
        return {}

    headers = list(data[0].keys())

    # Find cost column
    cost_cols = [c for c in headers if 'cost' in c.lower() or 'price' in c.lower()]
    total_cost = 0
    if cost_cols:
        for row in data:
            try:
                val = str(row.get(cost_cols[0], '')).replace('$', '').replace(',', '').strip()
                if val:
                    total_cost += float(val)
            except:
                pass

    # Count unique assets
    asset_cols = [c for c in headers if 'asset' in c.lower() and 'desc' not in c.lower()]
    unique_assets = 0
    if asset_cols:
        unique_assets = len(set(r.get(asset_cols[0], '') for r in data if r.get(asset_cols[0], '').strip()))

    # Count unique work orders
    wo_cols = [c for c in headers if ('work' in c.lower() and 'order' in c.lower()) or 'wonum' in c.lower() or c.lower() == 'work_order_number']
    unique_wos = 0
    if wo_cols:
        unique_wos = len(set(r.get(wo_cols[0], '') for r in data if r.get(wo_cols[0], '').strip()))

    # Count technicians
    tech_cols = [c for c in headers if 'assign' in c.lower() or 'tech' in c.lower()]
    unique_techs = 0
    if tech_cols:
        unique_techs = len(set(r.get(tech_cols[0], '') for r in data if r.get(tech_cols[0], '').strip()))

    return {
        'total_records': len(data),
        'total_columns': len(headers),
        'total_cost': total_cost,
        'unique_assets': unique_assets,
        'unique_work_orders': unique_wos,
        'unique_technicians': unique_techs,
        'potential_savings': total_cost * 0.25,
    }


# =============================================================================
# SESSION STATE
# =============================================================================
def init_session():
    """Initialize session state."""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_client' not in st.session_state:
        st.session_state.current_client = None
    if 'current_data' not in st.session_state:
        st.session_state.current_data = None
    if 'data_summary' not in st.session_state:
        st.session_state.data_summary = None
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None
    if 'use_code_interpreter' not in st.session_state:
        st.session_state.use_code_interpreter = True


# =============================================================================
# PAGES
# =============================================================================
def render_ai_chat():
    """Main AI Chat page - the core of the app."""
    st.markdown("# 🤖 AI CMMS Assistant")
    st.markdown("**Upload data, ask questions, get insights.**")

    # Check AI availability
    client_type, client = get_ai_client()

    if not client_type:
        st.error("⚠️ No AI available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.")
        return

    st.success(f"✓ AI Ready ({client_type.upper()})")

    st.markdown("---")

    # Two columns: Chat and Data
    col_chat, col_data = st.columns([2, 1])

    with col_data:
        st.markdown("### 📁 Data")

        # Client selection
        clients = list_clients()

        client_options = ["+ New Client"] + clients
        selected = st.selectbox("Select Client", client_options)

        if selected == "+ New Client":
            new_client = st.text_input("New Client Name", placeholder="e.g., Queso Queso")
            if new_client:
                st.session_state.current_client = new_client
                st.session_state.current_data = None
                st.session_state.data_summary = None
        else:
            # Always load data when a client is selected
            if st.session_state.current_client != selected:
                st.session_state.current_client = selected
                st.session_state.current_data = None
                st.session_state.data_summary = None

            # Load client data
            client_data = load_client_data(selected)

            # Set file path for code execution
            if client_data['csv_path']:
                st.session_state.uploaded_file_path = client_data['csv_path']

            # Show loaded files if any
            if client_data['files']:
                st.markdown("**Loaded Files:**")
                for f in client_data['files']:
                    st.write(f"- {f['name']} ({f['rows']:,} rows)")

            # Show metrics from existing analysis
            if client_data['metrics']:
                m = client_data['metrics']
                st.markdown("**Metrics:**")
                st.write(f"- Records: {m.get('total_records', 0):,}")
                st.write(f"- Assets: {m.get('unique_assets', 0):,}")
                st.write(f"- Work Orders: {m.get('unique_work_orders', 0):,}")
                if m.get('total_cost', 0) > 0:
                    st.write(f"- Total Cost: ${m.get('total_cost', 0):,.0f}")

            # Build data summary - always refresh from loaded data
            if client_data['records']:
                st.session_state.current_data = client_data['records']
                st.session_state.data_summary = get_data_summary(client_data['records'])
            elif client_data['analysis']:
                # Use existing analysis as context
                m = client_data['metrics']
                st.session_state.current_data = True  # Flag that we have data context
                st.session_state.data_summary = f"""
EXISTING ANALYSIS FOR {selected}
================================
Total Records: {m.get('total_records', 0):,}
Columns: {', '.join(m.get('columns', []))}
Total Cost: ${m.get('total_cost', 0):,.0f}
Unique Assets: {m.get('unique_assets', 0):,}
Unique Work Orders: {m.get('unique_work_orders', 0):,}

PREVIOUS ANALYSIS:
{client_data['analysis']}

EXECUTIVE SUMMARY:
{client_data.get('executive_summary', 'N/A')}
"""

        # File upload
        st.markdown("---")
        uploaded_file = st.file_uploader("Upload CSV", type=['csv'])

        if uploaded_file and st.session_state.current_client:
            with st.spinner("Loading data..."):
                data = load_csv_smart(uploaded_file.getvalue())

            if data:
                st.success(f"✓ Loaded {len(data):,} records")

                # Save to client folder
                df = pd.DataFrame(data)
                saved_path = save_client_data(st.session_state.current_client, df, uploaded_file.name)
                st.session_state.uploaded_file_path = str(saved_path)

                # Calculate and save metrics
                metrics = calculate_metrics(data)
                save_client_metrics(st.session_state.current_client, metrics)

                # Store in session
                st.session_state.current_data = data
                st.session_state.data_summary = get_data_summary(data)

                # Show metrics
                st.markdown("**Quick Metrics:**")
                st.write(f"- Records: {metrics['total_records']:,}")
                st.write(f"- Assets: {metrics['unique_assets']:,}")
                st.write(f"- Work Orders: {metrics['unique_work_orders']:,}")
                if metrics['total_cost'] > 0:
                    st.write(f"- Total Cost: ${metrics['total_cost']:,.0f}")
            else:
                st.error("Could not parse CSV file")

        # Quick actions
        if st.session_state.current_data:
            st.markdown("---")
            st.markdown("### Quick Actions")

            if st.button("📊 Full Analysis", use_container_width=True):
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Provide a comprehensive analysis of this CMMS data including data quality, financial analysis, asset insights, and recommendations.'
                })
                st.rerun()

            if st.button("💰 Cost Analysis", use_container_width=True):
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Analyze the costs in this data. What are the top cost drivers? Where can we save money?'
                })
                st.rerun()

            if st.button("🔧 Asset Health", use_container_width=True):
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Which assets need attention? Identify the "money pit" assets that are costing the most to maintain.'
                })
                st.rerun()

            if st.button("📋 Executive Summary", use_container_width=True):
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': 'Write a brief executive summary of this data in 3-4 sentences for a C-level presentation.'
                })
                st.rerun()

    with col_chat:
        st.markdown("### 💬 Chat")

        # Chat container
        chat_container = st.container()

        with chat_container:
            # Display chat history
            for msg in st.session_state.chat_history:
                if msg['role'] == 'user':
                    st.markdown(f"<div class='chat-user'><b>You:</b> {msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-ai'>{msg['content']}</div>", unsafe_allow_html=True)

        # Process pending AI responses
        if st.session_state.chat_history and st.session_state.chat_history[-1]['role'] == 'user':
            user_msg = st.session_state.chat_history[-1]['content']

            # Check if we can use local code execution
            use_local_code = (
                st.session_state.use_code_interpreter and
                st.session_state.uploaded_file_path and
                Path(st.session_state.uploaded_file_path).exists()
            )

            if use_local_code:
                with st.spinner("🐍 Running Python analysis locally..."):
                    try:
                        # Load the dataframe
                        df = pd.read_csv(st.session_state.uploaded_file_path)
                        response = run_local_analysis(client_type, client, df, user_msg)
                    except Exception as e:
                        st.warning(f"Code execution failed: {e}. Using regular AI...")
                        # Fallback to regular AI
                        if st.session_state.data_summary:
                            context = f"CMMS data for {st.session_state.current_client}:\n{st.session_state.data_summary}\n\nQuestion: {user_msg}"
                            response = ask_ai(client_type, client, context)
                        else:
                            response = f"Error: {e}"
            else:
                with st.spinner("AI is thinking..."):
                    # Build context
                    if st.session_state.data_summary:
                        context = f"""You are a CMMS expert consultant analyzing maintenance data for {st.session_state.current_client or 'a client'}.

{st.session_state.data_summary}

User question: {user_msg}

Provide a helpful, specific answer using the data. Use markdown formatting. Be direct and actionable."""
                    else:
                        context = f"""You are a CMMS expert consultant.

User question: {user_msg}

Note: No data has been uploaded yet. Ask the user to upload their CMMS data for analysis."""

                    response = ask_ai(client_type, client, context)

            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response
            })

            # Save report if it's an analysis
            if st.session_state.current_client and len(response) > 500:
                save_report(st.session_state.current_client, response)

            st.rerun()

        # Chat input
        st.markdown("---")
        user_input = st.text_area("Ask anything about your maintenance data...", height=100, key="chat_input")

        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Send", type="primary", use_container_width=True):
                if user_input.strip():
                    st.session_state.chat_history.append({
                        'role': 'user',
                        'content': user_input.strip()
                    })
                    st.rerun()
        with col2:
            if st.button("Clear", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()


def render_clients():
    """Client list and management."""
    st.markdown("# 📁 Clients")

    clients = list_clients()

    if not clients:
        st.info("No clients yet. Go to AI Chat and upload some data.")
        return

    for client in clients:
        with st.expander(f"📊 {client}", expanded=False):
            client_data = load_client_data(client)

            # Metrics
            if client_data['metrics']:
                m = client_data['metrics']
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Records", f"{m.get('total_records', 0):,}")
                with col2:
                    st.metric("Assets", f"{m.get('unique_assets', 0):,}")
                with col3:
                    st.metric("Work Orders", f"{m.get('unique_work_orders', 0):,}")
                with col4:
                    if m.get('total_cost', 0) > 0:
                        st.metric("Total Cost", f"${m.get('total_cost', 0):,.0f}")

            # Files
            if client_data['files']:
                st.markdown("**Data Files:**")
                for f in client_data['files']:
                    st.write(f"- {f['name']} ({f['rows']:,} rows)")

            # Reports
            client_dir = get_client_dir(client)
            reports = list((client_dir / "reports").glob("*.md"))
            if reports:
                st.markdown("**Reports:**")
                for r in sorted(reports, reverse=True)[:5]:
                    with open(r) as f:
                        preview = f.read()[:200]
                    st.download_button(
                        f"📄 {r.stem}",
                        open(r).read(),
                        file_name=r.name,
                        mime="text/markdown"
                    )


def render_reports():
    """View saved reports."""
    st.markdown("# 📋 Reports")

    reports_dir = DATA_DIR / "ai_reports"
    client_dirs = DATA_DIR / "clients"

    all_reports = []

    # Collect reports from ai_reports folder
    if reports_dir.exists():
        for r in reports_dir.glob("*.md"):
            all_reports.append(('General', r))

    # Collect reports from client folders
    if client_dirs.exists():
        for client_dir in client_dirs.iterdir():
            if client_dir.is_dir():
                reports_path = client_dir / "reports"
                if reports_path.exists():
                    for r in reports_path.glob("*.md"):
                        all_reports.append((client_dir.name.replace('_', ' '), r))

    if not all_reports:
        st.info("No reports yet. Use the AI Chat to analyze data and generate reports.")
        return

    # Sort by modification time
    all_reports.sort(key=lambda x: x[1].stat().st_mtime, reverse=True)

    for client, report_path in all_reports[:20]:
        with st.expander(f"📄 {report_path.stem} ({client})"):
            with open(report_path) as f:
                content = f.read()
            st.markdown(content)
            st.download_button(
                "Download",
                content,
                file_name=report_path.name,
                mime="text/markdown"
            )


# =============================================================================
# MAIN APP
# =============================================================================
def main():
    """Main application."""
    init_session()

    # Sidebar navigation
    st.sidebar.markdown("## 🔧 ChatterFix AI")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigate",
        ["🤖 AI Chat", "📁 Clients", "📋 Reports"],
        label_visibility="collapsed"
    )

    # Current client indicator
    if st.session_state.current_client:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Active:** {st.session_state.current_client}")
        if st.session_state.current_data and isinstance(st.session_state.current_data, list):
            st.sidebar.markdown(f"*{len(st.session_state.current_data):,} records loaded*")

    # Code Execution toggle
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Settings**")
    st.session_state.use_code_interpreter = st.sidebar.checkbox(
        "🐍 Run Python Locally",
        value=st.session_state.use_code_interpreter,
        help="AI generates pandas code, we run it locally (cheaper & faster)"
    )
    if st.session_state.use_code_interpreter:
        st.sidebar.caption("AI → Python code → Local execution → Results")

    st.sidebar.markdown("---")
    st.sidebar.markdown("*Powered by AI*")

    # Render page
    if page == "🤖 AI Chat":
        render_ai_chat()
    elif page == "📁 Clients":
        render_clients()
    elif page == "📋 Reports":
        render_reports()


if __name__ == "__main__":
    main()
