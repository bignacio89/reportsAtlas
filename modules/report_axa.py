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
    AXA Report Generator
    - Updated: Removed 'Variación Patrimonial' from Product Summary
    - Includes: 'Inversión actual' swap, column reordering, and Frozen Premium KPI cards
    """
    file_date_str = report_date.strftime("%Y%m%d")
    display_date_str = report_date.strftime("%B %d, %Y")

    # 1. LOAD AGENT MAPPING FROM ASSETS
    name_map = {}
    try:
        mapping_path = Path(__file__).parent.parent / "assets" / "agentes.csv"
        if mapping_path.exists():
            df_mapping = pd.read_csv(mapping_path)
            df_mapping['code'] = df_mapping['code'].astype(str).str.strip().str.replace('.0', '', regex=False)
            name_map = dict(zip(df_mapping['code'], df_mapping['name']))
            print(f"✅ DEBUG: Loaded {len(name_map)} agents from agentes.csv")
    except Exception as e:
        print(f"❌ DEBUG: Error loading agentes.csv: {e}")

    # 2. DATA EXTRACTION & CLEANING
    df_contratos = excel_dict.get('Contratos', pd.DataFrame())
    df_clientes = excel_dict.get('Clientes', pd.DataFrame())

    if df_contratos.empty or df_clientes.empty:
        raise ValueError("El archivo AXA debe contener las hojas 'Contratos' y 'Clientes'.")

    df_contratos.columns = df_contratos.columns.str.strip()
    df_clientes.columns = df_clientes.columns.str.strip()

    # Filter for Active Contracts
    df_vigentes = df_contratos[df_contratos['Estado'] == 'Vigente'].copy()
    
    # Merge with Client names
    df_cli_sub = df_clientes[['Cartera', 'Cliente']].drop_duplicates(subset='Cartera')
    df_merged = pd.merge(df_vigentes, df_cli_sub, on='Cartera', how='left')

    # Flag paralyzed contracts
    df_merged['_paralizado'] = df_merged['Situación plan de primas'] == 'Plan de primas paralizado'

    # Detect the correct column for the Mediator/Agent
    agent_col = 'Cod. Mediador' if 'Cod. Mediador' in df_merged.columns else 'Asesor'

    # Clean numeric columns
    numeric_cols = ['Saldo actual', 'Inversión actual', 'Variación patrimonial actual', 'Prima', 'Rent. Desde inicio actual']
    for col in numeric_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

    # Clean dates
    if 'Fecha de adquisición' in df_merged.columns:
        df_merged['Fecha de adquisición'] = pd.to_datetime(df_merged['Fecha de adquisición'], errors='coerce').dt.strftime('%d/%m/%Y').fillna('-')

    # 3. HTML TEMPLATE
    html_template = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <style>
            * { box-sizing: border-box; }
            @page { size: landscape; margin: 0.8cm; }
            body { font-family: Helvetica, Arial, sans-serif; font-size: 8.5px; color: #333; margin: 0; padding: 0; } 
            
            .header { border-bottom: 3px solid #232ECF; padding-bottom: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo { max-width: 130px; margin-bottom: 5px; }
            .report-title { font-size: 12px; font-weight: bold; color: #000; text-transform: uppercase; letter-spacing: 0.5px; }
            
            .header-right { text-align: right; }
            .agent-name { font-size: 15px; font-weight: bold; color: #000; margin-bottom: 2px; }
            .report-date { color: #666; font-size: 8px; margin-bottom: 8px; }
            
            .card-container { display: flex; gap: 6px; justify-content: flex-end; }
            .card { background: #ffffff; padding: 5px 8px; border: 1px solid #e0e0e0; border-radius: 6px; min-width: 105px; text-align: left; }
            .card small { color: #666; font-size: 7px; text-transform: uppercase; display: block; line-height: 1.1; }
            .card strong { font-size: 11px; color: #000; }
            .card.alert { border-color: #cc0000; background-color: #fff5f5; }
            .card.alert strong { color: #cc0000; }

            .section-title { font-size: 10px; font-weight: bold; color: #232ECF; margin: 12px 0 4px 0; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 2px;}
            
            table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 12px; }
            th, td { padding: 5px 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; border-bottom: 1px solid #eee; }
            th { background: #f8f9fa; color: #555; font-weight: bold; border-bottom: 2px solid #dee2e6; font-size: 7.5px; text-transform: uppercase; }

            .text-left { text-align: left; }
            .text-center { text-align: center; }
            .text-right { text-align: right; }

            tr:nth-child(even) { background-color: #fafafa; }
            .positive { color: #008000; font-weight: bold; }
            .negative { color: #cc0000; font-weight: bold; }
            tr.paralizado td { background-color: #fff4e5; color: #cc5500; }
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
                <div class="report-date">Valoración: {{ date }} | Cód: {{ agent_code }}</div>
                <div class="card-container">
                    <div class="card"><small>Clientes</small><strong>{{ total_clientes }}</strong></div>
                    <div class="card"><small>Saldo Total</small><strong>{{ total_saldo | eur }}</strong></div>
                    <div class="card {% if n_paralizados > 0 %}alert{% endif %}">
                        <small>Primas Paralizadas</small><strong>{{ n_paralizados }}</strong>
                    </div>
                    <div class="card {% if total_prima_paralizada > 0 %}alert{% endif %}">
                        <small>Primas perdidas</small><strong>{{ total_prima_paralizada | eur }}</strong>
                    </div>
                </div>
            </div>
        </div>

        <div class="section-title">Resumen por Producto</div>
        <table>
            <thead>
                <tr>
                    <th class="text-left" style="width: 35%;">Producto</th>
                    <th class="text-center" style="width: 10%;">Contratos</th>
                    <th class="text-right" style="width: 18%;">Inversión Actual</th>
                    <th class="text-right" style="width: 18%;">Saldo Actual</th>
                    <th class="text-right" style="width: 19%;">Prima Mensual</th>
                </tr>
            </thead>
            <tbody>
                {% for p in productos %}
                <tr>
                    <td class="text-left">{{ p.nombre }}</td>
                    <td class="text-center">{{ p.contratos }}</td>
                    <td class="text-right">{{ p.inversion | eur }}</td>
                    <td class="text-right"><strong>{{ p.saldo | eur }}</strong></td>
                    <td class="text-right">{{ p.prima_mens | eur }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="section-title">Detalle de Contratos</div>
        <table>
            <thead>
                <tr>
                    <th class="text-left" style="width: 18%;">Cliente</th>
                    <th class="text-left" style="width: 11%;">Cartera</th>
                    <th class="text-left" style="width: 16%;">Producto</th>
                    <th class="text-center" style="width: 8%;">F. Adquisición</th>
                    <th class="text-right" style="width: 8%;">Prima</th>
                    <th class="text-center" style="width: 9%;">Periodicidad</th>
                    <th class="text-right" style="width: 10%;">Inversión Actual</th>
                    <th class="text-right" style="width: 10%;">Saldo Actual</th>
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
                    <td class="text-right">{{ c['Inversión actual'] | eur }}</td>
                    <td class="text-right"><strong>{{ c['Saldo actual'] | eur }}</strong></td>
                    <td class="text-right">
                        <span class="{% if c['Rent. Desde inicio actual'] > 0 %}positive{% elif c['Rent. Desde inicio actual'] < 0 %}negative{% endif %}">
                            {{ c['Rent. Desde inicio actual'] | pct }}
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
    
    # 4. LOOP PER AGENT
    valid_agents = df_merged.dropna(subset=[agent_col])
    for agent_code, agent_df in valid_agents.groupby(agent_col):
        
        try:
            code_key = str(int(float(agent_code)))
        except:
            code_key = str(agent_code).strip()
        
        real_name = name_map.get(code_key, f"Mediador {code_key}")

        total_prima_paralizada = agent_df.loc[agent_df['_paralizado'], 'Prima'].sum()

        # Summary by Product Calculation (Variacion removed from agg)
        prod_group = agent_df.groupby('Producto').agg(
            contratos=('Cartera', 'count'),
            saldo=('Saldo actual', 'sum'),
            inversion=('Inversión actual', 'sum'),
            prima_mens=('Prima', lambda x: x[agent_df.loc[x.index, 'Periodicidad prima'] == 'Mensual'].sum()),
        ).reset_index()

        productos_list = prod_group.rename(columns={'Producto': 'nombre'}).to_dict(orient='records')

        # Render HTML
        html_out = template.render(
            logo_url=logo_url,
            agent_display_name=real_name,
            agent_code=code_key,
            date=display_date_str,
            count=len(agent_df),
            total_clientes=agent_df['Cliente'].nunique(),
            total_saldo=agent_df['Saldo actual'].sum(),
            n_paralizados=agent_df['_paralizado'].sum(),
            total_prima_paralizada=total_prima_paralizada,
            productos=productos_list,
            contratos=agent_df.sort_values('Saldo actual', ascending=False).to_dict(orient='records')
        )
        
        pdf_bytes = HTML(string=html_out, base_url=".").write_pdf()
        
        safe_name = "".join([c for c in real_name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
        filename = f"{file_date_str}_AXA_{safe_name}.pdf"
        generated_files.append((filename, pdf_bytes))
        
    return generated_files
