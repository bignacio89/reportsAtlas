import pandas as pd
import jinja2
from weasyprint import HTML
from .utils import currency_format 

# UPDATE: Added report_date to arguments
def generate_performance_pdfs(df, logo_url, report_date):
    """
    Returns a list of tuples: [('20260126_Performance_AgentName.pdf', pdf_bytes), ...]
    """
    
    # 1. Format Dates
    # Format for the filename: YYYYMMDD (e.g., 20260126)
    file_date_str = report_date.strftime("%Y%m%d")
    # Format for the visible report: Month Day, Year (e.g., January 26, 2026)
    display_date_str = report_date.strftime("%B %d, %Y")

    # 2. HTML Template
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page { size: landscape; margin: 1.5cm; }
            body { font-family: Helvetica, Arial, sans-serif; }
            .header { border-bottom: 2px solid #232ECF; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; }
            .logo { max-width: 170px; }
            .agent-name { font-size: 20px; font-weight: bold; }
            .summary-box { background: #f9f9f9; padding: 10px; border: 1px solid #ddd; display: inline-block; margin-left: 10px; min-width: 120px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #e0e0e0; padding: 8px; text-align: center; }
            td { border-bottom: 1px solid #eee; padding: 8px; text-align: center; }
            td:first-child { text-align: left; }
            .positive { color: green; font-weight: bold; }
            .negative { color: red; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{{ logo_url }}" class="logo">
            <div style="text-align: right;">
                <div class="agent-name">{{ agent_name }}</div>
                <div style="color: #666; font-size: 12px; margin-bottom: 10px;">Report Date: {{ date }}</div>
                
                <div class="summary-box">
                    <small>Total Accounts</small><br>
                    <strong>{{ count }}</strong>
                </div>
                <div class="summary-box">
                    <small>Total Balance</small><br>
                    <strong>${{ total | currency }}</strong>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr><th>Name</th><th>Portfolio</th><th>Balance</th><th>Performance</th></tr>
            </thead>
            <tbody>
                {% for client in clients %}
                <tr>
                    <td>{{ client.Name }}</td>
                    <td>{{ client.Portfolio }}</td>
                    <td>${{ client.Balance | currency }}</td>
                    <td><span class="{{ 'positive' if client.Performance >= 0 else 'negative' }}">{{ (client.Performance * 100) | round(2) }}%</span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """

    env = jinja2.Environment(loader=jinja2.BaseLoader)
    env.filters['currency'] = currency_format
    template = env.from_string(html_template)
    
    df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce').fillna(0)
    
    generated_files = []
    
    if 'Agent' not in df.columns:
        raise ValueError("Column 'Agent' not found in Excel.")

    grouped = df.groupby('Agent')
    
    for agent_name, agent_df in grouped:
        html_out = template.render(
            logo_url=logo_url,
            agent_name=agent_name,
            date=display_date_str, # Passed to template
            count=len(agent_df),
            total=agent_df['Balance'].sum(),
            clients=agent_df.to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out).write_pdf()
        
        # Safe filename creation
        safe_agent = str(agent_name).replace(' ', '_').replace('/', '-')
        
        # New Filename Format: 20260126_Performance_AgentName.pdf
        filename = f"{file_date_str}_Performance_{safe_agent}.pdf"
        
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
