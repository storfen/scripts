import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import plotly.express as px
import plotly.graph_objects as go
import time
from typing import List, Dict, Any, Tuple
import json

# Set page config
st.set_page_config(
    page_title="B3 Market View",
    page_icon="📈",
    layout="wide"
)

# Constants
API_BASE_URL = "https://api.oplab.com.br/v3"
HEADERS = {"Access-Token": ""}

# API endpoint map
API_ENDPOINTS = {
    "options_for_stock": "/market/options/{symbol}",
    "stock_details": "/market/stocks/{symbol}"
}

# Utility function to display pretty error messages
def display_api_message(status_code):
    if status_code == 200:
        return "Success"
    elif status_code == 204:
        return "No content available (204) - The request was successful but there's no data to return"
    elif status_code == 400:
        return "Bad request (400) - The request was improperly formatted or contains invalid parameters"
    elif status_code == 401:
        return "Unauthorized (401) - Invalid or missing API key. Please check your API key"
    elif status_code == 403:
        return "Forbidden (403) - Your API key doesn't have permission to access this resource"
    elif status_code == 404:
        return "Not found (404) - The requested resource doesn't exist"
    elif status_code == 429:
        return "Rate limit exceeded (429) - You've made too many requests. Please wait and try again later"
    elif status_code >= 500:
        return f"Server error ({status_code}) - There's an issue with the OpLab API server"
    else:
        return f"Unknown error ({status_code})"

# Function to get all stocks with options
def get_stocks_with_options():
    # Default list of popular Brazilian stocks that typically have options
    default_stocks = [
         {"symbol": "PETR4"},  # Petrobras
    {"symbol": "PETR3"},  # Petrobras
    {"symbol": "VALE3"},  # Vale
    {"symbol": "ITUB4"},  # Itaú Unibanco
    {"symbol": "BBDC4"},  # Bradesco
    {"symbol": "ABEV3"},  # Ambev
    {"symbol": "BBAS3"},  # Banco do Brasil
    {"symbol": "MGLU3"},  # Magazine Luiza
    {"symbol": "WEGE3"},  # WEG
    {"symbol": "ITSA4"},  # Itaúsa
    {"symbol": "B3SA3"},  # B3
    {"symbol": "RENT3"},  # Localiza
    {"symbol": "BBSE3"},  # BB Seguridade
    {"symbol": "ELET3"},  # Eletrobras
    {"symbol": "ELET6"},  # Eletrobras
    {"symbol": "JBSS3"},  # JBS
    {"symbol": "LREN3"},  # Lojas Renner
    {"symbol": "RADL3"},  # RaiaDrogasil
    {"symbol": "SUZB3"},  # Suzano
    {"symbol": "VIVT3"},  # Telefônica Brasil
    {"symbol": "ENEV3"},  # Eneva
    {"symbol": "BPAC11"},  # Banco BTG Pactual
    {"symbol": "BRKM5"},  # Braskem
    {"symbol": "VBBR3"},  # Vibra Energia
    {"symbol": "PRIO3"},  # PetroRio
    {"symbol": "CSNA3"},  # Companhia Siderúrgica Nacional
    {"symbol": "CYRE3"},  # Cyrela
    {"symbol": "EQTL3"},  # Equatorial Energia
    {"symbol": "HYPE3"},  # Equatorial Energia
    {"symbol": "GGBR4"}  # Gerdau
    ]
    
    return default_stocks

# Function to get stock details
def get_stock_details(symbol: str, timeout: int = 10):
    url = f"{API_BASE_URL}/market/stocks/{symbol}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            print(f"Sem dados para a ação {symbol} (204 No Content)")
            return None
        elif response.status_code == 401:
            print(f"Falha de autenticação para {symbol}: {display_api_message(response.status_code)}")
            return None
        else:
            print(f"Falha ao obter dados para {symbol}: {display_api_message(response.status_code)}")
            return None
    except requests.exceptions.Timeout:
        print(f"Timeout ao buscar dados para {symbol}. A API demorou muito para responder.")
        return None
    except Exception as e:
        print(f"Erro ao buscar dados para {symbol}: {str(e)}")
        return None

