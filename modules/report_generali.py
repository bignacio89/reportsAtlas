import pandas as pd
import jinja2
from weasyprint import HTML
from .utils import currency_format 

def generate_generali_pdfs(df, logo_url, report_date):
    """
    Generates PDFs for the Generali dataset with formatted dates.
    """
    
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { box-sizing: border-box; }
            @page { size: landscape; margin: 0.8cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5px; color: #333; margin: 0; padding: 0; } 
            
            .header { 
                border-bottom: 3px solid #232ECF; 
                padding-bottom: 12px; 
                margin-bottom: 12px; 
                display: flex; 
                justify-content: space-between; 
                align-items: flex-end; 
            }
            
            .logo-container { display: flex; flex-direction: column; }
            .logo { max-width: 140px; margin-bottom: 5px; }
            
            .report-title { 
                font-size: 13px; 
                font-weight: bold; 
                color: #000; 
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .header-right { text-align: right; }
            .agent-name { font-size: 16px; font-weight: bold; color: #000; margin-bottom: 2px; }
            .report-date { color: #666; font-size: 9px; margin-bottom: 8px; }
            
            .card-container { display: flex; gap: 10px; justify-content: flex-end; }
            .card { 
                background: #ffffff; 
                padding: 6px 12px; 
                border: 1px solid #e0e0e0; 
                border-radius: 6px; 
                width: 200px; 
                text-align: left;
            }
            .card small { color: #666; font-size: 8px; text-transform: uppercase; display: block; }
            .card strong { font-size: 14px; color: #000; }

            table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 5px; }
            th, td { padding: 10px 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; border-bottom: 1px solid #eee; }
            th { background: #f8f9fa; color: #555; font-weight: bold; border-bottom: 2px solid #dee2e6; font-size: 8.5px; text-transform: uppercase; }

            th:nth-child(-n+4), td:nth-child(-n+4) { text-align: left; }
            th:nth-child(n+5) { text-align: center; }
            td:nth-child(n+5) { text-align: right; }

            tr:nth-child(even) { background-color: #fafafa; }
            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo-container">
                <img src="{{ logo_url }}" class="logo">
                <div class="report-title">Resumen de Cartera de Inversiones - GENERALI</div>
            </div>
            <div class="header-right">
                <div class="agent-name">{{ agent_name }}</div>
                <div class="report-date">Fecha de Reporte: {{ date }}</div>
                <div class="card-container">
                    <div class="card">
                        <small>Total de Contratos</small>
                        <strong>{{ count }}</strong>
                    </div>
                    <div class="card">
                        <small>Valor Neto Total</small>
                        <strong>${{ total | currency }}</strong>
                    </div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 28%;">Nombre Cliente</th>
                    <th style="width: 12%;">Póliza</th>
                    <th style="width: 10%;">Nº Fondos</th>
                    <th style="width: 10%;">Fecha Emisión</th>
                    <th style="width: 13%;">Capital Invertido</th>
                    <th style="width: 14%;">Valor Neto</th>
                    <th style="width: 13%;">Rendimiento</th>
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr>
                    <td>{{ row.client }}</td>
                    <td>{{ row['contract id'] }}</td>
                    <td>{{ row['number of funds'] }}</td>
                    <td>{{ row.date }}</td> 
                    <td>{% if row.income %}${{ row.income | currency }}{% else %}-{% endif %}</td>
                    <td>{% if row['net value'] %}<strong>${{ row['net value'] | currency }}</strong>{% else %}-{% endif %}</td>
                    <td>
                        {% if row.performance != '' and row.performance is not none %}
                            {% set perf = (row.performance | float * 100) | round(2) %}
                            <span class="{% if perf > 0 %}positive{% elif perf < 0 %}negative{% endif %}">
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
    
    # --- DATE FIX START ---
    if 'date' in df.columns:
        # 1. Convert to datetime objects
        # 2. Format specifically to YYYY-MM-DD
        # 3. Cast as string to prevent Pandas/Jinja from re-adding the time
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('-')
    # --- DATE FIX END ---

    numeric_cols = ['net value', 'income', 'performance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    generated_files = []
    grouped = df.groupby('agent')
    
    for agent_name, agent_df in grouped:
        total_net_value = agent_df['net value'].sum()
        
        html_out = template.render(
            logo_url=logo_url,
            agent_name=agent_name,
            date=display_date_str,
            count=len(agent_df),
            total=total_net_value,
            data=agent_df.to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        safe_agent = str(agent_name).replace(' ', '_').replace('/', '-')
        filename = f"{file_date_str}_Generali_{safe_agent}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
