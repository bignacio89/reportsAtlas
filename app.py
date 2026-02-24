import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile

# Import your custom modules
from modules.report_performance import generate_performance_pdfs
from modules.report_generali import generate_generali_pdfs

st.set_page_config(page_title="Investment Report Generator", layout="wide")

st.title("📊 Client Investment Report Generator")
st.write("Upload your Excel or CSV file to generate professional PDF reports per agent.")

# --- Sidebar Configuration ---
st.sidebar.header("Settings")
logo_url = st.sidebar.text_input("Logo URL", "https://your-company-logo.png")
report_date = st.sidebar.date_input("Report Date", datetime.today())

# --- File Upload ---
uploaded_file = st.file_uploader("Choose a file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load the data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success("File uploaded successfully!")
        
        # Display a preview
        with st.expander("Preview Data"):
            st.dataframe(df.head())

        # --- ROUTING LOGIC ---
        columns = [col.lower() for col in df.columns]
        generated_pdfs = []
        report_type = ""

        if 'contract id' in columns:
            st.info("Detected Format: **Generali Report**")
            # Ensure columns are exactly as the module expects (lowercase)
            df.columns = [col.lower() for col in df.columns]
            generated_pdfs = generate_generali_pdfs(df, logo_url, report_date)
            report_type = "Generali"

        elif 'account number' in columns or 'Account Number' in df.columns:
            st.info("Detected Format: **Performance Report**")
            generated_pdfs = generate_performance_pdfs(df, logo_url, report_date)
            report_type = "Performance"

        else:
            st.error("Error: Could not identify report type. Ensure your file has either 'Contract ID' or 'Account Number' columns.")

        # --- Download Logic ---
        if generated_pdfs:
            st.subheader(f"Generated {len(generated_pdfs)} {report_type} Reports")
            
            # Create a ZIP file in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for filename, pdf_bytes in generated_pdfs:
                    zip_file.writestr(filename, pdf_bytes)
            
            st.download_button(
                label="📥 Download All Reports (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"{report_type}_Reports_{report_date.strftime('%Y%m%d')}.zip",
                mime="application/zip"
            )

            # Individual download links
            with st.expander("Download Individual PDFs"):
                for filename, pdf_bytes in generated_pdfs:
                    st.download_button(label=f"📄 {filename}", data=pdf_bytes, file_name=filename)

    except Exception as e:
        st.error(f"An error occurred: {e}")