# Function to get sector distribution data from stocks
def get_sector_distribution(stocks_data):
    sector_counts = {}
    
    for stock in stocks_data:
        sector = stock.get('sector', 'Desconhecido')
        if sector in sector_counts:
            sector_counts[sector] += 1
        else:
            sector_counts[sector] = 1
    
    return sector_counts

# Function to get performance data (winners/losers)
def get_performance_data(stocks_data):
    # Sort by variation
    winners = sorted(stocks_data, key=lambda x: x.get('variation', 0), reverse=True)[:10]
    losers = sorted(stocks_data, key=lambda x: x.get('variation', 0))[:10]
    
    # Create formatted DataFrames
    winners_df = pd.DataFrame([
        {
            'Símbolo': stock.get('symbol', ''),
            'Nome': stock.get('name', ''),
            'Preço': stock.get('close', 0),
            'Var (%)': stock.get('variation', 0),
            'Volume': stock.get('volume', 0),
            'Vol. Fin.': stock.get('financial_volume', 0)
        } for stock in winners
    ])
    
    losers_df = pd.DataFrame([
        {
            'Símbolo': stock.get('symbol', ''),
            'Nome': stock.get('name', ''),
            'Preço': stock.get('close', 0),
            'Var (%)': stock.get('variation', 0),
            'Volume': stock.get('volume', 0),
            'Vol. Fin.': stock.get('financial_volume', 0)
        } for stock in losers
    ])
    
    return winners_df, losers_df

# Function to get liquidity data
def get_liquidity_data(stocks_data):
    # Sort by financial volume
    most_liquid = sorted(stocks_data, key=lambda x: x.get('financial_volume', 0), reverse=True)[:15]
    
    # Create DataFrame
    liquid_df = pd.DataFrame([
        {
            'Símbolo': stock.get('symbol', ''),
            'Nome': stock.get('name', ''),
            'Preço': stock.get('close', 0),
            'Var (%)': stock.get('variation', 0),
            'Volume': stock.get('volume', 0),
            'Vol. Fin.': stock.get('financial_volume', 0),
            'Bid': stock.get('bid', 0),
            'Ask': stock.get('ask', 0)
        } for stock in most_liquid
    ])
    
    return liquid_df

# Function to get volatility data
def get_volatility_data(stocks_data):
    # Sort by current volatility
    high_vol = sorted(stocks_data, key=lambda x: x.get('ewma_current', 0), reverse=True)[:10]
    
    # Create DataFrame
    vol_df = pd.DataFrame([
        {
            'Símbolo': stock.get('symbol', ''),
            'Nome': stock.get('name', ''),
            'Preço': stock.get('close', 0),
            'Var (%)': stock.get('variation', 0),
            'Vol. Atual': stock.get('ewma_current', 0),
            'Vol. Min (6m)': stock.get('ewma_6m_min', 0),
            'Vol. Max (6m)': stock.get('ewma_6m_max', 0),
            'Perc. Vol.': stock.get('ewma_6m_percentile', 0)
        } for stock in high_vol
    ])
    
    return vol_df

