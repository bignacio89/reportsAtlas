import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile
import os

# Import your custom modules
from modules.report_performance import generate_performance_pdfs
from modules.report_generali import generate_generali_pdfs

st.set_page_config(page_title="Investment Report Generator", layout="wide")

st.title("📊 Client Investment Report Generator")

# --- Logo & Assets Logic ---
# Get the absolute path to the logo in the assets folder
base_path = os.path.dirname(__file__)
logo_path = os.path.join(base_path, "assets", "logo.png") # Change to your actual filename

# Check if logo exists to prevent errors
if not os.path.exists(logo_path):
    st.warning(f"Logo not found at {logo_path}. Please check your assets folder.")
    logo_to_use = "https://via.placeholder.com/150" # Fallback
else:
    logo_to_use = logo_path

# --- Sidebar ---
st.sidebar.header("Settings")
report_date = st.sidebar.date_input("Report Date", datetime.today())

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Client Data (CSV or Excel)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load the data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success("File uploaded successfully!")
        
        # Normalize columns for detection
        cols_lower = [str(c).lower().strip() for c in df.columns]
        generated_pdfs = []
        report_type = ""

        # ROUTING LOGIC
        if 'contract id' in cols_lower:
            st.info("Detected: **Generali Performance Format**")
            # Set columns to lowercase for the Generali module
            df.columns = [c.lower().strip() for c in df.columns]
            generated_pdfs = generate_generali_pdfs(df, logo_to_use, report_date)
            report_type = "Generali"

        elif 'account number' in cols_lower:
            st.info("Detected: **Standard Performance Format**")
            generated_pdfs = generate_performance_pdfs(df, logo_to_use, report_date)
            report_type = "Performance"

        # --- Download UI ---
        if generated_pdfs:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for filename, pdf_bytes in generated_pdfs:
                    zip_file.writestr(filename, pdf_bytes)
            
            st.download_button(
                label=f"📥 Download {len(generated_pdfs)} {report_type} Reports (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"{report_type}_Reports_{report_date.strftime('%Y%m%d')}.zip",
                mime="application/zip"
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")
