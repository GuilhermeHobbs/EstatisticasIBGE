import pandas as pd
import requests
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import display, clear_output
import ipywidgets as widgets

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

# Data cache dictionary - avoid repeating API calls
data_cache = {}

def consultar_obitos_casados(rm_id):
    """
    Consulta a API SIDRA para obter dados da variável 343 (número de óbitos)
    para óbitos não naturais de pessoas casadas em uma região metropolitana.
    """
    # Check cache first
    cache_key = f"casados_{rm_id}"
    if cache_key in data_cache:
        return data_cache[cache_key]
    
    url = f"{API_URL}values/t/{TABELA}/v/{VARIAVEL}/p/{','.join(PERIODOS)}/c9832/{ESTADO_CIVIL_CASADO}/c1836/{NATUREZA_OBITO}/{NIVEL_TERRITORIAL}/{rm_id}/f/n"
    
    print(f"Consultando API de ÓBITOS NÃO NATURAIS PARA CASADOS (código {rm_id})...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        data_cache[cache_key] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"Erro na consulta à API: {str(e)}")
        
        # Tentativa alternativa - usando N1 (Brasil)
        try:
            url_alt = f"{API_URL}values/t/{TABELA}/v/{VARIAVEL}/p/{','.join(PERIODOS)}/c9832/{ESTADO_CIVIL_CASADO}/c1836/{NATUREZA_OBITO}/n1/1/f/n"
            resp_alt = requests.get(url_alt)
            resp_alt.raise_for_status()
            data = resp_alt.json()
            data_cache[cache_key] = data
            print("Consulta alternativa bem-sucedida (dados do Brasil)")
            return data
        except:
            print("Consulta alternativa também falhou")
            return []

def consultar_obitos_nao_casados(rm_id, estado_civil_codigo):
    """
    Consulta a API SIDRA para obter dados da variável 343 (número de óbitos)
    para óbitos não naturais de um grupo específico de não casados em uma região metropolitana.
    """
    # Check cache first
    cache_key = f"nao_casados_{rm_id}_{estado_civil_codigo}"
    if cache_key in data_cache:
        return data_cache[cache_key]
    
    url = f"{API_URL}values/t/{TABELA}/v/{VARIAVEL}/p/{','.join(PERIODOS)}/c9832/{estado_civil_codigo}/c1836/{NATUREZA_OBITO}/{NIVEL_TERRITORIAL}/{rm_id}/f/n"
    
    print(f"Consultando API para estado civil código {estado_civil_codigo} (código de região {rm_id})...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        data_cache[cache_key] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"Erro na consulta à API: {str(e)}")
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
        print("Sem dados suficientes para criar gráfico")
        return
    
    # Criar figura limpa com fundo branco
    plt.figure(figsize=(12, 6), facecolor='white')
    ax = plt.gca()
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
    plt.show()

def criar_grafico_razao(df_casados, df_nao_casados, rm_nome, rm_codigo):
    """
    Cria um gráfico mostrando a evolução da razão entre óbitos não naturais
    de não casados e casados ao longo dos anos.
    """
    if df_casados.empty or df_nao_casados.empty:
        print("Sem dados suficientes para criar gráfico de razão")
        return
    
    # Mesclar os dataframes por ano
    df_merged = pd.merge(df_casados, df_nao_casados, on='Ano', suffixes=('_casados', '_nao_casados'))
    
    # Calcular razão
    df_merged['Razao'] = df_merged['Valor_nao_casados'] / df_merged['Valor_casados']
    
    # Ordenar por ano
    df_merged = df_merged.sort_values('Ano')
    
    # Criar figura
    plt.figure(figsize=(12, 6), facecolor='white')
    ax = plt.gca()
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
    plt.show()

def carregar_dados_regiao(rm_id, rm_nome):
    """
    Carrega e processa todos os dados para uma região metropolitana.
    """
    print(f"Carregando dados para {rm_nome}...")
    
    # Consultar dados de óbitos para casados
    data_casados = consultar_obitos_casados(rm_id)
    df_casados = processar_dados(data_casados)
    
    # Para os não casados, vamos buscar cada categoria e somá-las
    df_nao_casados_total = pd.DataFrame()
    
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

    return df_casados, df_nao_casados_total

# Criando a interface com ipywidgets para uso no Colab
def criar_dashboard_ipywidgets():
    # Criar um dicionário simples para o dropdown
    regiao_nomes = {} 
    for k, v in REGIOES_METROPOLITANAS.items():
        regiao_nomes[v] = k  # Aqui invertemos para mapear nome -> código
    
    # Lista ordenada de nomes para o dropdown
    nomes_ordenados = sorted(REGIOES_METROPOLITANAS.values())
    
    # Criar dropdown para seleção da região
    dropdown_regioes = widgets.Dropdown(
        options=nomes_ordenados,
        description='Região:',
        style={'description_width': 'initial'},
        layout=widgets.Layout(width='70%')
    )
    
    # Criar botão para carregar dados
    botao_carregar = widgets.Button(
        description='Carregar Dados',
        button_style='info',
        layout=widgets.Layout(width='200px')
    )
    
    # Criar abas para os diferentes gráficos
    tabs = widgets.Tab(children=[widgets.Output(), widgets.Output(), widgets.Output()])
    tabs.set_title(0, 'Evolução Temporal')
    tabs.set_title(1, 'Razão ao Longo do Tempo')
    tabs.set_title(2, 'Dados Brutos')
    
    # Output para mensagens
    output_mensagens = widgets.Output()
    
    # Função chamada quando o botão é clicado
    def on_botao_carregar_clicked(b):
        with output_mensagens:
            clear_output()
            rm_nome = dropdown_regioes.value  # Agora pega o nome diretamente
            rm_id = regiao_nomes[rm_nome]  # Obtém o ID a partir do nome
            print(f"Carregando dados para {rm_nome} (Código {rm_id})...")
            
            # Limpar abas
            for i in range(3):
                with tabs.children[i]:
                    clear_output()
            
            # Carregar dados
            df_casados, df_nao_casados = carregar_dados_regiao(rm_id, rm_nome)
            
            # Verificar se há dados disponíveis
            if df_casados.empty and df_nao_casados.empty:
                print(f"Não há dados disponíveis para {rm_nome}. Por favor, selecione outra região.")
                return
            
            # Atualizar aba de evolução temporal
            with tabs.children[0]:
                print(f"## Evolução de Óbitos Não Naturais em {rm_nome}")
                criar_grafico_comparativo(df_casados, df_nao_casados, rm_nome, rm_id)
                print("""
                **Sobre este gráfico:**
                * A linha vermelha representa óbitos não naturais entre pessoas casadas
                * A linha azul representa óbitos não naturais entre pessoas não casadas (solteiros, viúvos, divorciados, etc.)
                * As linhas pontilhadas mostram a tendência linear para cada grupo
                * Valores são mostrados a cada 3 anos para melhor visualização
                """)
            
            # Atualizar aba de razão
            with tabs.children[1]:
                if not df_casados.empty and not df_nao_casados.empty:
                    print(f"## Razão entre Óbitos Não Naturais (Não Casados/Casados) em {rm_nome}")
                    criar_grafico_razao(df_casados, df_nao_casados, rm_nome, rm_id)
                    print("""
                    **Sobre este gráfico:**
                    * A linha roxa mostra a razão entre óbitos não naturais de pessoas não casadas e casadas
                    * Valores acima de 1 indicam mais óbitos entre não casados do que casados
                    * A linha vermelha tracejada marca o ponto de igualdade (razão = 1)
                    * Este gráfico ajuda a identificar diferenças proporcionais entre os grupos
                    """)
                else:
                    print("Não há dados suficientes para calcular a razão.")
            
            # Atualizar aba de dados brutos
            with tabs.children[2]:
                print("## Dados Brutos")
                print("\n**Óbitos Não Naturais - Pessoas Casadas:**")
                if not df_casados.empty:
                    display(df_casados.sort_values('Ano'))
                else:
                    print("Não há dados disponíveis para pessoas casadas.")
                
                print("\n**Óbitos Não Naturais - Pessoas Não Casadas:**")
                if not df_nao_casados.empty:
                    display(df_nao_casados.sort_values('Ano'))
                else:
                    print("Não há dados disponíveis para pessoas não casadas.")
            
            # Mensagem de conclusão
            print(f"Dados carregados com sucesso para {rm_nome}.")
            # Exibir a primeira aba
            tabs.selected_index = 0
    
    # Conectar função ao botão
    botao_carregar.on_click(on_botao_carregar_clicked)
    
    # Layout do dashboard
    titulo = widgets.HTML("<h2>📊 Dashboard de Análise de Óbitos Não Naturais</h2>")
    subtitulo = widgets.HTML("<h3>Comparação entre pessoas casadas e não casadas (2003-2022)</h3>")
    
    controles = widgets.VBox([
        widgets.HBox([dropdown_regioes, botao_carregar]),
        output_mensagens
    ])
    
    # Informações da fonte de dados
    fonte = widgets.HTML("""
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 20px;">
        <p><strong>Fonte dos dados:</strong></p>
        <ul>
            <li>IBGE - Pesquisa Estatísticas do Registro Civil</li>
            <li>Tabela 2683 - Óbitos, por estado civil, natureza do óbito...</li>
            <li>Dados filtrados para óbitos não naturais</li>
        </ul>
    </div>
    """)
    
    # Montar dashboard
    display(titulo)
    display(subtitulo)
    display(controles)
    display(tabs)
    display(fonte)
    
    # Mensagem inicial
    with output_mensagens:
        print("Selecione uma região metropolitana e clique em 'Carregar Dados'.")

# Executar o dashboard
criar_dashboard_ipywidgets()
