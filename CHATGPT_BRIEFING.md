# ChatGPT Briefing: ChatterFix CMMS Consulting Platform

## Project Overview

We're building **ChatterFix** - a business platform for CMMS (Computerized Maintenance Management System) consulting. It's a Streamlit dashboard that helps consultants:

1. **Onboard client companies** and store their data
2. **Clean/merge messy CMMS data** (work orders often have duplicate rows)
3. **Generate reports** (Data Quality Audits, ROI Analysis, MTBF predictions)
4. **Create deliverables** (PDF reports, cleaned CSVs)
5. **Track sales pipeline** and client relationships

## Tech Stack

- **Frontend:** Streamlit (Python)
- **Backend:** Python with pandas for data processing
- **Storage:** File-based (`~/.chatterfix/companies/`)
- **AI:** Anthropic Claude API for analysis (with plans for multi-model orchestration)

## Current Architecture

```
~/.chatterfix/companies/
└── Company_Name/
    ├── uploaded_data/
    │   ├── work_orders/    ← Raw CSV uploads
    │   ├── assets/
    │   ├── inventory/
    │   └── parts/
    ├── cleaned_data/       ← Processed/merged data
    ├── reports/            ← Generated analysis (JSON)
    ├── deliverables/       ← Final PDFs
    ├── knowledge/          ← AI insights
    └── metadata.json       ← Tracking info
```

## Key Files

### `/dashboard/app.py` (~2800 lines)
Main Streamlit app with pages:
- Dashboard (business metrics, priorities)
- Pipeline (sales funnel)
- Clients (client management)
- Data Studio (data cleaning/analysis)
- Deliverables (report generation)

### `/dashboard/company_storage.py`
`CompanyStorageManager` class that handles:
- Creating company folder structure
- Saving uploaded data with versioning
- Saving cleaned data
- Saving reports and deliverables
- Tracking metadata

### `/dashboard/ai_data_analyzer.py`
AI-powered data analysis that:
- Analyzes column meanings (what does "ACTLABCOST" mean?)
- Suggests cleaning strategies
- Generates insights

### `/dashboard/knowledge_base.py`
Client knowledge system for AI memory:
- Stores "hero numbers" (total spend, savings potential)
- Tracks worst assets, pain points
- Maintains conversation history

### `/scripts/data_cleaner.py`
Data cleaning logic:
- Merges duplicate work order rows
- Sums labor hours (additive)
- Takes first value for costs (not additive - same cost repeated)
- Collects technician names

## The Core Data Problem

CMMS exports often have **multiple rows per work order** because:
- Multiple technicians worked on it
- Multiple parts were used
- Multiple tasks within the same WO

**Wrong approach:** Sum all costs (causes massive inflation - $1.1M becomes $4.6M)
**Correct approach:**
- Hours → SUM (each row is unique labor)
- Costs → FIRST VALUE (same total repeated per line)
- Technicians → COLLECT UNIQUE

## What We Just Built

1. **Proper folder storage** - Files now save to organized company folders
2. **AI Data Assistant** - Natural language interface for data operations
3. **Fixed the AI assistant** - Queries like "view the data" now work

## Current Issue / What We Need Help With

The **AI Data Assistant** on the Data Studio page lets users type queries like:
- "Show me work order 12345"
- "Merge rows by work order"
- "Change the cost to $500 on WO 208160"

It uses pattern matching to understand queries and perform operations. We just fixed it to recognize "view" and "see" keywords.

**Questions for review:**

1. Is the `process_data_studio_query()` function well-designed? It's ~400 lines of pattern matching. Should we use a different approach (LLM-based parsing, state machine, etc.)?

2. The storage architecture - is file-based storage appropriate or should we move to SQLite/PostgreSQL?

3. The data cleaning logic - are we handling the duplicate row problem correctly?

4. Any architectural improvements for scaling this to handle multiple consultants/users?

## Code Snippets for Context

### Query Processing (simplified)
```python
def process_data_studio_query(query: str, df: pd.DataFrame) -> Dict:
    query_lower = query.lower()

    # Find key columns
    wo_col = next((c for c in df.columns if 'wonum' in c.lower()), None)

    # Pattern: Look for work order numbers
    wo_match = re.search(r'(?:wo|work\s*order)\s*(\d+)', query_lower)
    if wo_match and wo_col:
        wo_num = wo_match.group(1)
        matches = df[df[wo_col].astype(str).str.contains(wo_num)]
        return {'type': 'show', 'result_df': matches}

    # Pattern: Merge operations
    if 'merge' in query_lower:
        # ... merge logic

    # Pattern: Update operations
    if any(word in query_lower for word in ['change', 'update', 'set']):
        # ... update logic

    # Default: help message
    return {'type': 'info', 'message': "Try: 'merge by work order'"}
```

### Storage Manager (simplified)
```python
class CompanyStorageManager:
    BASE_DIR = Path.home() / ".chatterfix" / "companies"

    def save_uploaded_data(self, company_name, data_type, df, filename):
        path = self.get_company_path(company_name) / "uploaded_data" / data_type
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_csv(path / f"{data_type}_{timestamp}.csv")
        # Also save as "current" for easy access
        df.to_csv(path / f"{data_type}_current.csv")
```

## Running the App

```bash
streamlit run dashboard/app.py
# Opens at http://localhost:8501
```

---

**Please review and provide feedback on:**
1. Architecture decisions
2. Code quality concerns
3. Scalability issues
4. Better approaches for the AI query parsing
5. Any security concerns
