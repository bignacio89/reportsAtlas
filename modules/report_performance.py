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
            /* Critical: Force padding to stay inside the defined widths */
            * { box-sizing: border-box; }

            @page { 
                size: landscape; 
                margin: 0.8cm; 
            }
            
            body { 
                font-family: Helvetica, Arial, sans-serif; 
                font-size: 9.5px; 
                color: #333; 
                margin: 0; 
                padding: 0; 
            } 
            
            .header { 
                border-bottom: 3px solid #232ECF; 
                padding-bottom: 12px; 
                margin-bottom: 12px; 
                display: flex; 
                justify-content: space-between; 
                align-items: flex-start; 
            }
            
            .logo { max-width: 140px; }
            .header-right { text-align: right; }
            .agent-name { font-size: 16px; font-weight: bold; color: #000; margin-bottom: 2px; }
            .report-date { color: #666; font-size: 9px; margin-bottom: 8px; }
            
            .card-container { display: flex; gap: 10px; justify-content: flex-end; }
            .card { 
                background: #ffffff; 
                padding: 6px 12px; 
                border: 1px solid #e0e0e0; 
                border-radius: 6px; 
                width: 190px; 
                text-align: left;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            }
            .card small { color: #666; font-size: 8px; text-transform: uppercase; display: block; }
            .card strong { font-size: 14px; color: #000; }

            /* TABLE SETTINGS */
            table { 
                width: 100%; 
                border-collapse: collapse; 
                table-layout: fixed; /* Strictly enforces the percentages below */
                margin-top: 5px;
            }
            
            th, td {
                padding: 10px 5px; 
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                border-bottom: 1px solid #eee;
            }

            th { 
                background: #f8f9fa; 
                color: #555;
                font-weight: bold;
                text-align: right; 
                border-bottom: 2px solid #dee2e6;
                font-size: 8.5px;
                text-transform: uppercase;
            }

            /* Left-align text columns, Right-align numeric columns */
            th:nth-child(-n+4), td:nth-child(-n+4) { text-align: left; }

            /* Zebra Striping */
            tr:nth-child(even) { background-color: #fafafa; }
            
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
                    <th style="width: 30%;">Client</th>
                    <th style="width: 10%;">Account ID</th>
                    <th style="width: 15%;">Portfolio</th>
                    <th style="width: 10%;">Opened</th>
                    <th style="width: 11%;">Net Invested</th>
                    <th style="width: 12%;">Market Value</th>
                    <th style="width: 12%;">Total Return</th>
                </tr>
            </thead>
            <tbody>
                {% for client in clients %}
                <tr>
                    <td>{{ client.Name }}</td>
                    <td>{{ client['Account Number'] }}</td>
                    <td>{{ client.Portfolio or '-' }}</td>
                    <td>{{ client.Date }}</td> 
                    
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
    
    # Data Cleaning
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('-')

    numeric_cols = ['Balance', 'Net Deposit', 'Performance']
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
