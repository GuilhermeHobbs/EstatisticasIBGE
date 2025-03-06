import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import time
from io import BytesIO
import base64

# Set page configuration
st.set_page_config(
    page_title="SIDRA Dashboard: Óbitos Não Naturais e Divórcios",
    page_icon="📊",
    layout="wide"
)

# ===== CONSTANTS =====

# API URL
API_URL = "https://apisidra.ibge.gov.br/"

# Constants for unnatural deaths data
TABELA_OBITOS = 2683
VARIAVEL_OBITOS = '343'  # Número de óbitos ocorridos no ano
NATUREZA_OBITO = '99818'  # Não natural
ESTADO_CIVIL_CASADO = '99197'  # Casado(a)
ESTADO_CIVIL_NAO_CASADOS = ['78090', '78092', '78093', '78094', '99195', '99217']  # Códigos para não casados
PERIODOS_OBITOS = [str(year) for year in range(2003, 2023)]  # 2003 a 2022

# Constants for divorce data
TABELA_DIVORCIOS = 1695
VARIAVEL_DIVORCIOS = '393'  # Número de divórcios concedidos
TEMPO_CASAMENTOS = {
    '8074': 'Menos de 1 ano',
    '8084': '10 a 14 anos',
    '8090': '15 a 19 anos',
    '8097': '20 a 25 anos'
}
PERIODOS_DIVORCIOS = [str(year) for year in range(2009, 2023)]  # 2009 a 2022

# Defined list of metropolitan regions
REGIOES_METROPOLITANAS = {
    '2701': 'Maceió',
    '1301': 'Manaus',
    '1601': 'Macapá',
    '2901': 'Salvador',
    '2301': 'Fortaleza',
    '3201': 'Grande Vitória',
    '5201': 'Goiânia',
    '2101': 'Grande São Luís',
    '3101': 'Belo Horizonte',
    '5101': 'Vale do Rio Cuiabá',
    '1501': 'Belém',
    '2501': 'João Pessoa',
    '2601': 'Recife',
    '4101': 'Curitiba',
    '3301': 'Rio de Janeiro',
    '2401': 'Natal',
    '4301': 'Porto Alegre',
    '4201': 'Florianópolis',
    '2801': 'Aracaju',
    '3501': 'São Paulo'
}

# Color schemes for graphs
COLORS = {
    'casados': 'darkred',
    'nao_casados': 'navy',
    'obitos': 'purple',
    'menos_1_ano': '#1f77b4',  # Blue
    '10_14_anos': '#ff7f0e',   # Orange
    '15_19_anos': '#2ca02c',   # Green
    '20_25_anos': '#d62728'    # Red
}

# ===== SESSION STATE FOR CACHING =====
if 'cached_data' not in st.session_state:
    st.session_state.cached_data = {}

# ===== API REQUEST AND DATA PROCESSING FUNCTIONS =====

def consultar_obitos_casados(rm_id, rm_nome):
    """
    Consulta a API SIDRA para obter dados da variável 343 (número de óbitos)
    para óbitos não naturais de pessoas casadas em uma região metropolitana.
    """
    url = f"{API_URL}values/t/{TABELA_OBITOS}/v/{VARIAVEL_OBITOS}/p/{','.join(PERIODOS_OBITOS)}/c9832/{ESTADO_CIVIL_CASADO}/c1836/{NATUREZA_OBITO}/n7/{rm_id}/f/n"
    
    st.info(f"Consultando dados de óbitos não naturais para casados em {rm_nome}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro na consulta: {str(e)}")
        
        # Tentativa alternativa - usando N1 (Brasil)
        try:
            url_alt = f"{API_URL}values/t/{TABELA_OBITOS}/v/{VARIAVEL_OBITOS}/p/{','.join(PERIODOS_OBITOS)}/c9832/{ESTADO_CIVIL_CASADO}/c1836/{NATUREZA_OBITO}/n1/1/f/n"
            resp_alt = requests.get(url_alt)
            resp_alt.raise_for_status()
            st.info("Usando dados de Brasil como alternativa")
            return resp_alt.json()
        except:
            return []