# Function to format DataFrame for display
def format_dataframe(df):
    """Format DataFrame for better display"""
    result = df.copy()
    
    # Format columns
    if 'Preço' in result.columns:
        result['Preço'] = result['Preço'].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "N/A")
    
    if 'Var (%)' in result.columns:
        result['Var (%)'] = result['Var (%)'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    if 'Volume' in result.columns:
        result['Volume'] = result['Volume'].apply(lambda x: f"{x/1000:.1f}K" if pd.notnull(x) and x > 0 else "N/A")
    
    if 'Vol. Fin.' in result.columns:
        result['Vol. Fin.'] = result['Vol. Fin.'].apply(lambda x: f"R$ {x/1000000:.2f}M" if pd.notnull(x) and x > 0 else "N/A")
    
    if 'Bid' in result.columns:
        result['Bid'] = result['Bid'].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "N/A")
    
    if 'Ask' in result.columns:
        result['Ask'] = result['Ask'].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "N/A")
    
    if 'Vol. Atual' in result.columns:
        result['Vol. Atual'] = result['Vol. Atual'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    if 'Vol. Min (6m)' in result.columns:
        result['Vol. Min (6m)'] = result['Vol. Min (6m)'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    if 'Vol. Max (6m)' in result.columns:
        result['Vol. Max (6m)'] = result['Vol. Max (6m)'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    if 'Perc. Vol.' in result.columns:
        result['Perc. Vol.'] = result['Perc. Vol.'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
    
    return result

# Function to get sector data
def get_sector_data(stocks_data):
    # Group by sector
    sector_data = {}
    
    for stock in stocks_data:
        sector = stock.get('sector', 'Desconhecido')
        variation = stock.get('variation', 0)
        volume = stock.get('financial_volume', 0)
        
        if sector in sector_data:
            sector_data[sector]['stocks'] += 1
            sector_data[sector]['total_variation'] += variation
            sector_data[sector]['total_volume'] += volume
        else:
            sector_data[sector] = {
                'stocks': 1,
                'total_variation': variation,
                'total_volume': volume
            }
    
    # Calculate averages and create DataFrame
    sector_df = pd.DataFrame([
        {
            'Setor': sector,
            'Ações': data['stocks'],
            'Variação Média (%)': data['total_variation'] / data['stocks'],
            'Volume Total': data['total_volume'],
            'Volume Médio': data['total_volume'] / data['stocks']
        } for sector, data in sector_data.items() if data['stocks'] > 0
    ])
    
    # Sort by variation
    sector_df = sector_df.sort_values('Variação Média (%)', ascending=False)
    
    return sector_df

# Function to create a heatmap of sectors by performance
def create_sector_heatmap(sector_df):
    # Create custom color scale for the heatmap
    color_scale = [
        [0, 'red'],         # Negative values
        [0.5, 'white'],     # Zero
        [1, 'green']        # Positive values
    ]
    
    # Find min and max variation for scaling
    min_var = sector_df['Variação Média (%)'].min()
    max_var = sector_df['Variação Média (%)'].max()
    
    # Normalize values around zero
    max_abs = max(abs(min_var), abs(max_var))
    
    # Create the heatmap figure
    fig = go.Figure(go.Heatmap(
        z=[[val] for val in sector_df['Variação Média (%)']],
        y=sector_df['Setor'],
        x=['Variação Média (%)'],
        colorscale=color_scale,
        zmid=0,
        zmin=-max_abs,
        zmax=max_abs,
        colorbar=dict(title='Variação (%)'),
        text=[[f"{val:.2f}%" for val in sector_df['Variação Média (%)']]]
    ))
    
    fig.update_layout(
        title='Performance por Setor',
        height=500,
        margin=dict(l=10, r=10, b=10, t=40)
    )
    
    return fig

# Function to create a plotly market summary visualization
def create_market_summary(stocks_data):
    # Count stocks with positive/negative/neutral variation
    positive = sum(1 for stock in stocks_data if stock.get('variation', 0) > 0)
    negative = sum(1 for stock in stocks_data if stock.get('variation', 0) < 0)
    neutral = sum(1 for stock in stocks_data if stock.get('variation', 0) == 0)
    
    # Create labels and values for pie chart
    labels = ['Em Alta', 'Em Baixa', 'Estável']
    values = [positive, negative, neutral]
    colors = ['green', 'red', 'gray']
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        textinfo='value+percent',
        marker=dict(colors=colors),
        hole=0.4
    )])
    
    fig.update_layout(
        title='Sentimento do Mercado',
        height=350,
        annotations=[dict(text=f'Total: {sum(values)}', x=0.5, y=0.5, font_size=15, showarrow=False)]
    )
    
    return fig

# Function to create a volatility index chart
def create_volatility_chart(stocks_data):
    # Calculate average current volatility
    volatilities = [stock.get('ewma_current', 0) for stock in stocks_data if 'ewma_current' in stock]
    avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0
    
    # Create gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_volatility,
        title={'text': "Índice Médio de Volatilidade (%)"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "royalblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgreen"},
                {'range': [25, 50], 'color': "lightyellow"},
                {'range': [50, 75], 'color': "orange"},
                {'range': [75, 100], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': avg_volatility
            }
        }
    ))
    
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, b=10, t=30)
    )
    
    return fig, avg_volatility

