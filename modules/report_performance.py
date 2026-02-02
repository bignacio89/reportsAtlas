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
            @page { size: landscape; margin: 1.0cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 11px; }
            .header { border-bottom: 2px solid #232ECF; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo { max-width: 160px; }
            .agent-name { font-size: 18px; font-weight: bold; color: #000; }
            .report-date { color: #666; font-size: 11px; margin-bottom: 5px; }
            .summary-container { display: flex; gap: 10px; justify-content: flex-end; margin-top: 5px; }
            .summary-box { background: #f9f9f9; padding: 6px 12px; border: 1px solid #e0e0e0; border-radius: 4px; min-width: 100px; }
            .summary-box small { color: #555; font-size: 10px; text-transform: uppercase; }
            .summary-box strong { display: block; font-size: 14px; color: #000; margin-top: 2px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th { background: #f0f0f0; color: #333; font-weight: bold; padding: 8px 4px; text-align: right; border-bottom: 2px solid #ccc; font-size: 10px; text-transform: uppercase; }
            th:nth-child(1), th:nth-child(2) { text-align: left; }
            td { border-bottom: 1px solid #eee; padding: 6px 4px; text-align: right; color: #333; }
            td:nth-child(1), td:nth-child(2) { text-align: left; }
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
                    <th style="width: 20%;">Client</th>
                    <th style="width: 10%;">Account ID</th>
                    <th style="width: 12%;">Inflows</th>
                    <th style="width: 12%;">Outflows</th>
                    <th style="width: 12%;">Net Invested</th>
                    <th style="width: 12%;">Market Value</th>
                    <th style="width: 10%;">Total Return</th>
                </tr>
            </thead>
            <tbody>
                {% for client in clients %}
                <tr>
                    <td>{{ client.Name }}</td>
                    <td>{{ client['Account Number'] }}</td>
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
                        {% else %} - {% endif %}
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
    
    numeric_cols = ['Balance', 'Total Incoming', 'Total Outgoing', 'Net Deposit', 'Performance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    generated_files = []
    
    if 'Agent' not in df.columns:
        raise ValueError("Column 'Agent' not found in Excel.")

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
