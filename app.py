import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile
import os
from pathlib import Path

# Import your custom modules
# Ensure these files exist in the /modules folder
from modules.report_performance import generate_performance_pdfs
from modules.report_generali import generate_generali_pdfs

# --- Page Configuration ---
st.set_page_config(
    page_title="Atlas Report Generator",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Atlas Client Report Generator")
st.markdown("""
Upload your Excel or CSV data. The system will automatically detect the report type 
(Performance or Generali) and generate branded PDFs for each agent.
""")

# --- Assets & Logo Logic ---
# We use Pathlib to get an absolute URI. This is the "Gold Standard" 
# for getting WeasyPrint to display local images.
base_path = Path(__file__).parent
logo_file = base_path / "assets" / "atlas_logo.png"

if logo_file.exists():
    # Converts /assets/atlas_logo.png to file:///C:/path/to/atlas_logo.png
    logo_to_use = logo_file.absolute().as_uri()
else:
    st.sidebar.error(f"⚠️ Logo not found at: {logo_file}")
    logo_to_use = "https://via.placeholder.com/150?text=Logo+Missing"

# --- Sidebar Settings ---
st.sidebar.header("Report Settings")
report_date = st.sidebar.date_input("Report Display Date", datetime.today())
st.sidebar.info(f"Using Logo: {os.path.basename(str(logo_file))}")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Excel or CSV File", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # 1. Load Data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"Successfully loaded '{uploaded_file.name}'")
        
        # Preview
        with st.expander("🔍 Preview Uploaded Data"):
            st.dataframe(df.head(10))

        # 2. Normalize columns for detection
        cols_lower = [str(c).lower().strip() for c in df.columns]
        generated_pdfs = []
        report_type = ""

        # 3. ROUTING LOGIC
        # Detect Generali (Check for 'contract id')
        if 'contract id' in cols_lower:
            st.info("🎯 **Detected Format:** Generali Performance")
            # The Generali module expects lowercase column names
            df.columns = cols_lower
            with st.spinner("Generating Generali Reports..."):
                generated_pdfs = generate_generali_pdfs(df, logo_to_use, report_date)
            report_type = "Generali"

        # Detect Standard Performance (Check for 'account number')
        elif 'account number' in cols_lower:
            st.info("🎯 **Detected Format:** Standard Performance")
            # Note: report_performance.py usually expects original casing (e.g., 'Agent', 'Balance')
            # If your module uses mixed case, do not force lowercase here.
            with st.spinner("Generating Performance Reports..."):
                generated_pdfs = generate_performance_pdfs(df, logo_to_use, report_date)
            report_type = "Performance"

        else:
            st.error("❌ **Format Not Recognized.** Make sure your file has 'Contract ID' or 'Account Number'.")

        # 4. DOWNLOAD SECTION
        if generated_pdfs:
            st.divider()
            st.subheader(f"✅ Generated {len(generated_pdfs)} {report_type} Reports")
            
            # Create a ZIP in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for filename, pdf_bytes in generated_pdfs:
                    zip_file.writestr(filename, pdf_bytes)
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.download_button(
                    label="📥 Download All (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"{report_type}_Reports_{report_date.strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                    type="primary"
                )
            
            with st.expander("📄 View Individual Files"):
                for filename, pdf_bytes in generated_pdfs:
                    st.download_button(
                        label=f"Download {filename}",
                        data=pdf_bytes,
                        file_name=filename,
                        key=filename
                    )

    except Exception as e:
        st.error(f"🚨 An error occurred during processing: {e}")
        st.exception(e) # This shows the full traceback to help you debug

else:
    st.info("Please upload a file to begin.")