# Function to create sector volume chart
def create_sector_volume_chart(sector_df):
    # Sort by volume
    sorted_df = sector_df.sort_values('Volume Total', ascending=False)
    
    # Create bar chart
    fig = go.Figure(go.Bar(
        x=sorted_df['Setor'],
        y=sorted_df['Volume Total'] / 1e9,  # Convert to billions
        text=[f"R$ {val/1e9:.2f}B" for val in sorted_df['Volume Total']],
        textposition='auto',
        marker_color='royalblue'
    ))
    
    fig.update_layout(
        title='Volume Negociado por Setor (R$ Bilhões)',
        xaxis_title='Setor',
        yaxis_title='Volume (R$ Bilhões)',
        height=400,
        margin=dict(l=10, r=10, b=120, t=40),
        xaxis={'categoryorder':'total descending'}
    )
    
    # Rotate x axis labels for better display
    fig.update_layout(xaxis_tickangle=-45)
    
    return fig

# Function to create a beta comparison chart
def create_beta_chart(stocks_data):
    # Get top 15 stocks by volume with beta data
    top_stocks = sorted(stocks_data, key=lambda x: x.get('financial_volume', 0), reverse=True)[:15]
    
    # Create chart data
    beta_df = pd.DataFrame([
        {
            'Ação': stock.get('symbol', ''),
            'Beta': stock.get('beta_ibov', 0),
            'Volume': stock.get('financial_volume', 0) / 1e9  # Convert to billions
        } for stock in top_stocks if 'beta_ibov' in stock
    ])
    
    # Sort by beta
    beta_df = beta_df.sort_values('Beta', ascending=False)
    
    # Create bar chart
    fig = go.Figure()
    
    # Add reference line for market (beta = 1)
    fig.add_shape(
        type="line",
        x0=-0.5,
        y0=1,
        x1=len(beta_df) - 0.5,
        y1=1,
        line=dict(color="red", width=2, dash="dash")
    )
    
    # Add bars
    fig.add_trace(go.Bar(
        x=beta_df['Ação'],
        y=beta_df['Beta'],
        text=[f"{val:.2f}" for val in beta_df['Beta']],
        textposition='auto',
        marker_color=['red' if b > 1 else 'green' for b in beta_df['Beta']],
        marker_line_color='rgb(8,48,107)',
        marker_line_width=1.5,
        opacity=0.8
    ))
    
    fig.update_layout(
        title='Beta em Relação ao Ibovespa (Principais Ações)',
        xaxis_title='Ação',
        yaxis_title='Beta',
        height=400,
        margin=dict(l=10, r=10, b=10, t=40),
    )
    
    return fig