def consultar_obitos_nao_casados(rm_id, rm_nome, estado_civil_codigo):
    """
    Consulta a API SIDRA para obter dados da variável 343 (número de óbitos)
    para óbitos não naturais de um grupo específico de não casados em uma região metropolitana.
    """
    url = f"{API_URL}values/t/{TABELA_OBITOS}/v/{VARIAVEL_OBITOS}/p/{','.join(PERIODOS_OBITOS)}/c9832/{estado_civil_codigo}/c1836/{NATUREZA_OBITO}/n7/{rm_id}/f/n"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro na consulta: {str(e)}")
        return []

def consultar_divorcios(rm_id, rm_nome, tempo_codigo):
    """
    Consulta a API SIDRA para obter dados da variável 393 (número de divórcios)
    para um tempo específico entre casamento e divórcio em uma região metropolitana.
    """
    url = f"{API_URL}values/t/{TABELA_DIVORCIOS}/v/{VARIAVEL_DIVORCIOS}/p/{','.join(PERIODOS_DIVORCIOS)}/c345/{tempo_codigo}/n7/{rm_id}/f/n"
    
    st.info(f"Consultando dados de divórcios ({TEMPO_CASAMENTOS.get(tempo_codigo, tempo_codigo)}) para {rm_nome}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro na consulta: {str(e)}")
        
        # Tentativa alternativa - usando N1 (Brasil)
        try:
            url_alt = f"{API_URL}values/t/{TABELA_DIVORCIOS}/v/{VARIAVEL_DIVORCIOS}/p/{','.join(PERIODOS_DIVORCIOS)}/c345/{tempo_codigo}/n1/1/f/n"
            resp_alt = requests.get(url_alt)
            resp_alt.raise_for_status()
            st.info("Usando dados de Brasil como alternativa")
            return resp_alt.json()
        except:
            return []

def processar_dados(data, tipo_dados=""):
    """
    Processa a resposta da API SIDRA e extrai anos e valores.
    """
    if not data:
        st.warning(f"Sem dados para {tipo_dados}")
        return pd.DataFrame()
    
    # Extract year-value pairs
    anos_valores = []
    
    for item in data:
        try:
            # Find the field containing the year
            ano = None
            for key, value in item.items():
                if key.startswith('D') and value in PERIODOS_OBITOS + PERIODOS_DIVORCIOS:
                    ano = value
                    break
            
            if not ano:
                continue
                
            # Get the value
            valor_str = item.get('V', '0')
            
            # Handle special characters
            if valor_str in ['-', 'X', '..', '...']:
                continue
                
            # Convert to float
            if isinstance(valor_str, str):
                valor_str = valor_str.replace(',', '.')
            valor = float(valor_str)
            
            # Get unit of measurement
            unidade = item.get('MN', '')
            
            anos_valores.append({'Ano': ano, 'Valor': valor, 'Unidade': unidade})
            
        except (ValueError, TypeError) as e:
            continue
    
    # Create DataFrame
    df = pd.DataFrame(anos_valores)
    
    # Check if we have data
    if df.empty:
        st.warning(f"Nenhum dado válido encontrado para {tipo_dados}")
        return df
    
    return df

# ===== VISUALIZATION FUNCTIONS =====

