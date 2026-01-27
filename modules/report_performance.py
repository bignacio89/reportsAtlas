import pandas as pd
import jinja2
from weasyprint import HTML
from datetime import datetime
from .utils import currency_format 

def generate_performance_pdfs(df, logo_url):
    """
    Returns a list of tuples: [('filename.pdf', pdf_bytes), ...]
    """
    
    # 1. Define the HTML Template (Specific to this report)
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
            .summary-box { background: #f9f9f9; padding: 10px; border: 1px solid #ddd; display: inline-block; margin-left: 10px; }
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
                <div style="color: #666; font-size: 12px; margin-bottom: 10px;">{{ date }}</div>
                
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

    # 2. Setup Environment
    env = jinja2.Environment(loader=jinja2.BaseLoader)
    env.filters['currency'] = currency_format
    template = env.from_string(html_template)
    
    # 3. Process Data
    # Ensure standard column names or handle mapping here
    df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce').fillna(0)
    
    generated_files = []
    
    # Group by Agent
    if 'Agent' not in df.columns:
        raise ValueError("Column 'Agent' not found in Excel.")

    grouped = df.groupby('Agent')
    
    for agent_name, agent_df in grouped:
        # Render HTML
        html_out = template.render(
            logo_url=logo_url,
            agent_name=agent_name,
            date=datetime.now().strftime("%B %d, %Y"),
            count=len(agent_df),
            total=agent_df['Balance'].sum(),
            clients=agent_df.to_dict(orient='records')
        )
        
        # Create PDF
        pdf_bytes = HTML(string=html_out).write_pdf()
        filename = f"Performance_{str(agent_name).replace(' ', '_')}.pdf"
        
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