# Function to create a correlation matrix
def create_correlation_matrix(stocks_data):
    # Get top stocks by volume for correlation analysis
    top_stocks = sorted(stocks_data, key=lambda x: x.get('financial_volume', 0), reverse=True)[:10]
    
    # Extract necessary data
    correlation_data = {
        stock.get('symbol'): [
            stock.get('correl_ibov', 0),
            stock.get('beta_ibov', 0),
            stock.get('variation', 0),
            stock.get('ewma_current', 0)
        ] for stock in top_stocks if 'correl_ibov' in stock and 'beta_ibov' in stock
    }
    
    # Create DataFrame
    if correlation_data:
        df = pd.DataFrame.from_dict(correlation_data, orient='index', 
                                   columns=['Correlação Ibov', 'Beta', 'Variação (%)', 'Volatilidade (%)'])
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=df.values,
            x=df.columns,
            y=df.index,
            colorscale='RdBu_r',
            zmid=0,
            text=[[f"{val:.2f}" for val in row] for row in df.values],
            texttemplate="%{text}",
            textfont={"size":10}
        ))
        
        fig.update_layout(
            title='Matriz de Correlação e Beta (Principais Ações)',
            height=500,
            margin=dict(l=10, r=10, b=10, t=40)
        )
        
        return fig
    
    return None

# Main Streamlit app
st.title("📊 B3 Market View - Dashboard")
st.markdown("""
Este dashboard fornece uma visão geral do mercado brasileiro (B3), exibindo dados em tempo real de ações, 
setores, volatilidade e tendências de mercado.
""")

# Sidebar for API Key and settings
st.sidebar.header("🔑 Configurações da API")
api_key = st.sidebar.text_input("Chave API OpLab", type="password", 
                               help="Insira sua chave API para acessar os dados da B3")

if api_key:
    HEADERS["Access-Token"] = api_key
else:
    st.sidebar.warning("⚠️ É necessário inserir uma chave API válida para visualizar os dados")

# Stock selection in sidebar
st.sidebar.header("⚙️ Configurações do Dashboard")
default_stocks = get_stocks_with_options()
default_symbols = [stock["symbol"] for stock in default_stocks]

selected_stocks = st.sidebar.multiselect(
    "Selecionar Ações (opcional)",
    options=default_symbols,
    default=[],
    help="Deixe vazio para ver todas as ações principais ou selecione ações específicas"
)

num_stocks = st.sidebar.slider(
    "Número Máximo de Ações a Analisar", 
    min_value=10, 
    max_value=100, 
    value=40,
    help="Limitar o número de ações analisadas melhora a performance"
)

# Data refresh control
refresh_interval = st.sidebar.selectbox(
    "Intervalo de Atualização",
    options=["Manual", "1 minuto", "5 minutos", "15 minutos", "30 minutos"],
    index=0,
    help="Escolha com que frequência os dados serão atualizados automaticamente"
)

# Convert refresh interval to seconds
refresh_seconds = 0
if refresh_interval == "1 minuto":
    refresh_seconds = 60
elif refresh_interval == "5 minutos":
    refresh_seconds = 300
elif refresh_interval == "15 minutos":
    refresh_seconds = 900
elif refresh_interval == "30 minutos":
    refresh_seconds = 1800

# Display options
show_advanced_charts = st.sidebar.checkbox("Mostrar Gráficos Avançados", value=True,
                                          help="Exibe gráficos adicionais de correlação e beta")

show_volatility_section = st.sidebar.checkbox("Mostrar Seção de Volatilidade", value=True,
                                             help="Exibe dados detalhados de volatilidade")

# Function to load market data
@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_market_data(symbols=None, max_stocks=40):
    if not api_key:
        return None
    
    with st.spinner("Carregando dados do mercado..."):
        stocks_to_fetch = default_stocks
        
        # Filter stocks if selection was made
        if symbols and len(symbols) > 0:
            stocks_to_fetch = [{"symbol": s} for s in symbols]
        
        # Limit the number of stocks to improve performance
        stocks_to_fetch = stocks_to_fetch[:max_stocks]
        
        # Get details for each stock
        stocks_data = []
        for stock in stocks_to_fetch:
            symbol = stock.get('symbol')
            details = get_stock_details(symbol)
            if details:
                stocks_data.append(details)
        
        return stocks_data

