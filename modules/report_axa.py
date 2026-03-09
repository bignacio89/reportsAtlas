import pandas as pd
import jinja2
import os
from weasyprint import HTML
from pathlib import Path

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
    Generates PDFs for AXA. Loads agent names from assets/agentes.csv
    """
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    # 1. Load Data
    df_contratos = excel_dict.get('Contratos', pd.DataFrame())
    df_clientes = excel_dict.get('Clientes', pd.DataFrame())

    if df_contratos.empty or df_clientes.empty:
        raise ValueError("El archivo AXA debe contener las hojas 'Contratos' y 'Clientes'.")

    # 2. Load Agent Mapping from Assets
    try:
        mapping_path = Path(__file__).parent.parent / "assets" / "agentes.csv"
        df_mapping = pd.read_csv(mapping_path)
        # Ensure codes are strings for clean matching
        df_mapping['code'] = df_mapping['code'].astype(str).str.strip()
        name_map = dict(zip(df_mapping['code'], df_mapping['name']))
    except Exception as e:
        print(f"Warning: Could not load assets/agentes.csv: {e}")
        name_map = {}

    # 3. Merge and Clean
    df_vigentes = df_contratos[df_contratos['Estado'] == 'Vigente'].copy()
    df_vigentes.columns = df_vigentes.columns.str.strip()
    
    # Merge Client names
    df_cli_sub = df_clientes[['Cartera', 'Cliente']].drop_duplicates(subset='Cartera')
    df_merged = pd.merge(df_vigentes, df_cli_sub, on='Cartera', how='left')

    # Detect Agent Column
    agent_col = 'Cod. Mediador' if 'Cod. Mediador' in df_merged.columns else 'Asesor'
    
    # 4. Numeric Formatting
    numeric_cols = ['Saldo actual', 'Importe aportaciones actual', 'Variación patrimonial actual', 'Prima', 'Rent. Desde inicio actual']
    for col in numeric_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')
            
    if 'Fecha de adquisición' in df_merged.columns:
        df_merged['Fecha de adquisición'] = pd.to_datetime(df_merged['Fecha de adquisición'], errors='coerce').dt.strftime('%d/%m/%Y').fillna('-')

    # --- HTML TEMPLATE ---
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { box-sizing: border-box; }
            @page { size: landscape; margin: 0.8cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 9px; color: #333; } 
            .header { border-bottom: 3px solid #232ECF; padding-bottom: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo { max-width: 140px; }
            .report-title { font-size: 13px; font-weight: bold; color: #000; text-transform: uppercase; }
            .header-right { text-align: right; }
            .agent-name { font-size: 16px; font-weight: bold; color: #000; }
            .card-container { display: flex; gap: 8px; justify-content: flex-end; margin-top: 5px; }
            .card { background: #fff; padding: 6px 10px; border: 1px solid #e0e0e0; border-radius: 6px; min-width: 110px; text-align: left; }
            .card small { color: #666; font-size: 7px; text-transform: uppercase; display: block; }
            .card strong { font-size: 12px; color: #000; }
            table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }
            th { background: #f8f9fa; color: #555; font-size: 8px; text-transform: uppercase; padding: 6px 4px; border-bottom: 2px solid #dee2e6; }
            td { padding: 6px 4px; border-bottom: 1px solid #eee; }
            .text-right { text-align: right; }
            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <img src="{{ logo_url }}" class="logo">
                <div class="report-title">Cartera de AXA</div>
            </div>
            <div class="header-right">
                <div class="agent-name">{{ agent_display_name }}</div>
                <div class="card-container">
                    <div class="card"><small>Clientes</small><strong>{{ total_clientes }}</strong></div>
                    <div class="card"><small>Saldo Total</small><strong>{{ total_saldo | eur }}</strong></div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="text-align:left; width: 25%;">Cliente</th>
                    <th style="text-align:left; width: 15%;">Cartera</th>
                    <th style="text-align:left; width: 20%;">Producto</th>
                    <th class="text-right" style="width: 12%;">Saldo Actual</th>
                    <th class="text-right" style="width: 14%;">Inversión</th>
                    <th class="text-right" style="width: 14%;">Rent. Inicio</th>
                </tr>
            </thead>
            <tbody>
                {% for c in contratos %}
                <tr>
                    <td>{{ c.Cliente }}</td>
                    <td>{{ c.Cartera }}</td>
                    <td>{{ c.Producto }}</td>
                    <td class="text-right"><strong>{{ c['Saldo actual'] | eur }}</strong></td>
                    <td class="text-right">{{ c['Importe aportaciones actual'] | eur }}</td>
                    <td class="text-right">
                        {% set r_val = c['Rent. Desde inicio actual'] %}
                        <span class="{% if r_val > 0 %}positive{% elif r_val < 0 %}negative{% endif %}">
                            {{ r_val | pct }}
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
    env.filters['eur'] = _fmt_eur
    env.filters['pct'] = _fmt_pct
    template = env.from_string(html_template)
    
    generated_files = []
    
    valid_agents = df_merged.dropna(subset=[agent_col])
    for agent_code, agent_df in valid_agents.groupby(agent_col):
        
        # Determine Display Name
        code_key = str(int(agent_code)) if isinstance(agent_code, (int, float)) else str(agent_code)
        real_name = name_map.get(code_key, f"Cod: {code_key}")
        
        html_out = template.render(
            logo_url=logo_url,
            agent_display_name=real_name,
            total_clientes=agent_df['Cliente'].nunique(),
            total_saldo=agent_df['Saldo actual'].sum(),
            contratos=agent_df.sort_values('Saldo actual', ascending=False).to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        
        # Clean name for filename
        clean_name = "".join([c for c in real_name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
        filename = f"{file_date_str}_AXA_{clean_name}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
