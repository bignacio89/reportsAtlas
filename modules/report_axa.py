import pandas as pd
import jinja2
import os
import streamlit as st
from weasyprint import HTML
from pathlib import Path

# --- FORMATTING HELPERS ---
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
    Generates PDFs for AXA with built-in 3-step debugging.
    """
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    # ---------------------------------------------------------
    # DEBUG STEP 1: LOAD AGENTES.CSV
    # ---------------------------------------------------------
    name_map = {}
    try:
        # Calculate path: modules/../assets/agentes.csv
        mapping_path = Path(__file__).parent.parent / "assets" / "agentes.csv"
        
        if not mapping_path.exists():
            st.error(f"DEBUG: File NOT FOUND at {mapping_path.absolute()}")
            print(f"❌ DEBUG: File NOT FOUND at {mapping_path.absolute()}")
        else:
            df_mapping = pd.read_csv(mapping_path)
            # Clean codes: Remove decimals, spaces, and force to string
            df_mapping['code'] = df_mapping['code'].astype(str).str.strip().str.replace('.0', '', regex=False)
            name_map = dict(zip(df_mapping['code'], df_mapping['name']))
            print(f"✅ DEBUG: Loaded {len(name_map)} agents from CSV.")
            print(f"✅ DEBUG: First 3 keys in Map: {list(name_map.keys())[:3]}")
    except Exception as e:
        st.error(f"DEBUG: Error loading agentes.csv: {e}")
        print(f"❌ DEBUG: Error loading agentes.csv: {e}")

    # ---------------------------------------------------------
    # DATA PREPARATION
    # ---------------------------------------------------------
    df_contratos = excel_dict.get('Contratos', pd.DataFrame())
    df_clientes = excel_dict.get('Clientes', pd.DataFrame())

    if df_contratos.empty or df_clientes.empty:
        raise ValueError("El archivo AXA debe contener las hojas 'Contratos' y 'Clientes'.")

    # Clean Excel column names
    df_contratos.columns = df_contratos.columns.str.strip()
    
    # DEBUG STEP 2: CHECK EXCEL COLUMNS
    print(f"🔍 DEBUG: Excel Columns found: {df_contratos.columns.tolist()}")

    # Merge logic
    df_vigentes = df_contratos[df_contratos['Estado'] == 'Vigente'].copy()
    df_cli_sub = df_clientes[['Cartera', 'Cliente']].drop_duplicates(subset='Cartera')
    df_merged = pd.merge(df_vigentes, df_cli_sub, on='Cartera', how='left')

    # Detect column for Agent
    if 'Cod. Mediador' in df_merged.columns:
        agent_col = 'Cod. Mediador'
    elif 'Asesor' in df_merged.columns:
        agent_col = 'Asesor'
    else:
        st.error("No se encontró 'Cod. Mediador' ni 'Asesor' en el Excel.")
        return []

    # Numeric Cleanup
    numeric_cols = ['Saldo actual', 'Importe aportaciones actual', 'Rent. Desde inicio actual']
    for col in numeric_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')

    # HTML Template
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
            .agent-code { font-size: 10px; color: #666; }
            .card-container { display: flex; gap: 8px; justify-content: flex-end; margin-top: 5px; }
            .card { background: #fff; padding: 6px 10px; border: 1px solid #e0e0e0; border-radius: 6px; min-width: 110px; text-align: left; }
            .card small { color: #666; font-size: 7px; text-transform: uppercase; display: block; }
            .card strong { font-size: 12px; color: #000; }
            table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }
            th { background: #f8f9fa; color: #555; font-size: 8px; text-transform: uppercase; padding: 6px 4px; border-bottom: 2px solid #dee2e6; text-align: left; }
            td { padding: 6px 4px; border-bottom: 1px solid #eee; text-align: left; }
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
                <div class="agent-code">Código Mediador: {{ agent_code }}</div>
                <div class="card-container">
                    <div class="card"><small>Clientes</small><strong>{{ total_clientes }}</strong></div>
                    <div class="card"><small>Saldo Total</small><strong>{{ total_saldo | eur }}</strong></div>
                </div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 25%;">Cliente</th>
                    <th style="width: 15%;">Cartera</th>
                    <th style="width: 20%;">Producto</th>
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

    # ---------------------------------------------------------
    # DEBUG STEP 3: MAPPING IN THE LOOP
    # ---------------------------------------------------------
    for agent_code, agent_df in valid_agents.groupby(agent_col):
        
        # Clean the key from Excel (Convert 758578.0 -> "758578")
        try:
            code_key = str(int(float(agent_code)))
        except:
            code_key = str(agent_code).strip()
        
        real_name = name_map.get(code_key)
        
        if real_name:
            print(f"🎯 MATCH FOUND: {code_key} -> {real_name}")
            display_name = real_name
        else:
            print(f"⚠️ NO MATCH: Code '{code_key}' not in agentes.csv")
            display_name = f"Agente {code_key}" # Fallback so it's not blank

        html_out = template.render(
            logo_url=logo_url,
            agent_display_name=display_name,
            agent_code=code_key,
            total_clientes=agent_df['Cliente'].nunique(),
            total_saldo=agent_df['Saldo actual'].sum(),
            contratos=agent_df.sort_values('Saldo actual', ascending=False).to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        
        # Clean name for filename
        clean_name = "".join([c for c in display_name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
        filename = f"{file_date_str}_AXA_{clean_name}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
