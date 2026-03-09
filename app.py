import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile
import os
from pathlib import Path

# Fix Sync Gap: Force Python to reload the modules
import importlib
import modules.report_performance
import modules.report_generali
import modules.report_axa

importlib.reload(modules.report_performance)
importlib.reload(modules.report_generali)
importlib.reload(modules.report_axa)

from modules.report_performance import generate_performance_pdfs
from modules.report_generali import generate_generali_pdfs
from modules.report_axa import generate_axa_pdfs

st.set_page_config(page_title="Atlas Report Generator", page_icon="📊", layout="wide")
st.title("📊 Atlas Client Report Generator")

# --- Assets & Logo ---
base_path = Path(__file__).parent
logo_file = base_path / "assets" / "atlas_logo.png"

if logo_file.exists():
    logo_to_use = logo_file.absolute().as_uri()
else:
    st.sidebar.error(f"⚠️ Logo not found at: {logo_file}")
    logo_to_use = ""

st.sidebar.header("Report Settings")
report_date = st.sidebar.date_input("Report Display Date", datetime.today())

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Excel or CSV File", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # CRITICAL CHANGE: sheet_name=None reads ALL sheets into a Dictionary
        if uploaded_file.name.endswith('.csv'):
            data_source = pd.read_csv(uploaded_file)
        else:
            data_source = pd.read_excel(uploaded_file, sheet_name=None)

        st.success(f"Loaded '{uploaded_file.name}'")
        generated_pdfs = []
        report_type = ""

        # ROUTING LOGIC
        # 1. Check if it's the multi-sheet AXA file
        if isinstance(data_source, dict) and 'Contratos' in data_source and 'Clientes' in data_source:
            st.info("🎯 **Detected Format:** AXA Report (Multi-sheet)")
            with st.spinner("Generando Reportes AXA..."):
                generated_pdfs = generate_axa_pdfs(data_source, logo_to_use, report_date)
            report_type = "AXA"
            
        else:
            # 2. Extract standard single-sheet Data
            df = list(data_source.values())[0] if isinstance(data_source, dict) else data_source
            cols_lower = [str(c).lower().strip() for c in df.columns]

            if 'contract id' in cols_lower:
                st.info("🎯 **Detected Format:** Generali Performance")
                df.columns = cols_lower 
                with st.spinner("Generating Generali Reports..."):
                    generated_pdfs = generate_generali_pdfs(df, logo_to_use, report_date)
                report_type = "Generali"

            elif 'account number' in cols_lower:
                st.info("🎯 **Detected Format:** Standard Performance")
                with st.spinner("Generating Performance Reports..."):
                    generated_pdfs = generate_performance_pdfs(df, logo_to_use, report_date)
                report_type = "Performance"

            else:
                st.error("❌ Format Not Recognized.")

        # DOWNLOAD SECTION
        if generated_pdfs:
            st.divider()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for filename, pdf_bytes in generated_pdfs:
                    zip_file.writestr(filename, pdf_bytes)
            
            st.download_button(
                label=f"📥 Download {len(generated_pdfs)} {report_type} Reports (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"{report_type}_Reports_{report_date.strftime('%Y%m%d')}.zip",
                mime="application/zip",
                type="primary"
            )

    except Exception as e:
        st.error(f"🚨 Error: {e}")
        st.exception(e)
