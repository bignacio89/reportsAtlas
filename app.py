import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# Import from your new modules
from modules.utils import get_base64_logo
from modules.report_performance import generate_performance_pdfs
# from modules.report_portfolio import generate_portfolio_pdfs (Future)
# from modules.report_tax import generate_tax_pdfs (Future)

st.set_page_config(page_title="RIA Portal", layout="wide")

# --- UI HEADER ---
st.title("📊 RIA Reporting Portal")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    report_type = st.selectbox(
        "Select Report Type", 
        ["RIA Performance", "Portfolio Composition", "Tax Summary"]
    )
    uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

# --- MAIN LOGIC ---
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success(f"Loaded data: {len(df)} rows found.")
    
    # Load Logo once
    logo_b64 = get_base64_logo("assets/atlas_logo.png")
    logo_url = f"data:image/png;base64,{logo_b64}"

    if st.button("Generate Reports"):
        
        with st.spinner("Processing..."):
            try:
                files_to_zip = []
                
                # ROUTING LOGIC
                if report_type == "RIA Performance":
                    files_to_zip = generate_performance_pdfs(df, logo_url)
                
                elif report_type == "Portfolio Composition":
                    st.warning("This module is coming soon!")
                    # files_to_zip = generate_portfolio_pdfs(df, logo_url)
                    
                elif report_type == "Tax Summary":
                    st.warning("This module is coming soon!")
                    # files_to_zip = generate_tax_pdfs(df, logo_url)

                # ZIP CREATION
                if files_to_zip:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for filename, content in files_to_zip:
                            zf.writestr(filename, content)
                    
                    st.success("✅ Done!")
                    st.download_button(
                        label="Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"{report_type}_{datetime.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip"
                    )
            
            except ValueError as e:
                st.error(f"Data Error: {e}")
            except Exception as e:
                st.error(f"System Error: {e}")
