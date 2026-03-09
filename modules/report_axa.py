import pandas as pd
import jinja2
from weasyprint import HTML

def _fmt_eur(val):
    try:
        if pd.isna(val) or val == '': return '-'
        return f"€{float(val):,.2f}"
    except (ValueError, TypeError):
        return "€0.00"

def _fmt_pct(val):
    try:
        if pd.isna(val) or val == '': return '-'
        return f"{float(val) * 100:.2f}%"
    except (ValueError, TypeError):
        return "-"

def generate_axa_pdfs(excel_dict, logo_url, report_date):
    """
    Generates PDFs for the AXA dataset.
    Expects a dictionary of DataFrames with 'Contratos' and 'Clientes' sheets.
    """
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    # 1. Extract Sheets
    df_contratos = excel_dict.get('Contratos', pd.DataFrame())
    df_clientes = excel_dict.get('Clientes', pd.DataFrame())

    if df_contratos.empty or df_clientes.empty:
        raise ValueError("El archivo AXA debe contener las hojas 'Contratos' y 'Clientes'.")

    # 2. Filter Active Contracts & Merge
    df_vigentes = df_contratos[df_contratos['Estado'] == 'Vigente'].copy()
    df_cli_sub = df_clientes[['Cartera', 'Cliente']].drop_duplicates(subset='Cartera')
    df_merged = pd.merge(df_vigentes, df_cli_sub, on='Cartera', how='left')

    # Flag paralyzed contracts
    df_merged['_paralizado'] = df_merged['Situación plan de primas'] == 'Plan de primas paralizado'

    # 3. Clean Numeric & Date Columns
    numeric_cols = ['Saldo actual', 'Importe aportaciones actual', 'Variación patrimonial actual', 'Prima', 'Rent. Desde inicio actual']
    for col in numeric_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')
            
    if 'Fecha de adquisición' in df_merged.columns:
        df_merged['Fecha de adquisición'] = pd.to_datetime(df_merged['Fecha de adquisición'], errors='coerce').dt.strftime('%d/%m/%Y').fillna('-')

    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <style>
            * { box-sizing: border-box; }
            @page { size: landscape; margin: 0.8cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 9px; color: #333; margin: 0; padding: 0; } 
            
            /* --- HEADER & CARDS --- */
            .header { border-bottom: 3px solid #232ECF; padding-bottom: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo-container { display: flex; flex-direction: column; }
            .logo { max-width: 140px; margin-bottom: 5px; }
            .report-title { font-size: 13px; font-weight: bold; color: #000; text-transform: uppercase; letter-spacing: 0.5px; }
            
            .header-right { text-align: right; }
            .agent-name { font-size: 16px; font-weight: bold; color: #000; margin-bottom: 2px; }
            .report-date { color: #666; font-size: 9px; margin-bottom: 8px; }
            
            .card-container { display: flex; gap: 8px; justify-content: flex-end; }
            .card { background: #ffffff; padding: 6px 10px; border: 1px solid #e0e0e0; border-radius: 6px; min-width: 120px; text-align: left; }
            .card small { color: #666; font-size: 8px; text-transform: uppercase; display: block; }
            .card strong { font-size: 13px; color: #000; }
            .card.alert { border-color: #cc0000; background-color: #fff5f5; }
            .card.alert strong { color: #cc0000; }

            /* --- TABLES & SECTIONS --- */
            .section-title { font-size: 11px; font-weight: bold; color: #232ECF; margin: 15px 0 5px 0; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 3px;}
            
            table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 15px; }
            th, td { padding: 6px 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; border-bottom: 1px solid #eee; }
            th { background: #f8f9fa; color: #555; font-weight: bold; border-bottom: 2px solid #dee2e6; font-size: 8px; text-transform: uppercase; }

            /* Alignment Classes */
            .text-left { text-align: left; }
            .text-center { text-align: center; }
            .text-right { text-align: right; }

            tr:nth-child(even) { background-color: #fafafa; }
            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
            
            /* Highlight Paralyzed Contracts */
            tr.paralizado td { background-color: #fff4e5; color: #cc5500; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo-container">
                <img src="{{ logo_url }}" class="logo">
                <div class="report-title">Cartera de AXA</div>
            </div>
            <div class="header-right">
                <div class="agent-name">Asesor: {{ agent_name }}</div>
                <div class="report-date">Fecha de Valoración: {{ date }}</div>
                <div class="card-container">
                    <div class="card"><small>Clientes</small><strong>{{ total_clientes }}</strong></div>
                    <div class="card"><small>Contratos Vigentes</small><strong>{{ count }}</strong></div>
                    <div class="card"><small>Saldo Total</small><strong>{{ total_saldo | eur }}</strong></div>
                    <div class="card {% if n_paralizados > 0 %}alert{% endif %}">
                        <small>Primas Paralizadas</small><strong>{{ n_paralizados }}</strong>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-title">Resumen por Producto</div>
        <table>
            <thead>
                <tr>
                    <th class="text-left" style="width: 30%;">Producto</th>
                    <th class="text-center" style="width: 10%;">Contratos</th>
                    <th class="text-right" style="width: 15%;">Saldo Actual</th>
                    <th class="text-right" style="width: 15%;">Aportaciones</th>
                    <th class="text-right" style="width: 15%;">Variación Patrim.</th>
                    <th class="text-right" style="width: 15%;">Prima Mensual</th>
                </tr>
            </thead>
            <tbody>
                {% for p in productos %}
                <tr>
                    <td class="text-left">{{ p.nombre }}</td>
                    <td class="text-center">{{ p.contratos }}</td>
                    <td class="text-right"><strong>{{ p.saldo | eur }}</strong></td>
                    <td class="text-right">{{ p.aportaciones | eur }}</td>
                    <td class="text-right">
                        <span class="{% if p.variacion > 0 %}positive{% elif p.variacion < 0 %}negative{% endif %}">
                            {{ p.variacion | eur }}
                        </span>
                    </td>
                    <td class="text-right">{{ p.prima_mens | eur }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="section-title">Detalle de Contratos</div>
        <table>
            <thead>
                <tr>
                    <th class="text-left" style="width: 16%;">Cliente</th>
                    <th class="text-left" style="width: 10%;">Cartera</th>
                    <th class="text-left" style="width: 16%;">Producto</th>
                    <th class="text-center" style="width: 9%;">F. Adquisición</th>
                    <th class="text-right" style="width: 9%;">Prima</th>
                    <th class="text-center" style="width: 10%;">Periodicidad</th>
                    <th class="text-right" style="width: 10%;">Saldo Actual</th>
                    <th class="text-right" style="width: 10%;">Aportaciones</th>
                    <th class="text-right" style="width: 10%;">Rent. Inicio</th>
                </tr>
            </thead>
            <tbody>
                {% for c in contratos %}
                <tr class="{% if c._paralizado %}paralizado{% endif %}">
                    <td class="text-left">{{ c.Cliente }}</td>
                    <td class="text-left">{{ c.Cartera }}</td>
                    <td class="text-left">{{ c.Producto }}</td>
                    <td class="text-center">{{ c['Fecha de adquisición'] }}</td>
                    <td class="text-right">{{ c.Prima | eur }}</td>
                    <td class="text-center">{{ c['Periodicidad prima'] }}</td>
                    <td class="text-right"><strong>{{ c['Saldo actual'] | eur }}</strong></td>
                    <td class="text-right">{{ c['Importe aportaciones actual'] | eur }}</td>
                    <td class="text-right">
                        {% set r_val = c['Rent. Desde inicio actual'] %}
                        {% if r_val != '' and r_val != None and r_val == r_val %}
                            <span class="{% if r_val > 0 %}positive{% elif r_val < 0 %}negative{% endif %}">
                                {{ r_val | pct }}
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
    env.filters['eur'] = _fmt_eur
    env.filters['pct'] = _fmt_pct
    template = env.from_string(html_template)
    
    generated_files = []
    
    # 4. Generate PDF per Agent
    # Clean up column names just in case there are accidental spaces in the Excel file
    df_merged.columns = df_merged.columns.str.strip()

    # Automatically detect if the file uses 'Cod. Mediador' or 'Asesor'
    if 'Cod. Mediador' in df_merged.columns:
        agent_col = 'Cod. Mediador'
    elif 'Asesor' in df_merged.columns:
        agent_col = 'Asesor'
    else:
        raise KeyError("No se encontró la columna 'Cod. Mediador' ni 'Asesor' en el archivo Excel.")

    # Drop rows where the agent column is empty
    valid_agents = df_merged.dropna(subset=[agent_col])
    
    for agent_name, agent_df in valid_agents.groupby(agent_col):
        
        # Product Grouping Logic
        prod_group = agent_df.groupby('Producto').agg(
            contratos=('Cartera', 'count'),
            saldo=('Saldo actual', 'sum'),
            aportaciones=('Importe aportaciones actual', 'sum'),
            variacion=('Variación patrimonial actual', 'sum'),
            prima_mens=('Prima', lambda x: x[agent_df.loc[x.index, 'Periodicidad prima'] == 'Mensual'].sum()),
        ).reset_index()

        productos_list = []
        for _, r in prod_group.iterrows():
            productos_list.append({
                'nombre': r['Producto'],
                'contratos': r['contratos'],
                'saldo': r['saldo'],
                'aportaciones': r['aportaciones'],
                'variacion': r['variacion'],
                'prima_mens': r['prima_mens'],
            })

        # Render HTML
        html_out = template.render(
            logo_url=logo_url,
            agent_name=int(agent_name) if isinstance(agent_name, float) else agent_name,
            date=display_date_str,
            count=len(agent_df),
            total_clientes=agent_df['Cliente'].nunique(),
            total_saldo=agent_df['Saldo actual'].sum(),
            n_paralizados=agent_df['_paralizado'].sum(),
            productos=productos_list,
            contratos=agent_df.sort_values('Saldo actual', ascending=False).to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        safe_agent = str(agent_name).replace(' ', '_').replace('/', '-')
        filename = f"{file_date_str}_AXA_{safe_agent}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
