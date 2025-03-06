import pandas as pd
import requests
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import time

# Set page configuration
st.set_page_config(
    page_title="Dashboard de Análise de Óbitos",
    page_icon="📊",
    layout="wide"
)

# Constants
API_URL = "https://apisidra.ibge.gov.br/"
TABELA = 2683  # Óbitos por estado civil, natureza do óbito, etc.
VARIAVEL = '343'  # Número de óbitos ocorridos no ano
NATUREZA_OBITO = '99818'  # Não natural
ESTADO_CIVIL_CASADO = '99197'  # Casado(a)
ESTADO_CIVIL_NAO_CASADOS = ['78090', '78092', '78093', '78094', '99195', '99217']  # Códigos para não casados
NIVEL_TERRITORIAL = 'N7'  # Região Metropolitana
PERIODOS = [str(year) for year in range(2003, 2023)]  # 2003 a 2022

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

# Initialize session state to store data
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = {}

def consultar_obitos_casados(rm_id):
    """
    Consulta a API SIDRA para obter dados da variável 343 (número de óbitos)
    para óbitos não naturais de pessoas casadas em uma região metropolitana.
    """
    # Check cache first
    cache_key = f"casados_{rm_id}"
    if cache_key in st.session_state.data_cache:
        return st.session_state.data_cache[cache_key]
    
    url = f"{API_URL}values/t/{TABELA}/v/{VARIAVEL}/p/{','.join(PERIODOS)}/c9832/{ESTADO_CIVIL_CASADO}/c1836/{NATUREZA_OBITO}/{NIVEL_TERRITORIAL}/{rm_id}/f/n"
    
    st.info(f"Consultando API de ÓBITOS NÃO NATURAIS PARA CASADOS (código {rm_id})...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        st.session_state.data_cache[cache_key] = data
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na consulta à API: {str(e)}")
        
        # Tentativa alternativa - usando N1 (Brasil)
        try:
            url_alt = f"{API_URL}values/t/{TABELA}/v/{VARIAVEL}/p/{','.join(PERIODOS)}/c9832/{ESTADO_CIVIL_CASADO}/c1836/{NATUREZA_OBITO}/n1/1/f/n"
            resp_alt = requests.get(url_alt)
            resp_alt.raise_for_status()
            data = resp_alt.json()
            st.session_state.data_cache[cache_key] = data
            st.success("Consulta alternativa bem-sucedida (dados do Brasil)")
            return data
        except:
            st.error("Consulta alternativa também falhou")
            return []

def consultar_obitos_nao_casados(rm_id, estado_civil_codigo):
    """
    Consulta a API SIDRA para obter dados da variável 343 (número de óbitos)
    para óbitos não naturais de um grupo específico de não casados em uma região metropolitana.
    """
    # Check cache first
    cache_key = f"nao_casados_{rm_id}_{estado_civil_codigo}"
    if cache_key in st.session_state.data_cache:
        return st.session_state.data_cache[cache_key]
    
    url = f"{API_URL}values/t/{TABELA}/v/{VARIAVEL}/p/{','.join(PERIODOS)}/c9832/{estado_civil_codigo}/c1836/{NATUREZA_OBITO}/{NIVEL_TERRITORIAL}/{rm_id}/f/n"
    
    st.info(f"Consultando API para estado civil código {estado_civil_codigo} (código de região {rm_id})...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        st.session_state.data_cache[cache_key] = data
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na consulta à API: {str(e)}")
        return []

def processar_dados(data, tipo="casados"):
    """
    Processa a resposta da API SIDRA e extrai anos e valores.
    """
    if not data:
        return pd.DataFrame()
    
    # Extrair pares de ano e valor
    anos_valores = []
    
    for item in data:
        try:
            # Encontrar o campo que contém o ano
            ano = None
            for key, value in item.items():
                # Os períodos estão nos anos do estudo (2003 a 2022)
                if value in PERIODOS:
                    ano = value
                    break
            
            if not ano:
                continue
                
            # Obter o valor
            valor_str = item.get('V', '0')  # Valor
            
            # Tratar caracteres especiais
            if valor_str in ['-', 'X', '..', '...']:
                continue
                
            # Converter para float
            if isinstance(valor_str, str):
                valor_str = valor_str.replace(',', '.')
            valor = float(valor_str)
            
            # Obter unidade de medida
            unidade = item.get('MN', 'Pessoas')
            
            anos_valores.append({'Ano': ano, 'Valor': valor, 'Unidade': unidade})
            
        except (ValueError, TypeError) as e:
            continue
    
    # Criar DataFrame
    df = pd.DataFrame(anos_valores)
    
    return df

def criar_grafico_comparativo(df_casados, df_nao_casados, rm_nome, rm_codigo):
    """
    Cria um gráfico comparativo mostrando a evolução dos óbitos não naturais 
    entre pessoas casadas e não casadas ao longo dos anos.
    """
    if df_casados.empty and df_nao_casados.empty:
        st.warning("Sem dados suficientes para criar gráfico")
        return
    
    # Criar figura limpa com fundo branco
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    ax.set_facecolor('white')
    
    # Definir valores mínimo e máximo para o eixo y
    min_values = []
    max_values = []
    
    # Plotar dados para casados
    if not df_casados.empty:
        df_sorted = df_casados.sort_values('Ano')
        line1 = ax.plot(df_sorted['Ano'], df_sorted['Valor'], '-', 
                      color='darkred', 
                      linewidth=2.5,
                      marker='o',
                      markersize=8,
                      label='Casados')[0]
        
        # Adicionar rótulos
        for x, y in zip(df_sorted['Ano'], df_sorted['Valor']):
            if int(x) % 3 == 0:  # Adicionar rótulos apenas a cada 3 anos para evitar sobrecarga
                ax.annotate(f'{int(y)}', 
                          xy=(x, y), 
                          xytext=(0, 10),
                          textcoords='offset points',
                          ha='center',
                          fontsize=9,
                          fontweight='bold',
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="darkred", alpha=0.7))
        
        min_values.append(df_sorted['Valor'].min())
        max_values.append(df_sorted['Valor'].max())
    
    # Plotar dados para não casados
    if not df_nao_casados.empty:
        df_sorted = df_nao_casados.sort_values('Ano')
        line2 = ax.plot(df_sorted['Ano'], df_sorted['Valor'], '-', 
                      color='navy', 
                      linewidth=2.5,
                      marker='s',
                      markersize=8,
                      label='Não Casados')[0]
        
        # Adicionar rótulos
        for x, y in zip(df_sorted['Ano'], df_sorted['Valor']):
            if int(x) % 3 == 0:  # Adicionar rótulos apenas a cada 3 anos para evitar sobrecarga
                ax.annotate(f'{int(y)}', 
                          xy=(x, y), 
                          xytext=(0, -25),
                          textcoords='offset points',
                          ha='center',
                          fontsize=9,
                          fontweight='bold',
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="navy", alpha=0.7))
        
        min_values.append(df_sorted['Valor'].min())
        max_values.append(df_sorted['Valor'].max())
    
    # Configurar título e rótulos dos eixos
    ax.set_title(f'Óbitos Não Naturais: Casados vs. Não Casados\n{rm_nome} (Código {rm_codigo})\n2003-2022', 
             fontsize=14, fontweight='bold')
    ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
    ax.set_ylabel('Número de Óbitos', fontsize=12, fontweight='bold')
    
    # Configurar ticks do eixo x para mostrar anos selecionados
    # Mostra anos a cada 3 anos para evitar sobrecarga
    anos_mostrar = [str(year) for year in range(2003, 2023, 3)]
    ax.set_xticks([int(x) for x in anos_mostrar])
    ax.set_xticklabels(anos_mostrar, rotation=45)
    
    # Calcular intervalo adequado para as linhas de grade horizontais
    if min_values and max_values:
        y_min = max(0, min(min_values) * 0.9)
        y_max = max(max_values) * 1.1
        
        # Calcular ticks adequados para as linhas horizontais
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
            
        # Criar ticks começando de um número redondo
        start = np.floor(y_min / step) * step
        ticks = np.arange(start, y_max + step, step)
        
        ax.set_ylim(y_min, y_max)
        ax.set_yticks(ticks)
    
    # Adicionar linhas de grade horizontais proeminentes
    ax.grid(axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    
    # Remover bordas superior e direita para um visual mais limpo
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Adicionar tendência para ambas as séries se houver dados suficientes
    for df, cor, nome in [(df_casados, 'darkred', 'Casados'), (df_nao_casados, 'navy', 'Não Casados')]:
        if not df.empty and len(df) > 1:
            # Converter anos para valores numéricos para cálculo de tendência
            df['Ano_Num'] = df['Ano'].astype(int)
            x = df['Ano_Num'].values
            y = df['Valor'].values
            
            # Calcular linha de tendência
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            
            # Plotar linha de tendência
            anos_num = np.array([int(ano) for ano in df['Ano']])
            ax.plot(df['Ano'], p(anos_num), '--', color=cor, linewidth=1.5, 
                   label=f'Tendência {nome}: {z[0]:.1f}/ano')
    
    # Adicionar legenda
    ax.legend(loc='best')
    
    # Adicionar texto com a razão entre não casados e casados para o último ano
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

def criar_grafico_razao(df_casados, df_nao_casados, rm_nome, rm_codigo):
    """
    Cria um gráfico mostrando a evolução da razão entre óbitos não naturais
    de não casados e casados ao longo dos anos.
    """
    if df_casados.empty or df_nao_casados.empty:
        st.warning("Sem dados suficientes para criar gráfico de razão")
        return None
    
    # Mesclar os dataframes por ano
    df_merged = pd.merge(df_casados, df_nao_casados, on='Ano', suffixes=('_casados', '_nao_casados'))
    
    # Calcular razão
    df_merged['Razao'] = df_merged['Valor_nao_casados'] / df_merged['Valor_casados']
    
    # Ordenar por ano
    df_merged = df_merged.sort_values('Ano')
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    ax.set_facecolor('white')
    
    # Plotar razão
    linha = ax.plot(df_merged['Ano'], df_merged['Razao'], '-o', color='purple', linewidth=2.5, markersize=8)
    
    # Adicionar rótulos
    for x, y in zip(df_merged['Ano'], df_merged['Razao']):
        if int(x) % 3 == 0:  # Adicionar rótulos apenas a cada 3 anos
            ax.annotate(f'{y:.1f}x', 
                      xy=(x, y), 
                      xytext=(0, 10),
                      textcoords='offset points',
                      ha='center',
                      fontsize=9,
                      fontweight='bold',
                      bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="purple", alpha=0.7))
    
    # Configurar título e rótulos
    ax.set_title(f'Razão entre Óbitos Não Naturais: Não Casados/Casados\n{rm_nome} (Código {rm_codigo})\n2003-2022', 
             fontsize=14, fontweight='bold')
    ax.set_xlabel('Ano', fontsize=12, fontweight='bold')
    ax.set_ylabel('Razão (Não Casados/Casados)', fontsize=12, fontweight='bold')
    
    # Configurar eixo x
    anos_mostrar = [str(year) for year in range(2003, 2023, 3)]
    ax.set_xticks([int(x) for x in anos_mostrar])
    ax.set_xticklabels(anos_mostrar, rotation=45)
    
    # Adicionar linha horizontal em razão = 1
    ax.axhline(y=1, color='red', linestyle='--', linewidth=1)
    
    # Adicionar grid
    ax.grid(axis='y', color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
    
    # Remover bordas
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    return fig

def carregar_dados_regiao(rm_id, rm_nome):
    """
    Carrega e processa todos os dados para uma região metropolitana.
    """
    st.info(f"Carregando dados para {rm_nome}...")
    
    # Add a progress bar
    progress_bar = st.progress(0)
    
    # Consultar dados de óbitos para casados
    data_casados = consultar_obitos_casados(rm_id)
    df_casados = processar_dados(data_casados)
    progress_bar.progress(50)
    
    # Para os não casados, vamos buscar cada categoria e somá-las
    df_nao_casados_total = pd.DataFrame()
    
    # Calculate progress step for each category
    progress_step = 50 / len(ESTADO_CIVIL_NAO_CASADOS)
    current_progress = 50
    
    for codigo in ESTADO_CIVIL_NAO_CASADOS:
        data_grupo = consultar_obitos_nao_casados(rm_id, codigo)
        df_grupo = processar_dados(data_grupo)
        
        if not df_grupo.empty:
            if df_nao_casados_total.empty:
                df_nao_casados_total = df_grupo.copy()
            else:
                # Juntar os dados por ano
                df_merged = pd.merge(df_nao_casados_total, df_grupo, on=['Ano'], how='outer')
                df_merged['Valor'] = df_merged['Valor_x'].fillna(0) + df_merged['Valor_y'].fillna(0)
                df_merged['Unidade'] = df_merged['Unidade_x'].fillna(df_merged['Unidade_y'])
                df_nao_casados_total = df_merged[['Ano', 'Valor', 'Unidade']].copy()
                
        current_progress += progress_step
        progress_bar.progress(min(int(current_progress), 100))
    
    progress_bar.progress(100)
    time.sleep(0.5)  # Small delay for UI feedback
    progress_bar.empty()  # Remove progress bar
    
    return df_casados, df_nao_casados_total

# Streamlit app main function
def main():
    # Title and subtitle
    st.title("📊 Dashboard de Análise de Óbitos Não Naturais")
    st.subheader("Comparação entre pessoas casadas e não casadas (2003-2022)")
    
    # Sidebar for region selection
    st.sidebar.header("Configurações")
    
    # Create a list of region names sorted alphabetically
    nomes_ordenados = sorted(REGIOES_METROPOLITANAS.values())
    
    # Create a mapping from names to codes
    regiao_nomes = {v: k for k, v in REGIOES_METROPOLITANAS.items()}
    
    # Region selection dropdown
    rm_nome = st.sidebar.selectbox(
        "Selecione a Região Metropolitana:",
        options=nomes_ordenados
    )
    
    rm_id = regiao_nomes[rm_nome]
    
    # Load data button
    if st.sidebar.button("Carregar Dados", type="primary"):
        with st.spinner(f"Carregando dados para {rm_nome}..."):
            df_casados, df_nao_casados = carregar_dados_regiao(rm_id, rm_nome)
            
            # Check if data is available
            if df_casados.empty and df_nao_casados.empty:
                st.error(f"Não há dados disponíveis para {rm_nome}. Por favor, selecione outra região.")
            else:
                # Create tabs for different visualizations
                tab1, tab2, tab3 = st.tabs(["Evolução Temporal", "Razão ao Longo do Tempo", "Dados Brutos"])
                
                with tab1:
                    st.header(f"Evolução de Óbitos Não Naturais em {rm_nome}")
                    fig_comp = criar_grafico_comparativo(df_casados, df_nao_casados, rm_nome, rm_id)
                    if fig_comp:
                        st.pyplot(fig_comp)
                    
                    st.markdown("""
                    **Sobre este gráfico:**
                    * A linha vermelha representa óbitos não naturais entre pessoas casadas
                    * A linha azul representa óbitos não naturais entre pessoas não casadas (solteiros, viúvos, divorciados, etc.)
                    * As linhas pontilhadas mostram a tendência linear para cada grupo
                    * Valores são mostrados a cada 3 anos para melhor visualização
                    """)
                
                with tab2:
                    if not df_casados.empty and not df_nao_casados.empty:
                        st.header(f"Razão entre Óbitos Não Naturais (Não Casados/Casados) em {rm_nome}")
                        fig_razao = criar_grafico_razao(df_casados, df_nao_casados, rm_nome, rm_id)
                        if fig_razao:
                            st.pyplot(fig_razao)
                        
                        st.markdown("""
                        **Sobre este gráfico:**
                        * A linha roxa mostra a razão entre óbitos não naturais de pessoas não casadas e casadas
                        * Valores acima de 1 indicam mais óbitos entre não casados do que casados
                        * A linha vermelha tracejada marca o ponto de igualdade (razão = 1)
                        * Este gráfico ajuda a identificar diferenças proporcionais entre os grupos
                        """)
                    else:
                        st.warning("Não há dados suficientes para calcular a razão.")
                
                with tab3:
                    st.header("Dados Brutos")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Óbitos Não Naturais - Pessoas Casadas")
                        if not df_casados.empty:
                            st.dataframe(df_casados.sort_values('Ano'), use_container_width=True)
                        else:
                            st.info("Não há dados disponíveis para pessoas casadas.")
                    
                    with col2:
                        st.subheader("Óbitos Não Naturais - Pessoas Não Casadas")
                        if not df_nao_casados.empty:
                            st.dataframe(df_nao_casados.sort_values('Ano'), use_container_width=True)
                        else:
                            st.info("Não há dados disponíveis para pessoas não casadas.")
    else:
        # Initial message when app is loaded
        st.info("👈 Selecione uma região metropolitana no painel lateral e clique em 'Carregar Dados'.")
    
    # Information about the data source
    st.sidebar.markdown("---")
    st.sidebar.subheader("Fonte dos dados:")
    st.sidebar.markdown("""
    * IBGE - Pesquisa Estatísticas do Registro Civil
    * Tabela 2683 - Óbitos, por estado civil, natureza do óbito...
    * Dados filtrados para óbitos não naturais
    """)

if __name__ == "__main__":
    main()
