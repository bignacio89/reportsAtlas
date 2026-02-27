import pandas as pd
import jinja2
from weasyprint import HTML
from .utils import currency_format 

def generate_generali_pdfs(df, logo_url, report_date):
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { box-sizing: border-box; }
            @page { size: landscape; margin: 0.8cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5px; color: #333; margin: 0; } 
            .header { border-bottom: 3px solid #232ECF; padding-bottom: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo-container { display: flex; flex-direction: column; }
            .logo { max-width: 140px; margin-bottom: 5px; }
            .report-title { font-size: 13px; font-weight: bold; color: #000; text-transform: uppercase; }
            .header-right { text-align: right; }
            .agent-name { font-size: 16px; font-weight: bold; color: #000; }
            .card-container { display: flex; gap: 10px; justify-content: flex-end; }
            .card { background: #fff; padding: 6px 12px; border: 1px solid #e0e0e0; border-radius: 6px; width: 200px; text-align: left; }
            .card small { color: #666; font-size: 8px; text-transform: uppercase; display: block; }
            .card strong { font-size: 14px; color: #000; }
            table { width: 100%; border-collapse: collapse; table-layout: fixed; }
            th, td { padding: 10px 5px; border-bottom: 1px solid #eee; }
            th { background: #f8f9fa; color: #555; font-weight: bold; border-bottom: 2px solid #dee2e6; text-transform: uppercase; }
            th:nth-child(-n+4), td:nth-child(-n+4) { text-align: left; }
            th:nth-child(n+5) { text-align: center; }
            td:nth-child(n+5) { text-align: right; }
            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo-container">
                <img src="{{ logo_url }}" class="logo">
                <div class="report-title">Cartera de Generali</div>
            </div>
            <div class="header-right">
                <div class="agent-name">{{ agent_name }}</div>
                <div class="report-date">Report Date: {{ date }}</div>
                <div class="card-container">
                    <div class="card"><small>Total Contracts</small><strong>{{ count }}</strong></div>
                    <div class="card"><small>Total Net Value</small><strong>${{ total | currency }}</strong></div>
                </div>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th style="width: 28%;">Client</th>
                    <th style="width: 12%;">Contract ID</th>
                    <th style="width: 10%;">Funds</th>
                    <th style="width: 10%;">Date</th>
                    <th style="width: 13%;">Income</th>
                    <th style="width: 14%;">Net Value</th>
                    <th style="width: 13%;">Performance</th>
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr>
                    <td>{{ row.client }}</td>
                    <td>{{ row['contract id'] }}</td>
                    <td>{{ row['number of funds'] }}</td>
                    <td>{{ row.date }}</td> 
                    <td>${{ row.income | currency }}</td>
                    <td><strong>${{ row['net value'] | currency }}</strong></td>
                    <td>
                        {% set perf = (row.performance | float * 100) | round(2) %}
                        <span class="{% if perf > 0 %}positive{% elif perf < 0 %}negative{% endif %}">
                            {{ "+" if perf > 0 }}{{ perf }}%
                        </span>
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
    
    # Process numeric columns
    for col in ['net value', 'income', 'performance']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    generated_files = []
    for agent_name, agent_df in df.groupby('agent'):
        html_out = template.render(
            logo_url=logo_url, agent_name=agent_name, date=display_date_str,
            count=len(agent_df), total=agent_df['net value'].sum(),
            data=agent_df.to_dict(orient='records')
        )
        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        filename = f"{file_date_str}_Generali_{str(agent_name).replace(' ', '_')}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
