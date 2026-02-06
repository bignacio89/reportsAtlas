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
            body { font-family: Helvetica, Arial, sans-serif; font-size: 10px; } 
            
            .header { border-bottom: 2px solid #232ECF; padding-bottom: 8px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo { max-width: 150px; }
            .agent-name { font-size: 16px; font-weight: bold; color: #000; }
            .report-date { color: #666; font-size: 10px; margin-bottom: 4px; }
            
            .summary-container { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
            .summary-box { background: #f9f9f9; padding: 5px 10px; border: 1px solid #e0e0e0; border-radius: 4px; min-width: 90px; }
            .summary-box small { color: #555; font-size: 9px; text-transform: uppercase; }
            .summary-box strong { display: block; font-size: 13px; color: #000; margin-top: 2px; }

            table { width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }
            
            th { 
                background: #f0f0f0; 
                color: #333;
                font-weight: bold;
                padding: 6px 3px; 
                text-align: right; 
                border-bottom: 2px solid #ccc;
                font-size: 9px;
                text-transform: uppercase;
                word-wrap: break-word;
            }
            /* Left align text columns, Right align money/perc columns */
            th:nth-child(-n+4) { text-align: left; }

            td { 
                border-bottom: 1px solid #eee; 
                padding: 5px 3px; 
                text-align: right; 
                color: #333;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            td:nth-child(-n+4) { text-align: left; }

            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
            .neutral  { color: #333; }
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{{ logo_url }}" class="logo">
            <div style="text-align: right;">
                <div class="agent-name">{{ agent_name }}</div>
                <div class="report-date">Report Date: {{ date }}</div>
                <div class="summary-container">
                    <div class="summary-box"><small>Total Accounts</small><strong>{{ count }}</strong></div>
                    <div class="summary-box"><small>Total AUM</small><strong>${{ total | currency }}</strong></div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 16%;">Client</th>
                    <th style="width: 10%;">Account ID</th>
                    <th style="width: 10%;">Portfolio</th>
                    <th style="width: 8%;">Opened</th>
                    <th style="width: 10%;">Inflows</th>
                    <th style="width: 10%;">Outflows</th>
                    <th style="width: 12%;">Net Invested</th>
                    <th style="width: 12%;">Market Value</th>
                    <th style="width: 12%;">Total Return</th>
                </tr>
            </thead>
            <tbody>
                {% for client in clients %}
                <tr>
                    <td>{{ client.Name }}</td>
                    <td>{{ client['Account Number'] }}</td>
                    <td>{{ client.Portfolio }}</td>
                    <td>{{ client.Date }}</td>
                    
                    <td>{% if client['Total Incoming'] %}${{ client['Total Incoming'] | currency }}{% else %}-{% endif %}</td>
                    <td>{% if client['Total Outgoing'] %}${{ client['Total Outgoing'] | currency }}{% else %}-{% endif %}</td>
                    <td>{% if client['Net Deposit'] %}${{ client['Net Deposit'] | currency }}{% else %}-{% endif %}</td>
                    <td>{% if client.Balance %}<strong>${{ client.Balance | currency }}</strong>{% else %}-{% endif %}</td>
                    
                    <td>
                        {% if client.Performance != '' and client.Performance is not none %}
                            {% set perf = (client.Performance | float * 100) | round(2) %}
                            <span class="{% if perf > 0 %}positive{% elif perf < 0 %}negative{% else %}neutral{% endif %}">
                                {% if perf > 0 %}+{% endif %}{{ perf }}%
                            </span>
                        {% else %}-{% endif %}
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
    
    # Pre-processing numeric columns
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