# Button to refresh data
if st.button("🔄 Atualizar Dados do Mercado") or refresh_seconds > 0:
    # Clear cache to force refresh
    load_market_data.clear()

# Load fresh data
stocks_data = load_market_data(selected_stocks, num_stocks)

if stocks_data:
    # Global market summary variables
    total_stocks = len(stocks_data)
    stocks_up = sum(1 for stock in stocks_data if stock.get('variation', 0) > 0)
    stocks_down = sum(1 for stock in stocks_data if stock.get('variation', 0) < 0)
    
    # Display current date and time
    current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(f"**Dados atualizados em:** {current_time}")
    
    # Market summary metrics
    st.header("📊 Resumo do Mercado")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Ações Analisadas", total_stocks)
    
    with col2:
        avg_variation = sum(stock.get('variation', 0) for stock in stocks_data) / total_stocks
        delta_color = "normal" if avg_variation > 0 else "inverse"
        st.metric("Variação Média", f"{avg_variation:.2f}%", delta=f"{avg_variation:.2f}%", delta_color=delta_color)
    
    with col3:
        st.metric("Em Alta/Baixa", f"{stocks_up}/{stocks_down}")
    
    with col4:
        if stocks_up > stocks_down:
            sentiment = "📈 Positivo"
        elif stocks_down > stocks_up:
            sentiment = "📉 Negativo"
        else:
            sentiment = "➡️ Neutro"
        st.metric("Sentimento", sentiment)
    
    with col5:
        # Get the stocks with the highest volume
        highest_vol_stock = max(stocks_data, key=lambda x: x.get('financial_volume', 0))
        st.metric("Mais Negociada", highest_vol_stock.get('symbol', ''))
    
    # Market summary charts
    col1, col2 = st.columns(2)
    
    with col1:
        market_summary_fig = create_market_summary(stocks_data)
        st.plotly_chart(market_summary_fig, use_container_width=True)
    
    with col2:
        volatility_fig, avg_vol = create_volatility_chart(stocks_data)
        st.plotly_chart(volatility_fig, use_container_width=True)
    
    # Sector analysis
    st.header("🏢 Análise Setorial")
    
    # Get sector data
    sector_df = get_sector_data(stocks_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Sector heatmap
        sector_heatmap = create_sector_heatmap(sector_df)
        st.plotly_chart(sector_heatmap, use_container_width=True)
    
    with col2:
        # Sector volume chart
        sector_volume_chart = create_sector_volume_chart(sector_df)
        st.plotly_chart(sector_volume_chart, use_container_width=True)
    
    # Table with sector data
    with st.expander("Ver Detalhes por Setor"):
        formatted_sector_df = sector_df.copy()
        formatted_sector_df['Variação Média (%)'] = formatted_sector_df['Variação Média (%)'].apply(lambda x: f"{x:.2f}%")
        formatted_sector_df['Volume Total'] = formatted_sector_df['Volume Total'].apply(lambda x: f"R$ {x/1e9:.2f}B")
        formatted_sector_df['Volume Médio'] = formatted_sector_df['Volume Médio'].apply(lambda x: f"R$ {x/1e6:.2f}M")
        
        st.dataframe(formatted_sector_df, use_container_width=True)
    
    # Performance analysis
    st.header("📈 Maiores Altas e Baixas")
    
    winners_df, losers_df = get_performance_data(stocks_data)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟢 Top 10 - Maiores Altas")
        st.dataframe(format_dataframe(winners_df), use_container_width=True)
    
    with col2:
        st.subheader("🔴 Top 10 - Maiores Baixas")
        st.dataframe(format_dataframe(losers_df), use_container_width=True)
    
    # Liquidity analysis
    st.header("💧 Ações Mais Líquidas")
    
    # Get liquidity data
    liquid_df = get_liquidity_data(stocks_data)
    st.dataframe(format_dataframe(liquid_df), use_container_width=True)
    
    # Create bar chart of top liquid stocks
    top_5_liquid = liquid_df.head(5)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_5_liquid['Símbolo'],
        y=[float(str(vol).replace('R$ ', '').replace('M', '')) for vol in top_5_liquid['Vol. Fin.']],
        name='Volume Financeiro (R$ Milhões)',
        marker_color='royalblue'
    ))
    
    fig.update_layout(
        title='Top 5 Ações por Volume Financeiro',
        xaxis_title='Ação',
        yaxis_title='Volume Financeiro (R$ Milhões)',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    if show_volatility_section:
        # Volatility analysis
        st.header("📊 Análise de Volatilidade")
        
        # Get volatility data
        vol_df = get_volatility_data(stocks_data)
        st.subheader("Top 10 Ações Mais Voláteis")
        st.dataframe(format_dataframe(vol_df), use_container_width=True)
        
        # Volatility distribution chart
        volatilities = [stock.get('ewma_current', 0) for stock in stocks_data if 'ewma_current' in stock]
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=volatilities,
            nbinsx=20,
            marker_color='royalblue',
            opacity=0.7
        ))
        
        fig.update_layout(
            title='Distribuição de Volatilidade no Mercado',
            xaxis_title='Volatilidade (%)',
            yaxis_title='Número de Ações',
            height=400
        )
        
        # Add a vertical line for average volatility
        fig.add_shape(
            type="line",
            x0=avg_vol,
            y0=0,
            x1=avg_vol,
            y1=10,  # This will be adjusted automatically
            line=dict(color="red", width=2, dash="dash")
        )
        
        # Add annotation for average
        fig.add_annotation(
            x=avg_vol,
            y=10,
            text=f"Média: {avg_vol:.2f}%",
            showarrow=True,
            arrowhead=1
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Volatility vs. Return scatter plot
        fig = go.Figure()
        
        # Create data points
        x_data = [stock.get('ewma_current', 0) for stock in stocks_data if 'ewma_current' in stock]
        y_data = [stock.get('variation', 0) for stock in stocks_data if 'ewma_current' in stock]
        text_data = [stock.get('symbol', '') for stock in stocks_data if 'ewma_current' in stock]
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=x_data,
            y=y_data,
            mode='markers',
            text=text_data,
            marker=dict(
                size=10,
                color=y_data,
                colorscale='RdBu',
                colorbar=dict(title='Variação (%)'),
                line=dict(width=1, color='black')
            )
        ))
        
        # Add quadrant lines
        fig.add_shape(
            type="line",
            x0=min(x_data),
            y0=0,
            x1=max(x_data),
            y1=0,
            line=dict(color="black", width=1, dash="dash")
        )
        
        fig.add_shape(
            type="line",
            x0=avg_vol,
            y0=min(y_data),
            x1=avg_vol,
            y1=max(y_data),
            line=dict(color="black", width=1, dash="dash")
        )
        
        # Add quadrant annotations
        fig.add_annotation(
            x=(max(x_data) + avg_vol) / 2,
            y=max(y_data) / 2,
            text="Alta Vol, Alta Var",
            showarrow=False,
            font=dict(size=10)
        )
        
        fig.add_annotation(
            x=(min(x_data) + avg_vol) / 2,
            y=max(y_data) / 2,
            text="Baixa Vol, Alta Var",
            showarrow=False,
            font=dict(size=10)
        )
        
        fig.add_annotation(
            x=(max(x_data) + avg_vol) / 2,
            y=min(y_data) / 2,
            text="Alta Vol, Baixa Var",
            showarrow=False,
            font=dict(size=10)
        )
        
        fig.add_annotation(
            x=(min(x_data) + avg_vol) / 2,
            y=min(y_data) / 2,
            text="Baixa Vol, Baixa Var",
            showarrow=False,
            font=dict(size=10)
        )
        
        fig.update_layout(
            title='Volatilidade vs. Variação Diária',
            xaxis_title='Volatilidade (%)',
            yaxis_title='Variação (%)',
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    if show_advanced_charts:
        # Advanced analysis
        st.header("🔍 Análise Avançada")
        
        # Beta chart
        st.subheader("Beta em Relação ao Ibovespa")
        beta_chart = create_beta_chart(stocks_data)
        st.plotly_chart(beta_chart, use_container_width=True)
        
        # Correlation matrix
        st.subheader("Correlação e Métricas de Mercado")
        corr_matrix = create_correlation_matrix(stocks_data)
        if corr_matrix:
            st.plotly_chart(corr_matrix, use_container_width=True)
            
            with st.expander("O que significa Beta e Correlação?"):
                st.markdown("""
                **Beta** mede a volatilidade de uma ação em relação ao mercado (Ibovespa):
                - Beta > 1: A ação é mais volátil que o mercado
                - Beta = 1: A ação se move de forma similar ao mercado
                - Beta < 1: A ação é menos volátil que o mercado
                
                **Correlação** mede quão alinhados são os movimentos de uma ação com o mercado:
                - Próximo a 1: Forte correlação positiva (movem juntos)
                - Próximo a 0: Baixa correlação (movimentos independentes)
                - Próximo a -1: Forte correlação negativa (movem em direções opostas)
                """)
    
    # Market insights
    st.header("💡 Insights de Mercado")
    
    # Generate some insights based on the data
    insights = []
    
    # Sector insights
    best_sector = sector_df.iloc[0]['Setor']
    worst_sector = sector_df.iloc[-1]['Setor']
    insights.append(f"O setor de **{best_sector}** está apresentando a melhor performance do dia com variação média de **{sector_df.iloc[0]['Variação Média (%)']:.2f}%**.")
    insights.append(f"O setor de **{worst_sector}** está apresentando a pior performance do dia com variação média de **{sector_df.iloc[-1]['Variação Média (%)']:.2f}%**.")
    
    # Volume insights
    highest_vol_stock = max(stocks_data, key=lambda x: x.get('financial_volume', 0))
    insights.append(f"**{highest_vol_stock.get('symbol')}** ({highest_vol_stock.get('name')}) é a ação mais negociada com volume financeiro de **R$ {highest_vol_stock.get('financial_volume', 0)/1e9:.2f} bilhões**.")
    
    # Volatility insights
    highest_vol_stock = max(stocks_data, key=lambda x: x.get('ewma_current', 0) if 'ewma_current' in x else 0)
    insights.append(f"**{highest_vol_stock.get('symbol')}** apresenta a maior volatilidade atual (**{highest_vol_stock.get('ewma_current', 0):.2f}%**).")
    
    # Market sentiment
    if stocks_up > stocks_down * 2:
        insights.append(f"**Sentimento fortemente positivo** com {stocks_up} ações em alta contra apenas {stocks_down} em baixa.")
    elif stocks_down > stocks_up * 2:
        insights.append(f"**Sentimento fortemente negativo** com {stocks_down} ações em baixa contra apenas {stocks_up} em alta.")
    
    # Display insights
    for i, insight in enumerate(insights):
        st.markdown(f"{i+1}. {insight}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: gray; font-size: 0.8em;">
        <p>B3 Market View v1.0 | Desenvolvido com Streamlit | Dados fornecidos pela API OpLab</p>
        <p>© 2025 | Este dashboard é apenas para fins informativos e não constitui recomendação de investimento.</p>
    </div>
    """, unsafe_allow_html=True)

else:
    # No data available or API key missing
    if not api_key:
        st.error("Por favor, insira uma chave API válida no painel lateral para visualizar os dados.")
    else:
        st.error("Não foi possível carregar os dados do mercado. Verifique sua conexão e chave API.")

# Auto-refresh logic
if refresh_seconds > 0:
    time.sleep(refresh_seconds)
    st.experimental_rerun()