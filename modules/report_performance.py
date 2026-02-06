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
                min-width: 180px;
                text-align: left;
                box-shadow: 0 2px 4px rgba(0,0,0,0.03);
            }
            .card small { color: #666; font-size: 9px; text-transform: uppercase; display: block; margin-bottom: 4px; }
            .card strong { font-size: 15px; color: #000; }

            /* Table Styles */
            table { width: 100%; border-collapse: collapse; margin-top: 5px; table-layout: fixed; }
            
            th { 
                background: #f8f9fa; 
                color: #555;
                font-weight: bold;
                padding: 10px 5px; 
                text-align: right; 
                border-bottom: 2px solid #dee2e6;
                font-size: 9px;
                text-transform: uppercase;
                white-space: nowrap; /* Prevent headers from wrapping */
            }
            th:nth-child(-n+4) { text-align: left; }

            td { 
                padding: 10px 5px; 
                text-align: right; 
                border-bottom: 1px solid #eee;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            td:nth-child(-n+4) { text-align: left; }

            /* Zebra Striping */
            tr:nth-child(even) { background-color: #fafafa; }

            /* Alignment for last column */
            th:last-child, td:last-child { padding-right: 10px; }

            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{{ logo_url }}" class="logo">
            <div class="header-right">
                <div class="agent-name">{{ agent_name }}</div>
                <div class="report-date">Report Date: {{ date }}</div>
                <div class="card-container">
                    <div class="card">
                        <small>Total Accounts</small>
                        <strong>{{ count }}</strong>
                    </div>
                    <div class="card">
                        <small>Total AUM</small>
                        <strong>${{ total | currency }}</strong>
                    </div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 15%;">Client</th>
                    <th style="width: 8%;">Account ID</th> <th style="width: 9%;">Portfolio</th>  <th style="width: 7%;">Opened</th>     <th style="width: 11%;">Inflows</th>   <th style="width: 11%;">Outflows</th>  <th style="width: 13%;">Net Invested</th> <th style="width: 13%;">Market Value</th> <th style="width: 13%;">Total Return</th> </tr>
            </thead>
            <tbody>
                {% for client in clients %}
                <tr>
                    <td>{{ client.Name }}</td>
                    <td>{{ client['Account Number'] }}</td>
                    <td>{{ client.Portfolio or '-' }}</td>
                    <td>{{ client.Date }}</td> 
                    
                    <td>{% if client['Total Incoming'] %}${{ client['Total Incoming'] | currency }}{% else %}-{% endif %}</td>
                    <td>{% if client['Total Outgoing'] %}${{ client['Total Outgoing'] | currency }}{% else %}-{% endif %}</td>
                    <td>{% if client['Net Deposit'] %}${{ client['Net Deposit'] | currency }}{% else %}-{% endif %}</td>
                    <td>{% if client.Balance %}<strong>${{ client.Balance | currency }}</strong>{% else %}-{% endif %}</td>
                    
                    <td>
                        {% if client.Performance != '' and client.Performance is not none and client.Performance == client.Performance %}
                            {% set perf = (client.Performance | float * 100) | round(2) %}
                            <span class="{% if perf > 0 %}positive{% elif perf < 0 %}negative{% endif %}">
                                {% if perf > 0 %}+{% endif %}{{ perf }}%
                            </span>
                        {% else %}
                            -
                        {% endif %}
                    </td>
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
    
    # --- Data Cleaning ---
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('-')

    numeric_cols = ['Balance', 'Total Incoming', 'Total Outgoing', 'Net Deposit', 'Performance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    generated_files = []
    grouped = df.groupby('Agent')
    
    for agent_name, agent_df in grouped:
        total_balance = agent_df['Balance'].sum()
        
        html_out = template.render(
            logo_url=logo_url,
            agent_name=agent_name,
            date=display_date_str,
            count=len(agent_df),
            total=total_balance,
            clients=agent_df.to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out).write_pdf()
        safe_agent = str(agent_name).replace(' ', '_').replace('/', '-')
        filename = f"{file_date_str}_Performance_{safe_agent}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
