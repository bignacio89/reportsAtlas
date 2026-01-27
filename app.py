import streamlit as st
import pandas as pd
import jinja2
from weasyprint import HTML
import base64
import io
import zipfile
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="RIA Report Portal", layout="wide")

# --- CUSTOM FILTERS & UTILS ---
def currency_format(value):
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "0.00"

def get_base64_logo(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- STYLING ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; background-color: #232ECF; color: white; }
    .report-card { border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- MAIN APP ---
st.title("📊 RIA Performance Reporting Portal")
st.info("Upload your Excel file and select the report type to generate PDFs for your agents.")

with st.sidebar:
    st.header("Setup")
    # Dropdown for the 3 report types
    report_selection = st.selectbox(
        "Choose Report Type",
        ["RIA Performance", "Portfolio Composition", "Tax & Activity Summary"]
    )
    
    uploaded_file = st.file_uploader("Upload Master Excel", type=["xlsx"])

# --- GENERATION LOGIC ---
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.fillna('', inplace=True)
    
    st.success(f"File uploaded! Found {len(df)} records.")
    
    # Validation: Ensure 'Agent' column exists
    if 'Agent' not in df.columns:
        st.error("Error: The Excel file must contain an 'Agent' column.")
    else:
        if st.button(f"Generate All {report_selection} Reports"):
            
            # 1. Load Logo
            try:
                logo_b64 = get_base64_logo("atlas_logo.png")
                logo_url = f"data:image/png;base64,{logo_b64}"
            except FileNotFoundError:
                st.warning("Logo file (atlas_logo.png) not found in repo. Using placeholder.")
                logo_url = ""

            # 2. Setup Jinja Environment & HTML (Performance Report Example)
            # You can create 'if' statements here to change templates based on report_selection
            template_loader = jinja2.FileSystemLoader(searchpath="./")
            env = jinja2.Environment(loader=template_loader)
            env.filters['currency'] = currency_format
            
            # Using the style we refined earlier
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page { size: landscape; margin: 1.5cm; }
                    body { font-family: Arial, sans-serif; color: #333; }
                    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #232ECF; padding-bottom: 10px; margin-bottom: 20px; }
                    .logo { max-width: 172.5px; } /* 15% bigger */
                    .report-info { text-align: right; }
                    .agent-name { font-size: 20px; font-weight: bold; color: #000; }
                    .report-date { font-size: 11.2px; color: #666; }
                    .summary-container { display: flex; justify-content: flex-end; gap: 15px; margin-top: 10px; }
                    .summary-card { background-color: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px 20px; min-width: 160px; text-align: left; }
                    .summary-card p { margin: 0; font-size: 12px; color: #555; }
                    .summary-card strong { display: block; font-size: 18px; color: #000; }
                    .client-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    .client-table th { background-color: #e0e0e0; padding: 10px; border-bottom: 2px solid #aaa; }
                    .client-table td { padding: 8px; border-bottom: 1px solid #eee; text-align: center; }
                    .client-table td:first-child { text-align: left; }
                    .positive { color: #1a8b30; font-weight: bold; }
                    .negative { color: #cc0000; font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="header">
                    <img src="{{ logo_url }}" class="logo">
                    <div class="report-info">
                        <div class="agent-name">{{ agent_name }}</div>
                        <p class="report-date">Report Date: {{ today }}</p>
                        <div class="summary-container">
                            <div class="summary-card"><p>Total Accounts</p><strong>{{ count }}</strong></div>
                            <div class="summary-card"><p>Total Balance</p><strong>${{ total | currency }}</strong></div>
                        </div>
                    </div>
                </div>
                <table class="client-table">
                    <thead>
                        <tr>
                            <th>Name</th><th>Portfolio</th><th>Balance</th><th>Performance</th><th>Open Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for client in clients %}
                        <tr>
                            <td>{{ client.Name }}</td>
                            <td>{{ client.Portfolio }}</td>
                            <td>${{ client.Balance | currency }}</td>
                            <td>
                                <span class="{{ 'positive' if client.Performance|float >= 0 else 'negative' }}">
                                    {{ (client.Performance|float * 100)|round(2) }}%
                                </span>
                            </td>
                            <td>{{ client.Date }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            template = env.from_string(html_template)
            
            # 3. Process Data and Create ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                
                grouped = df.groupby('Agent')
                progress_bar = st.progress(0)
                
                for i, (agent_name, agent_df) in enumerate(grouped):
                    # Clean data for PDF
                    agent_df['Balance'] = pd.to_numeric(agent_df['Balance'], errors='coerce').fillna(0)
                    
                    html_content = template.render(
                        logo_url=logo_url,
                        agent_name=agent_name,
                        today=datetime.now().strftime("%B %d, %Y"),
                        count=len(agent_df),
                        total=agent_df['Balance'].sum(),
                        clients=agent_df.to_dict(orient='records')
                    )
                    
                    pdf_data = HTML(string=html_content).write_pdf()
                    zf.writestr(f"Report_{agent_name}.pdf", pdf_data)
                    
                    progress_bar.progress((i + 1) / len(grouped))

            st.success("✅ All reports generated!")
            
            st.download_button(
                label="Download ZIP of All Reports",
                data=zip_buffer.getvalue(),
                file_name=f"Reports_{report_selection}_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip"
            )
