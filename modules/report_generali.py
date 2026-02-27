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
            body {
                font-family: Helvetica, Arial, sans-serif;
                font-size: 9.5px;
                color: #333;
                margin: 0;
                padding: 0;
            }

            /* ── HEADER ─────────────────────────────────────────────── */
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
            .agent-name  { font-size: 16px; font-weight: bold; color: #000; margin-bottom: 2px; }
            .report-date { color: #666; font-size: 9px; margin-bottom: 8px; }

            /* ── SUMMARY CARDS ───────────────────────────────────────── */
            .card-container { display: flex; gap: 10px; justify-content: flex-end; }
            .card {
                background: #ffffff;
                padding: 6px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                min-width: 160px;   /* grows with content instead of fixed 200px */
                width: auto;
                text-align: left;
            }
            .card small  { color: #666; font-size: 8px; text-transform: uppercase; display: block; }
            .card strong { font-size: 14px; color: #000; }

            /* ── TABLE BASE ──────────────────────────────────────────── */
            table {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                margin-top: 5px;
            }

            th, td {
                padding: 7px 5px;           /* reduced from 10px → less wasted space */
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                border-bottom: 1px solid #eee;
            }

            th {
                background: #f8f9fa;
                color: #555;
                font-weight: bold;
                border-bottom: 2px solid #dee2e6;
                font-size: 8.5px;
                text-transform: uppercase;
            }

            tr:nth-child(even) { background-color: #fafafa; }

            /* ── COLUMN WIDTHS ───────────────────────────────────────── */
            /*  Total = 94%  (6% breathing room)                         */
            th:nth-child(1), td:nth-child(1) { width: 26%; } /* Nombre Cliente  */
            th:nth-child(2), td:nth-child(2) { width: 14%; } /* Póliza          */
            th:nth-child(3), td:nth-child(3) { width:  8%; } /* Nº Fondos       */
            th:nth-child(4), td:nth-child(4) { width: 10%; } /* Fecha Emisión   */
            th:nth-child(5), td:nth-child(5) { width: 13%; } /* Capital Invertido */
            th:nth-child(6), td:nth-child(6) { width: 13%; } /* Valor Neto      */
            th:nth-child(7), td:nth-child(7) { width: 10%; } /* Rendimiento     */

            /* ── COLUMN ALIGNMENT — HEADERS ─────────────────────────── */
            th:nth-child(1) { text-align: left; }
            th:nth-child(2) { text-align: center; }
            th:nth-child(3), th:nth-child(4) { text-align: center; }
            th:nth-child(5), th:nth-child(6),
            th:nth-child(7)                  { text-align: right;  }

            /* ── COLUMN ALIGNMENT — DATA CELLS ──────────────────────── */
            td:nth-child(1), td:nth-child(2) { text-align: left;   }
            td:nth-child(3), td:nth-child(4) { text-align: center; }
            td:nth-child(5), td:nth-child(6),
            td:nth-child(7)                  { text-align: right;  }

            /* ── PERFORMANCE COLORS ──────────────────────────────────── */
            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
            .neutral  { color: #888888; }
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
                    <th>Nombre Cliente</th>
                    <th>Póliza</th>
                    <th>Nº Fondos</th>
                    <th>Fecha Emisión</th>
                    <th>Capital Invertido</th>
                    <th>Valor Neto</th>
                    <th>Rendimiento</th>
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

    # --- DATE FORMATTING ---
    if 'date' in df.columns:
        df['date'] = (
            pd.to_datetime(df['date'], errors='coerce')
            .dt.strftime('%Y-%m-%d')
            .fillna('-')
        )

    # --- NUMERIC COLUMNS ---
    numeric_cols = ['net value', 'income', 'performance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- GENERATE ONE PDF PER AGENT ---
    generated_files = []

    for agent_name, agent_df in df.groupby('agent'):
        total_net_value = agent_df['net value'].sum()

        html_out = template.render(
            logo_url=logo_url,
            agent_name=agent_name,
            date=display_date_str,
            count=len(agent_df),
            total=total_net_value,
            data=agent_df.to_dict(orient='records'),
        )

        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        safe_agent = str(agent_name).replace(' ', '_').replace('/', '-')
        filename = f"{file_date_str}_Generali_{safe_agent}.pdf"
        generated_files.append((filename, pdf_bytes))

    return generated_files
