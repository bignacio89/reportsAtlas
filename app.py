import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# Import from modules
from modules.utils import get_base64_logo
from modules.report_performance import generate_performance_pdfs

st.set_page_config(page_title="RIA Portal", layout="wide")

st.title("📊 RIA Reporting Portal")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    
    # 1. REPORT TYPE
    report_type = st.selectbox(
        "Select Report Type", 
        ["RIA Performance", "Portfolio Composition", "Tax Summary"]
    )
    
    # 2. DATE PICKER (New!)
    # Defaults to today, but user can change it
    selected_date = st.date_input("Data Date", datetime.today())
    
    # 3. FILE UPLOADER
    uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

# --- MAIN LOGIC ---
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success(f"Loaded data: {len(df)} rows found.")
    
    # Load Logo
    logo_b64 = get_base64_logo("assets/atlas_logo.png")
    logo_url = f"data:image/png;base64,{logo_b64}"

    if st.button("Generate Reports"):
        
        with st.spinner("Processing..."):
            try:
                files_to_zip = []
                
                if report_type == "RIA Performance":
                    # PASS THE DATE HERE
                    files_to_zip = generate_performance_pdfs(df, logo_url, selected_date)
                
                elif report_type == "Portfolio Composition":
                    st.warning("Coming soon!")
                    
                # ZIP CREATION
                if files_to_zip:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for filename, content in files_to_zip:
                            zf.writestr(filename, content)
                    
                    # Create a filename for the ZIP too, using the selected date
                    zip_name = f"{report_type.replace(' ', '_')}_{selected_date.strftime('%Y%m%d')}.zip"
                    
                    st.success("✅ Done!")
                    st.download_button(
                        label="Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=zip_name,
                        mime="application/zip"
                    )
            
            except Exception as e:
                st.error(f"Error: {e}")
