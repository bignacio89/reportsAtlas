import pandas as pd
import jinja2
from weasyprint import HTML
from .utils import currency_format 

def generate_performance_pdfs(df, logo_url, report_date):
    """
    Returns a list of tuples: [('filename.pdf', pdf_bytes), ...]
    """
    
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page { size: landscape; margin: 0.8cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 10px; color: #333; } 
            
            /* Header Section */
            .header { border-bottom: 3px solid #232ECF; padding-bottom: 15px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: flex-start; }
            .logo { max-width: 150px; }
            
            /* Agent info & Cards */
            .header-right { text-align: right; }
            .agent-name { font-size: 18px; font-weight: bold; color: #000; margin-bottom: 2px; }
            .report-date { color: #666; font-size: 10px; margin-bottom: 10px; }
            
            .card-container { display: flex; gap: 12px; justify-content: flex-end; }
            .card { 
                background: #ffffff; 
                padding: 8px 15px; 
                border: 1px solid #e0e0e0; 
                border-radius: 8px;