def criar_grafico_obitos(df_casados, df_nao_casados, rm_nome, rm_codigo):
    """
    Cria um gráfico comparativo mostrando a evolução dos óbitos não naturais 
    entre pessoas casadas e não casadas ao longo dos anos.
    """
    if df_casados.empty and df_nao_casados.empty:
        st.warning(f"Sem dados para criar gráfico para {rm_nome}")
        return None
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')
    ax.set_facecolor('white')
    
    # Define years to plot
    all_years = set()
    if not df_casados.empty:
        all_years.update(df_casados['Ano'])
    if not df_nao_casados.empty:
        all_years.update(df_nao_casados['Ano'])
    
    all_years = sorted(list(all_years))
    
    # Define min and max values for y-axis
    min_values = []
    max_values = []
    
    # Plot data for married people
    if not df_casados.empty:
        df_sorted = df_casados.sort_values('Ano')
        line1 = ax.plot(df_sorted['Ano'], df_sorted['Valor'], '-', 
                      color=COLORS['casados'], 
                      linewidth=2.5,
                      marker='o',
                      markersize=8,
                      label='Casados')[0]
        
        # Add labels
        for x, y in zip(df_sorted['Ano'], df_sorted['Valor']):
            if int(x) % 3 == 0:  # Add labels every 3 years to avoid clutter
                ax.annotate(f'{int(y)}', 
                          xy=(x, y), 
                          xytext=(0, 10),
                          textcoords='offset points',
                          ha='center',
                          fontsize=9,
                          fontweight='bold',
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=COLORS['casados'], alpha=0.7))
        
        min_values.append(df_sorted['Valor'].min())
        max_values.append(df_sorted['Valor'].max())
    
    # Plot data for non-married people
    if not df_nao_casados.empty:
        df_sorted = df_nao_casados.sort_values('Ano')
        line2 = ax.plot(df_sorted['Ano'], df_sorted['Valor'], '-', 
                      color=COLORS['nao_casados'], 
                      linewidth=2.5,
                      marker='s',
                      markersize=8,
                      label='Não Casados')[0]
        
        # Add labels
        for x, y in zip(df_sorted['Ano'], df_sorted['Valor']):
            if int(x) % 3 == 0:  # Add labels every 3 years to avoid clutter
                ax.annotate(f'{int(y)}', 
                          xy=(x, y), 
                          xytext=(0, -25),
                          textcoords='offset points',
                          ha='center',
                          fontsize=9,
                          fontweight='bold',
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=COLORS['nao_casados'], alpha=0.7))
        
        min_values.append(df_sorted['Valor'].min())
        max_values.append(df_sorted['Valor'].max())
    
    # Configure title and axis labels
    plt.title(f'Óbitos Não Naturais: Casados vs. Não Casados\n{rm_nome} (Código {rm_codigo})\n2003-2022', 
             fontsize=14, fontweight='bold')
    plt.xlabel('Ano', fontsize=12, fontweight='bold')
    plt.ylabel('Número de Óbitos', fontsize=12, fontweight='bold')
    
    # Configure x-axis ticks
    anos_mostrar = [str(year) for year in range(2003, 2023, 3)]
    plt.xticks(anos_mostrar, anos_mostrar, rotation=45, fontsize=10)
    
    # Calculate appropriate range for y-axis
    if min_values and max_values:
        y_min = max(0, min(min_values) * 0.9)
        y_max = max(max_values) * 1.1
        
        # Calculate appropriate ticks for horizontal grid lines
        range_size = y_max - y_min
        if range_size <= 10:
            step = 1
        elif range_size <= 50:
            step = 5
        elif range_size <= 100:
            step = 10
        elif range_size <= 500:
            step = 50
        else:
            step = 100
            
        # Create ticks starting from a round number
        start = np.floor(y_min / step) * step
        ticks = np.arange(start, y_max + step, step)
        
        plt.ylim(y_min, y_max)
        plt.yticks(ticks, fontsize=10)
    
    # Add prominent horizontal grid lines
    plt.grid(axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add trend lines for both series if there is enough data
    for df, cor, nome in [(df_casados, COLORS['casados'], 'Casados'), (df_nao_casados, COLORS['nao_casados'], 'Não Casados')]:
        if not df.empty and len(df) > 1:
            # Convert years to numeric values for trend calculation
            df['Ano_Num'] = df['Ano'].astype(int)
            x = df['Ano_Num'].values
            y = df['Valor'].values
            
            # Calculate trend line
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            
            # Plot trend line
            anos_num = np.array([int(ano) for ano in df['Ano']])
            ax.plot(df['Ano'], p(anos_num), '--', color=cor, linewidth=1.5, 
                   label=f'Tendência {nome}: {z[0]:.1f}/ano')
    
    # Add legend
    plt.legend(loc='best', fontsize=10)
    
    # Add text with the ratio between non-married and married for the last year
    if not df_casados.empty and not df_nao_casados.empty:
        ultimo_ano_casados = df_casados.sort_values('Ano').iloc[-1]
        ultimo_ano_nao_casados = df_nao_casados.sort_values('Ano').iloc[-1]
        
        if ultimo_ano_casados['Ano'] == ultimo_ano_nao_casados['Ano'] and ultimo_ano_casados['Valor'] > 0:
            razao = ultimo_ano_nao_casados['Valor'] / ultimo_ano_casados['Valor']
            texto_razao = f"Razão Não Casados/Casados em {ultimo_ano_casados['Ano']}: {razao:.1f}x"
            plt.figtext(0.15, 0.02, texto_razao, ha='left', fontsize=11, 
                       color='black', weight='bold',
                       bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2'))
    
    plt.tight_layout()
    return fig

def criar_grafico_casamentos_obitos(df_nao_casados, df_divorcios_dict, rm_nome, rm_codigo):
    """
    Cria um gráfico comparativo mostrando a evolução dos óbitos não naturais de não casados
    em comparação com os divórcios por tempo de casamento.
    
    IMPORTANTE: Usa apenas dados de óbitos de NÃO CASADOS.
    """
    # Check if we have at least some data
    has_divorcio_data = any(not df.empty for df in df_divorcios_dict.values())
    
    if df_nao_casados.empty and not has_divorcio_data:
        st.warning(f"Sem dados para criar gráfico para {rm_nome}")
        return None
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7), facecolor='white')
    ax.set_facecolor('white')
    
    # Define years to plot (common range: 2009-2022)
    anos_comuns = PERIODOS_DIVORCIOS
    
    # Define min and max values for y-axis
    min_values = []
    max_values = []
    
    # Dictionary to hold line objects for the legend
    lines = {}
    
    # Plot data for unnatural deaths (only non-married people)
    if not df_nao_casados.empty:
        # Filter to common years (2009-2022)
        df_filtered = df_nao_casados[df_nao_casados['Ano'].isin(anos_comuns)]
        
        if not df_filtered.empty:
            df_sorted = df_filtered.sort_values('Ano')
            line = ax.plot(df_sorted['Ano'], df_sorted['Valor'], '-', 
                          color=COLORS['obitos'], 
                          linewidth=3,
                          marker='o',
                          markersize=8,
                          label='Óbitos Não Naturais (Não Casados)')[0]
            
            lines['Óbitos Não Naturais (Não Casados)'] = line
            
            # Add labels
            for x, y in zip(df_sorted['Ano'], df_sorted['Valor']):
                if int(x) % 3 == 0:  # Add labels every 3 years to avoid clutter
                    ax.annotate(f'{int(y)}', 
                              xy=(x, y), 
                              xytext=(0, 10),
                              textcoords='offset points',
                              ha='center',
                              fontsize=9,
                              fontweight='bold',
                              bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=COLORS['obitos'], alpha=0.7))
            
            min_values.append(df_sorted['Valor'].min())
            max_values.append(df_sorted['Valor'].max())
    
    # Plot data for divorces by marriage duration
    tempos_labels = {
        '8074': 'Menos de 1 ano',
        '8084': '10 a 14 anos',
        '8090': '15 a 19 anos',
        '8097': '20 a 25 anos'
    }
    
    tempos_cores = {
        '8074': COLORS['menos_1_ano'],
        '8084': COLORS['10_14_anos'],
        '8090': COLORS['15_19_anos'],
        '8097': COLORS['20_25_anos']
    }
    
    for tempo_codigo, df_divorcios in df_divorcios_dict.items():
        if df_divorcios.empty:
            continue
            
        label = tempos_labels.get(tempo_codigo, tempo_codigo)
        cor = tempos_cores.get(tempo_codigo, 'gray')
        
        df_sorted = df_divorcios.sort_values('Ano')
        line = ax.plot(df_sorted['Ano'], df_sorted['Valor'], '-', 
                      color=cor, 
                      linewidth=2,
                      marker='s',
                      markersize=6,
                      label=f'Divórcios: {label}')[0]
        
        lines[f'Divórcios: {label}'] = line
        
        # Add labels for some key years
        for x, y in zip(df_sorted['Ano'], df_sorted['Valor']):
            if x in ['2009', '2015', '2022']:  # Label only at beginning, middle, end
                ax.annotate(f'{int(y)}', 
                          xy=(x, y), 
                          xytext=(0, -15),
                          textcoords='offset points',
                          ha='center',
                          fontsize=8,
                          bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=cor, alpha=0.7))
        
        min_values.append(df_sorted['Valor'].min())
        max_values.append(df_sorted['Valor'].max())
    
    # Configure title and axis labels
    plt.title(f'Evolução dos Casamentos Curtos x Óbitos Não-naturais (Não Casados)\n{rm_nome} (Código {rm_codigo})\n2009-2022', 
             fontsize=14, fontweight='bold')
    plt.xlabel('Ano', fontsize=12, fontweight='bold')
    plt.ylabel('Número de Ocorrências', fontsize=12, fontweight='bold')
    
    # Configure x-axis ticks
    anos_mostrar = [str(year) for year in range(2009, 2023, 2)]
    plt.xticks(anos_mostrar, anos_mostrar, rotation=45, fontsize=10)
    
    # Calculate appropriate range for y-axis
    if min_values and max_values:
        y_min = max(0, min(min_values) * 0.9)
        y_max = max(max_values) * 1.1
        
        # Calculate appropriate ticks for horizontal grid lines
        range_size = y_max - y_min
        if range_size <= 10:
            step = 1
        elif range_size <= 50:
            step = 5
        elif range_size <= 100:
            step = 10
        elif range_size <= 500:
            step = 50
        else:
            step = 100
            
        # Create ticks starting from a round number
        start = np.floor(y_min / step) * step
        ticks = np.arange(start, y_max + step, step)
        
        plt.ylim(y_min, y_max)
        plt.yticks(ticks, fontsize=10)
    
    # Add prominent horizontal grid lines
    plt.grid(axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add legend with only the lines that were actually plotted
    if lines:
        plt.legend(handles=list(lines.values()), labels=list(lines.keys()), 
                 loc='best', fontsize=10)
    
    plt.tight_layout()
    return fig

# ===== DATA FETCHING FUNCTION =====

def get_data_for_region(rm_id, rm_nome, status_placeholder):
    """
    Get data from cache or fetch it if not available.
    Returns dict with all data for the location.
    """
    if rm_id in st.session_state.cached_data:
        status_placeholder.info(f"Usando dados em cache para {rm_nome}")
        return st.session_state.cached_data[rm_id]
    
    status_placeholder.info(f"Buscando dados para {rm_nome} (Código {rm_id})...")
    location_data = {}
    
    # Get deaths data for married people
    data_casados = consultar_obitos_casados(rm_id, rm_nome)
    df_casados = processar_dados(data_casados, "óbitos casados")
    location_data['obitos_casados'] = df_casados
    
    # Wait to avoid overwhelming the API
    time.sleep(1)
    
    # Get deaths data for non-married people (aggregate of all categories)
    df_nao_casados_total = pd.DataFrame()
    
    for codigo in ESTADO_CIVIL_NAO_CASADOS:
        status_placeholder.info(f"Obtendo dados para estado civil código {codigo}...")
        data_grupo = consultar_obitos_nao_casados(rm_id, rm_nome, codigo)
        df_grupo = processar_dados(data_grupo, f"óbitos estado civil {codigo}")
        
        if not df_grupo.empty:
            if df_nao_casados_total.empty:
                df_nao_casados_total = df_grupo.copy()
            else:
                # Merge data by year
                df_merged = pd.merge(df_nao_casados_total, df_grupo, on=['Ano'], how='outer')
                df_merged['Valor'] = df_merged['Valor_x'].fillna(0) + df_merged['Valor_y'].fillna(0)
                df_merged['Unidade'] = df_merged['Unidade_x'].fillna(df_merged['Unidade_y'])
                df_nao_casados_total = df_merged[['Ano', 'Valor', 'Unidade']].copy()
        
        # Wait to avoid overwhelming the API
        time.sleep(1)
    
    location_data['obitos_nao_casados'] = df_nao_casados_total
    
    # Get divorce data by marriage duration
    for tempo_codigo in TEMPO_CASAMENTOS.keys():
        data_divorcios = consultar_divorcios(rm_id, rm_nome, tempo_codigo)
        df_divorcios = processar_dados(data_divorcios, f"divórcios {TEMPO_CASAMENTOS[tempo_codigo]}")
        location_data[f'divorcios_{tempo_codigo}'] = df_divorcios
        
        # Wait to avoid overwhelming the API
        time.sleep(1)
    
    # Cache the data
    st.session_state.cached_data[rm_id] = location_data
    
    status_placeholder.success(f"Dados carregados com sucesso para {rm_nome}")
    return location_data

# ===== MAIN APP =====

def main():
    # Main title
    st.title("Dashboard Interativo - IBGE SIDRA")
    
    # Description
    st.markdown("### Análise de Óbitos Não Naturais e Divórcios por Região Metropolitana")
    
    # Add some app information
    with st.expander("Sobre este dashboard"):
        st.markdown("""
        Este dashboard utiliza dados da API SIDRA do IBGE para visualizar:
        - **Óbitos não naturais** por estado civil (casados vs. não casados)
        - **Divórcios** por tempo de casamento
        
        Os dados são organizados por Região Metropolitana e abrangem os períodos:
        - Óbitos: 2003-2022
        - Divórcios: 2009-2022
        
        Fonte dos dados: [API SIDRA - IBGE](https://apisidra.ibge.gov.br/)
        """)
    
    # Region selector
    st.markdown("## Selecione uma Região Metropolitana")
    
    # Create sidebar for selections
    st.sidebar.title("Controles")
    
    # Convert RM dictionary to list for sorting
    regioes_lista = [(k, v) for k, v in REGIOES_METROPOLITANAS.items()]
    regioes_lista.sort(key=lambda x: x[1])  # Sort by name
    
    # Create dropdown options
    opcoes_regioes = [(k, v) for k, v in regioes_lista]
    
    # Region selector in sidebar
    rm_selecionada = st.sidebar.selectbox(
        "Região Metropolitana:",
        options=[k for k, v in opcoes_regioes],
        format_func=lambda x: REGIOES_METROPOLITANAS[x],
    )
    
    # Status placeholder
    status_placeholder = st.empty()
    
    # Only proceed if a region is selected
    if rm_selecionada:
        rm_nome = REGIOES_METROPOLITANAS[rm_selecionada]
        
        # Get data for the selected region
        data = get_data_for_region(rm_selecionada, rm_nome, status_placeholder)
        
        # Create tabs
        tab1, tab2, tab3 = st.tabs([
            "Óbitos: Casados vs. Não Casados", 
            "Casamentos Curtos vs. Óbitos Não Casados",
            "Dados Brutos"
        ])
        
        with tab1:
            st.header("Comparação de Óbitos Não Naturais: Casados vs. Não Casados")
            
            # Create and display the first graph
            fig1 = criar_grafico_obitos(
                data.get('obitos_casados', pd.DataFrame()),
                data.get('obitos_nao_casados', pd.DataFrame()),
                rm_nome, rm_selecionada
            )
            
            if fig1:
                st.pyplot(fig1)
            else:
                st.warning("Não foi possível gerar o gráfico devido a dados insuficientes.")
        
        with tab2:
            st.header("Evolução dos Casamentos Curtos x Óbitos Não-naturais (Não Casados)")
            
            # Get divorce data for each marriage duration category
            divorcios_dict = {
                '8074': data.get('divorcios_8074', pd.DataFrame()),
                '8084': data.get('divorcios_8084', pd.DataFrame()),
                '8090': data.get('divorcios_8090', pd.DataFrame()),
                '8097': data.get('divorcios_8097', pd.DataFrame())
            }
            
            # Create and display the second graph
            fig2 = criar_grafico_casamentos_obitos(
                data.get('obitos_nao_casados', pd.DataFrame()),  # Only non-married deaths
                divorcios_dict,
                rm_nome, rm_selecionada
            )
            
            if fig2:
                st.pyplot(fig2)
            else:
                st.warning("Não foi possível gerar o gráfico devido a dados insuficientes.")
        
        with tab3:
            st.header("Dados Brutos")
            
            # Show raw data tables
            st.subheader("Óbitos Não Naturais - Pessoas Casadas")
            if not data.get('obitos_casados', pd.DataFrame()).empty:
                st.dataframe(data['obitos_casados'].sort_values('Ano'))
            else:
                st.info("Não há dados disponíveis.")
                
            st.subheader("Óbitos Não Naturais - Pessoas Não Casadas")
            if not data.get('obitos_nao_casados', pd.DataFrame()).empty:
                st.dataframe(data['obitos_nao_casados'].sort_values('Ano'))
            else:
                st.info("Não há dados disponíveis.")
            
            # Add download options for data
            st.subheader("Baixar dados")
            
            # Function to convert dataframe to CSV for download
            def convert_df_to_csv(df):
                return df.to_csv(index=False).encode('utf-8')
            
            # Create download buttons for each dataset
            col1, col2 = st.columns(2)
            
            with col1:
                if not data.get('obitos_casados', pd.DataFrame()).empty:
                    csv_casados = convert_df_to_csv(data['obitos_casados'])
                    st.download_button(
                        label="Download dados de óbitos (casados)",
                        data=csv_casados,
                        file_name=f'obitos_casados_{rm_nome}.csv',
                        mime='text/csv',
                    )
            
            with col2:
                if not data.get('obitos_nao_casados', pd.DataFrame()).empty:
                    csv_nao_casados = convert_df_to_csv(data['obitos_nao_casados'])
                    st.download_button(
                        label="Download dados de óbitos (não casados)",
                        data=csv_nao_casados,
                        file_name=f'obitos_nao_casados_{rm_nome}.csv',
                        mime='text/csv',
                    )
            
            # Display divorce data
            st.subheader("Dados de Divórcio por Tempo de Casamento")
            
            # Create tabs for different marriage durations
            divorcio_tabs = st.tabs([
                "Menos de 1 ano", 
                "10 a 14 anos",
                "15 a 19 anos",
                "20 a 25 anos"
            ])
            
            tempo_codigos = ['8074', '8084', '8090', '8097']
            
            for i, tab in enumerate(divorcio_tabs):
                with tab:
                    tempo_cod = tempo_codigos[i]
                    df_div = data.get(f'divorcios_{tempo_cod}', pd.DataFrame())
                    
                    if not df_div.empty:
                        st.dataframe(df_div.sort_values('Ano'))
                        
                        # Add download button
                        csv_div = convert_df_to_csv(df_div)
                        st.download_button(
                            label=f"Download dados de divórcios ({TEMPO_CASAMENTOS[tempo_cod]})",
                            data=csv_div,
                            file_name=f'divorcios_{tempo_cod}_{rm_nome}.csv',
                            mime='text/csv',
                        )
                    else:
                        st.info("Não há dados disponíveis.")

    # Footer with credits
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center">
        <p>Desenvolvido com Streamlit • Dados: SIDRA-IBGE</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
