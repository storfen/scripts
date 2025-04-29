import streamlit as st
import pandas as pd
import requests
import datetime
import time
import numpy as np
from typing import List, Dict, Any, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import io

# Set page config
st.set_page_config(
    page_title="Scanner de Calendar Spread 1:3 Automático",
    page_icon="📊",
    layout="wide"
)

# Constants
API_BASE_URL = "https://api.oplab.com.br/v3"
HEADERS = {"Access-Token": ""}

# Email configuration
EMAIL_RECIPIENT = "storfen@gmail.com"  # Email fixo para receber as notificações
EMAIL_SENDER = ""  # Será preenchido pelo usuário na interface
EMAIL_APP_PASSWORD = ""  # Será preenchido pelo usuário na interface
EMAIL_SMTP_SERVER = "smtp.gmail.com"  # Servidor SMTP do Gmail
EMAIL_SMTP_PORT = 587  # Porta para TLS

# Função para enviar email de notificação
def send_email_notification(opportunities_df, scan_type="Calendar Spread", min_opportunities=1):
    """
    Envia email de notificação com os resultados do scan
    
    Args:
        opportunities_df: DataFrame com os resultados do scan
        scan_type: Tipo do scan (Calendar Spread, etc.)
        min_opportunities: Número mínimo de oportunidades para disparar o email
    
    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário
    """
    # Verifica se temos oportunidades suficientes para enviar email
    if len(opportunities_df) < min_opportunities:
        return False
    
    # Verifica se as configurações de email estão completas
    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD:
        st.warning("Configuração de email incompleta. Preencha o email do remetente e a senha de aplicativo na barra lateral.")
        return False
    
    try:
        # Cria a mensagem de email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = f"Scanner de Calendar Spread: {len(opportunities_df)} Oportunidade(s) Encontrada(s)"
        
        # Corpo do email
        email_body = f"""
        <html>
        <head>
            <style>
                table {{
                    border-collapse: collapse;
                    width: 100%;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .put {{
                    background-color: rgba(255, 235, 205, 0.5);
                }}
                .call {{
                    background-color: rgba(204, 230, 255, 0.5);
                }}
            </style>
        </head>
        <body>
            <h2>Scanner de Calendar Spread - Resultados</h2>
            <p>Foram encontradas {len(opportunities_df)} oportunidade(s) de Calendar Spread.</p>
            <p>Data e hora do escaneamento: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <h3>Melhores Oportunidades:</h3>
        """
        
        # Formatar os dados para a exibição na tabela HTML
        display_df = opportunities_df.copy()
        for col in ["Net Cost %", "Strike Difference %"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
        
        for col in ["Short Premium", "Long Premium", "Net Cost", "Stock Price", "Short Strike", "Long Strike"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "N/A")
        
        for col in ["Theta Advantage", "Delta Exposure", "Vega Exposure", "Ideal Ratio"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
        
        # Exibe as 5 melhores oportunidades em uma tabela HTML
        top_opportunities = display_df.head(5)
        
        # Adiciona classes para colorir linhas de PUT e CALL
        html_with_classes = top_opportunities.to_html(index=False, escape=False, classes='sortable')
        html_with_classes = html_with_classes.replace('<tr>', '<tr class="put">', len(opportunities_df[opportunities_df["Type"] == "PUT"]))
        html_with_classes = html_with_classes.replace('<tr class="put">', '<tr class="call">', len(opportunities_df[opportunities_df["Type"] == "CALL"]))
        
        email_body += html_with_classes
        
        # Contagem por tipo
        put_count = len(opportunities_df[opportunities_df["Type"] == "PUT"])
        call_count = len(opportunities_df[opportunities_df["Type"] == "CALL"])
        
        # Adiciona resumo
        email_body += f"""
        <p><strong>Resumo:</strong> {put_count} PUTs (🟠) | {call_count} CALLs (🔵)</p>
        <p>Para detalhes completos, consulte o arquivo CSV anexo.</p>
        <p>Atenciosamente,<br>Scanner de Calendar Spread</p>
        </body>
        </html>
        """
        
        # Anexa o conteúdo HTML
        msg.attach(MIMEText(email_body, 'html'))
        
        # Converte o DataFrame para CSV e anexa
        csv_buffer = io.StringIO()
        opportunities_df.to_csv(csv_buffer, index=False)
        
        attachment = MIMEApplication(csv_buffer.getvalue().encode('utf-8'))
        attachment['Content-Disposition'] = f'attachment; filename="calendar_spread_opportunities.csv"'
        msg.attach(attachment)
        
        # Envia o email
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {str(e)}")
        return False

# Function to get all stocks with options
def get_stocks_with_options():
    # Lista padrão de ações brasileiras populares com opções
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
    {"symbol": "VIVT3"}   # Telefônica Brasil
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
            st.info(f"Sem dados para a ação {symbol} (204 No Content)")
            return None
        elif response.status_code == 401:
            st.error(f"Falha de autenticação para {symbol}: Código {response.status_code}")
            return None
        else:
            st.warning(f"Falha ao obter dados para {symbol}: Código {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Erro ao buscar dados para {symbol}: {str(e)}")
        return None

# Function to get all options for a specific stock
def get_options_for_stock(symbol: str, timeout: int = 10):
    url = f"{API_BASE_URL}/market/options/{symbol}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return data
            else:
                st.info(f"Sem dados de opções para {symbol} (resposta vazia)")
                return []
        elif response.status_code == 204:
            st.info(f"Sem opções disponíveis para {symbol} (204 No Content)")
            return []
        elif response.status_code == 401:
            st.error(f"Falha de autenticação para {symbol}: Código {response.status_code}")
            return []
        else:
            st.warning(f"Falha ao obter opções para {symbol}: Código {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Erro ao buscar opções para {symbol}: {str(e)}")
        return []

# Function to calculate implied volatility using Black-Scholes model via API
def get_black_scholes_data(symbol: str, irate: float = 11.25, show_errors: bool = False):
    url = f"{API_BASE_URL}/market/options/bs"
    params = {
        "symbol": symbol,
        "irate": irate
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception:
        return None

# Function to find calendar spread opportunities (1:3 ratio)
def find_calendar_spreads(options_data: List[Dict[Any, Any]], stock_price: float, 
                         option_type: str = "PUT",
                         max_short_days: int = 45, min_long_days: int = 60, 
                         max_strike_diff_pct: float = 20.0, otm_range_pct: float = 25.0, 
                         max_ratio_diff: float = 0.8, max_net_cost_pct: float = 5.0, 
                         interest_rate: float = 11.25) -> pd.DataFrame:
    if not options_data:
        return pd.DataFrame()
    
    # Filter options by type (PUT or CALL)
    type_options = [opt for opt in options_data if opt.get('category') == option_type]
    
    if not type_options:
        return pd.DataFrame()
    
    # Get current date
    current_date = datetime.datetime.now().date()
    
    # Organize options by expiry date
    options_by_expiry = {}
    for option in type_options:
        due_date = option.get('due_date', '')
        if not due_date:
            continue
            
        # Calculate days to expiry
        try:
            expiry_date = datetime.datetime.strptime(due_date, '%Y-%m-%d').date()
            days_to_expiry = (expiry_date - current_date).days
            
            if days_to_expiry <= 0:
                continue
                
            if due_date not in options_by_expiry:
                options_by_expiry[due_date] = []
                
            # Add days to expiry to the option object for easy access
            option['days_to_expiry'] = days_to_expiry
            options_by_expiry[due_date].append(option)
        except ValueError:
            continue
    
    # Filter expiry dates into short-term and long-term
    short_term_expiries = []
    long_term_expiries = []
    
    for due_date, options in options_by_expiry.items():
        if options and options[0]['days_to_expiry'] <= max_short_days:
            short_term_expiries.append(due_date)
        elif options and options[0]['days_to_expiry'] >= min_long_days:
            long_term_expiries.append(due_date)
    
    # If we don't have both short and long term options, we can't create calendar spreads
    if not short_term_expiries or not long_term_expiries:
        return pd.DataFrame()
    
    # Find calendar spread opportunities
    opportunities = []
    
    # Determine the OTM/ITM range based on option type
    if option_type == "PUT":
        # For PUTs, OTM means strike below current price
        otm_min = stock_price * (1 - otm_range_pct/100)
        otm_max = stock_price
    else:
        # For CALLs, OTM means strike above current price
        otm_min = stock_price
        otm_max = stock_price * (1 + otm_range_pct/100)
    
    for short_expiry in short_term_expiries:
        short_term_options = options_by_expiry[short_expiry]
        
        # Filter for OTM short options with valid bid prices
        if option_type == "PUT":
            # For PUTs, find options with strike below current price (OTM)
            otm_short_options = [p for p in short_term_options if 
                               p.get('strike', 0) <= otm_max and 
                               p.get('strike', 0) >= otm_min and 
                               p.get('bid', 0) > 0]
        else:
            # For CALLs, find options with strike above current price (OTM)
            otm_short_options = [p for p in short_term_options if 
                               p.get('strike', 0) >= otm_min and 
                               p.get('strike', 0) <= otm_max and 
                               p.get('bid', 0) > 0]
        
        if not otm_short_options:
            continue
            
        for short_option in otm_short_options:
            short_strike = short_option.get('strike', 0)
            short_premium = short_option.get('bid', 0)  # Use bid price (what you can sell for)
            short_days = short_option.get('days_to_expiry', 0)
            
            for long_expiry in long_term_expiries:
                long_term_options = options_by_expiry[long_expiry]
                
                # Filter long options with strikes close to the short option strike
                max_strike_diff = short_strike * (max_strike_diff_pct / 100)
                matching_long_options = [p for p in long_term_options if 
                                     abs(p.get('strike', 0) - short_strike) <= max_strike_diff and
                                     p.get('ask', 0) > 0]
                
                if not matching_long_options:
                    continue
                    
                for long_option in matching_long_options:
                    long_strike = long_option.get('strike', 0)
                    long_premium = long_option.get('ask', 0)  # Use ask price (what you pay to buy)
                    long_days = long_option.get('days_to_expiry', 0)
                    
                    # Calculate how many long options we need to buy to get close to zero cost
                    # We're targeting a 1:3 ratio
                    # For zero cost: short_premium = long_premium * 3
                    
                    ideal_ratio = short_premium / long_premium if long_premium > 0 else 0
                    
                    # Check if we can buy close to 3 long options with the premium from 1 short option
                    if abs(ideal_ratio - 3.0) <= max_ratio_diff:
                        # Calculate exact net cost
                        net_cost = long_premium * 3 - short_premium
                        net_cost_pct = (net_cost / stock_price) * 100
                        
                        # Skip if net cost exceeds maximum allowed
                        if abs(net_cost_pct) > max_net_cost_pct:
                            continue
                        
                        # Calculate the difference between strikes
                        strike_diff = abs(long_strike - short_strike)
                        strike_diff_pct = (strike_diff / short_strike) * 100
                        
                        # Get Black-Scholes data if available
                        bs_short = get_black_scholes_data(short_option.get('symbol', ''), interest_rate)
                        bs_long = get_black_scholes_data(long_option.get('symbol', ''), interest_rate)
                        
                        # Calculate theta advantage if BS data available
                        theta_advantage = None
                        delta_exposure = None
                        vega_exposure = None
                        
                        if bs_short and bs_long:
                            theta_short = bs_short.get('theta', 0)
                            theta_long = bs_long.get('theta', 0)
                            theta_advantage = theta_short - (theta_long * 3)
                            
                            delta_short = bs_short.get('delta', 0)
                            delta_long = bs_long.get('delta', 0)
                            delta_exposure = delta_short - (delta_long * 3)
                            
                            vega_short = bs_short.get('vega', 0)
                            vega_long = bs_long.get('vega', 0)
                            vega_exposure = vega_short - (vega_long * 3)
                        
                        # Create opportunity data
                        opportunity = {
                            'Stock': short_option.get('parent_symbol', ''),
                            'Type': option_type,
                            'Stock Price': stock_price,
                            'Short Option': short_option.get('symbol', ''),
                            'Short Strike': short_strike,
                            'Short Premium': short_premium,
                            'Short Expiry': short_expiry,
                            'Short Days': short_days,
                            'Long Option': long_option.get('symbol', ''),
                            'Long Strike': long_strike,
                            'Long Premium': long_premium,
                            'Long Expiry': long_expiry,
                            'Long Days': long_days,
                            'Days Difference': long_days - short_days,
                            'Strike Difference %': strike_diff_pct,
                            'Ideal Ratio': ideal_ratio,
                            'Net Cost': net_cost,
                            'Net Cost %': net_cost_pct,
                            'Theta Advantage': theta_advantage,
                            'Delta Exposure': delta_exposure,
                            'Vega Exposure': vega_exposure
                        }
                        
                        opportunities.append(opportunity)
    
    # Convert to DataFrame
    if opportunities:
        df = pd.DataFrame(opportunities)
        return df
    else:
        return pd.DataFrame()

# Function to display the scanner results
def display_scan_results(all_opportunities, sort_column="Net Cost %", sort_order="Crescente"):
    if not all_opportunities.empty:
        # Sort based on user selection
        ascending = (sort_order == "Crescente")
        
        # Map front-end names to DataFrame column names if needed
        column_mapping = {
            "Net Cost %": "Net Cost %",
            "Ideal Ratio": "Ideal Ratio",
            "Strike Difference %": "Strike Difference %",
            "Days Difference": "Days Difference",
            "Theta Advantage": "Theta Advantage"
        }
        
        sort_by = column_mapping.get(sort_column, "Net Cost %")
        
        # For columns that may be None, replace None with appropriate value for sorting
        if sort_by == "Theta Advantage" and "Theta Advantage" in all_opportunities.columns:
            all_opportunities["Theta Advantage"] = all_opportunities["Theta Advantage"].fillna(0)
        
        all_opportunities = all_opportunities.sort_values(by=sort_by, ascending=ascending)
        
        # Display the results
        st.subheader(f"Encontradas {len(all_opportunities)} Oportunidades de Calendar Spread")
        
        # Show metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_cost = all_opportunities["Net Cost %"].mean()
            st.metric("Custo Líquido Médio", f"{avg_cost:.2f}%")
        with col2:
            avg_strike_diff = all_opportunities["Strike Difference %"].mean()
            st.metric("Diferença Média de Strike", f"{avg_strike_diff:.2f}%")
        with col3:
            avg_days_diff = all_opportunities["Days Difference"].mean()
            st.metric("Diferença Média de Dias", f"{avg_days_diff:.0f}")
        with col4:
            avg_ratio = all_opportunities["Ideal Ratio"].mean()
            st.metric("Proporção Média", f"{avg_ratio:.2f}")
        
        # Count by type
        put_count = len(all_opportunities[all_opportunities["Type"] == "PUT"])
        call_count = len(all_opportunities[all_opportunities["Type"] == "CALL"])
        
        # Color code options by type for easier distinction
        def highlight_type(val):
            if val == "PUT":
                return 'background-color: rgba(255, 235, 205, 0.5)'  # Light orange
            elif val == "CALL":
                return 'background-color: rgba(204, 230, 255, 0.5)'  # Light blue
            return ''
        
        # Format numeric columns for display
        display_df = all_opportunities.copy()
        for col in ["Net Cost %", "Strike Difference %"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
        
        for col in ["Short Premium", "Long Premium", "Net Cost", "Stock Price", "Short Strike", "Long Strike"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "N/A")
        
        for col in ["Theta Advantage", "Delta Exposure", "Vega Exposure", "Ideal Ratio"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
        
        # Display full results table with highlight
        st.markdown(f"**Resumo:** {put_count} PUTs (🟠) | {call_count} CALLs (🔵)")
        st.dataframe(display_df.style.applymap(highlight_type, subset=['Type']), use_container_width=True)
        
        # Option to download as CSV
        csv = all_opportunities.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Baixar Oportunidades como CSV",
            csv,
            "calendar_spread_opportunities.csv",
            "text/csv",
            key='download-opportunities-csv'
        )
        
        # Display a detailed view of the top opportunity
        if len(all_opportunities) > 0:
            st.subheader("Detalhes da Melhor Oportunidade")
            best_opportunity = all_opportunities.iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                type_emoji = "🟠" if best_opportunity['Type'] == "PUT" else "🔵"
                st.write(f"**Estratégia: {type_emoji} {best_opportunity['Type']} Calendar Spread 1:3**")
                st.write(f"Ação: **{best_opportunity['Stock']}** (R$ {best_opportunity['Stock Price']:.2f})")
                st.write(f"Vender 1x {best_opportunity['Short Option']} (Strike R$ {best_opportunity['Short Strike']:.2f})")
                st.write(f"Comprar 3x {best_opportunity['Long Option']} (Strike R$ {best_opportunity['Long Strike']:.2f})")
                st.write(f"Custo Líquido: **R$ {best_opportunity['Net Cost']:.2f}** ({best_opportunity['Net Cost %']:.2f}% do preço da ação)")
                st.write(f"Proporção Ideal (calculada): {best_opportunity['Ideal Ratio']:.3f}")
            
            with col2:
                st.write("**Métricas:**")
                st.write(f"Opção Curta: {best_opportunity['Short Days']} dias até o vencimento")
                st.write(f"Opção Longa: {best_opportunity['Long Days']} dias até o vencimento")
                st.write(f"Diferença de Dias: {best_opportunity['Days Difference']} dias")
                st.write(f"Diferença de Strike: {best_opportunity['Strike Difference %']:.2f}%")
                
                if pd.notnull(best_opportunity['Theta Advantage']):
                    st.write(f"Vantagem Theta: {best_opportunity['Theta Advantage']:.3f}")
                if pd.notnull(best_opportunity['Delta Exposure']):
                    st.write(f"Exposição Delta: {best_opportunity['Delta Exposure']:.3f}")
                if pd.notnull(best_opportunity['Vega Exposure']):
                    st.write(f"Exposição Vega: {best_opportunity['Vega Exposure']:.3f}")
                    
        # Display charts
        if len(all_opportunities) > 3:
            st.subheader("Análise Gráfica")
            
            # Prepare data for charts
            chart_data = all_opportunities.copy()
            
            # Add a column for color coding by option type
            chart_data['Option Type'] = chart_data['Type']
            
            col1, col2 = st.columns(2)
            
            # Chart 1: Net Cost % vs Ideal Ratio
            with col1:
                st.write("**Custo Líquido vs. Proporção Ideal**")
                # Use Streamlit's native charting
                st.scatter_chart(
                    chart_data,
                    x="Net Cost %",
                    y="Ideal Ratio",
                    color="Option Type",
                    size="Days Difference"
                )
            
            # Chart 2: Strike Difference % vs Days Difference
            with col2:
                st.write("**Diferença de Strike vs. Diferença de Dias**")
                st.scatter_chart(
                    chart_data,
                    x="Strike Difference %",
                    y="Days Difference",
                    color="Option Type",
                    size="Ideal Ratio"
                )
    else:
        st.info(f"Nenhuma oportunidade de Calendar Spread encontrada com os critérios selecionados.")
        st.write("Sugestões para aumentar as chances de encontrar oportunidades:")
        st.write("1. Aumente o valor de 'Diferença Máx. da Proporção 1:3'")
        st.write("2. Aumente o valor de 'Diferença Máx. de Strike (%)'")
        st.write("3. Aumente o valor de 'Custo Líquido Máx. (%)'")
        st.write("4. Aumente o valor de 'Faixa OTM (%)'")
        st.write("5. Expanda o intervalo de dias para as opções curtas e longas")

# Function to run the complete scan for both PUT and CALL options
def run_complete_scan(
    stocks, 
    max_short_days=45, 
    min_long_days=60,
    max_strike_diff_pct=20.0, 
    otm_range_pct=25.0,
    max_ratio_diff=0.8, 
    max_net_cost_pct=5.0,
    interest_rate=11.25,
    sort_column="Net Cost %", 
    sort_order="Crescente",
    email_notification_enabled=False,
    min_opportunities=3
):
    if not stocks:
        st.error("Por favor, selecione pelo menos uma ação para analisar.")
        return
    
    # Placeholder for scan status
    status_container = st.empty()
    progress_bar = st.progress(0)
    
    # Placeholder for results
    results_container = st.container()
    
    # Start timestamp
    start_time = time.time()
    
    # Initialize result dataframes
    all_opportunities = pd.DataFrame()
    
    for i, stock in enumerate(stocks):
        symbol = stock.get('symbol')
        status_container.text(f"Analisando {symbol}... ({i+1}/{len(stocks)})")
        
        # Get stock details first to get current price
        stock_details = get_stock_details(symbol)
        
        if stock_details:
            # Get current stock price
            stock_price = stock_details.get('close', 0)
            
            # Skip if stock price is 0 or not available
            if stock_price <= 0:
                continue
            
            # Get options for this stock
            options = get_options_for_stock(symbol)
            
            if options:
                # Find PUT calendar spread opportunities
                put_opportunities = find_calendar_spreads(
                    options,
                    stock_price,
                    option_type="PUT",
                    max_short_days=max_short_days,
                    min_long_days=min_long_days,
                    max_strike_diff_pct=max_strike_diff_pct,
                    otm_range_pct=otm_range_pct,
                    max_ratio_diff=max_ratio_diff,
                    max_net_cost_pct=max_net_cost_pct,
                    interest_rate=interest_rate
                )
                
                # Find CALL calendar spread opportunities
                call_opportunities = find_calendar_spreads(
                    options,
                    stock_price,
                    option_type="CALL",
                    max_short_days=max_short_days,
                    min_long_days=min_long_days,
                    max_strike_diff_pct=max_strike_diff_pct,
                    otm_range_pct=otm_range_pct,
                    max_ratio_diff=max_ratio_diff,
                    max_net_cost_pct=max_net_cost_pct,
                    interest_rate=interest_rate
                )
                
                # Combine results
                if not put_opportunities.empty:
                    all_opportunities = pd.concat([all_opportunities, put_opportunities], ignore_index=True)
                    
                if not call_opportunities.empty:
                    all_opportunities = pd.concat([all_opportunities, call_opportunities], ignore_index=True)
        
        # Update progress
        progress_bar.progress((i + 1) / len(stocks))
    
    # Clear status
    status_container.empty()
    progress_bar.empty()
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Display results
    with results_container:
        st.write(f"Escaneamento completo em {elapsed_time:.2f} segundos")
        display_scan_results(all_opportunities, sort_column, sort_order)
    
    # Send email notification if appropriate and enabled
    if email_notification_enabled and not all_opportunities.empty and len(all_opportunities) >= min_opportunities:
        email_sent = send_email_notification(
            all_opportunities, 
            scan_type="Calendar Spread", 
            min_opportunities=min_opportunities
        )
        if email_sent:
            st.success(f"📧 Email enviado para {EMAIL_RECIPIENT} com {len(all_opportunities)} oportunidades!")
    
    return all_opportunities

# Streamlit interface
st.title("🔍 Scanner de Calendar Spread 1:3 Automático")
st.write("""
Este aplicativo escaneia automaticamente oportunidades de Calendar Spread com proporção 1:3 tanto para PUTs quanto para CALLs.

A estratégia consiste em:
1. Vender 1 opção (PUT ou CALL) de curto prazo levemente fora do dinheiro (OTM)
2. Comprar 3 opções do mesmo tipo de longo prazo com strike similar
3. Buscar um custo líquido próximo a zero

Esta versão automática busca oportunidades tanto em PUTs quanto em CALLs simultaneamente.
""")

# API Key
st.sidebar.header("Autenticação API")
api_key = st.sidebar.text_input("Digite sua chave API OpLab", type="password", 
                               help="A chave API é necessária. Se você não tiver uma, obtenha-a do OpLab.")
if api_key:
    HEADERS["Access-Token"] = api_key
else:
    st.sidebar.warning("⚠️ Por favor, digite sua chave API OpLab para usar este aplicativo")

# Email configuration - Add this after API key
st.sidebar.header("Configuração de Email")
email_notification_enabled = st.sidebar.checkbox("Habilitar Notificações por Email", value=True, 
                                          help="Envia email quando encontrar oportunidades")

email_config_container = st.sidebar.container()
min_opportunities = 3  # Default value

if email_notification_enabled:
    with email_config_container:
        EMAIL_SENDER = st.text_input("Seu Email (Gmail)", placeholder="seu.email@gmail.com")
        EMAIL_APP_PASSWORD = st.text_input("Senha de Aplicativo do Gmail", type="password", 
                                help="Não é sua senha normal do Gmail. Crie uma senha de aplicativo específica em myaccount.google.com/apppasswords")
        min_opportunities = st.number_input("Mínimo de Oportunidades para Enviar Email", min_value=1, max_value=20, value=3, 
                                help="Email será enviado apenas quando o número de oportunidades encontradas for maior ou igual a este valor")
        
        # Botão para testar a configuração de email
        if st.button("Testar Configuração de Email"):
            if not EMAIL_SENDER or not EMAIL_APP_PASSWORD:
                st.error("Por favor, preencha seu email e senha de aplicativo do Gmail")
            else:
                try:
                    # Cria uma mensagem de teste
                    msg = MIMEMultipart()
                    msg['From'] = EMAIL_SENDER
                    msg['To'] = EMAIL_RECIPIENT
                    msg['Subject'] = "Teste de Configuração - Scanner de Calendar Spread"
                    
                    msg.attach(MIMEText("Este é um email de teste do Scanner de Calendar Spread. Se você recebeu este email, sua configuração está correta!", 'plain'))
                    
                    # Envia a mensagem
                    with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
                        server.starttls()
                        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
                        server.send_message(msg)
                    
                    st.success("Email de teste enviado com sucesso! Verifique sua caixa de entrada.")
                except Exception as e:
                    st.error(f"Erro ao enviar email de teste: {str(e)}")
else:
    email_config_container.info("Notificações por email desativadas")

# Sidebar controls
st.sidebar.header("Configurações do Scanner")

# Interest rate for Black-Scholes calculation
interest_rate = st.sidebar.slider("Taxa de Juros (%)", 0.0, 20.0, 11.25, 0.25, 
                                 help="Taxa de juros atual (SELIC) para cálculos de opções")

# Days to expiry parameters
max_short_days = st.sidebar.slider("Dias Máx. para Opção Curta", 1, 90, 45, 
                                 help="Número máximo de dias até o vencimento da opção curta (vendida)")

min_long_days = st.sidebar.slider("Dias Mín. para Opção Longa", 46, 240, 60, 
                                help="Número mínimo de dias até o vencimento da opção longa (comprada)")

# Strike and OTM parameters
max_strike_diff_pct = st.sidebar.slider("Diferença Máx. de Strike (%)", 0.5, 30.0, 20.0, 0.5,
                                     help="Diferença percentual máxima entre os strikes das opções curta e longa")

otm_range_pct = st.sidebar.slider("Faixa OTM (%)", 1.0, 30.0, 25.0, 1.0,
                               help="Quão OTM a opção curta pode estar (% em relação ao preço atual)")

# Ratio and cost parameters
max_ratio_diff = st.sidebar.slider("Diferença Máx. da Proporção 1:3", 0.1, 2.0, 0.8, 0.1,
                                help="Máximo desvio permitido da proporção ideal de 1:3")

max_net_cost_pct = st.sidebar.slider("Custo Líquido Máx. (%)", 0.0, 10.0, 5.0, 0.25,
                                  help="Custo líquido máximo da operação como percentual do preço da ação")

# Stock selection
st.sidebar.header("Seleção de Ações")
all_stocks = get_stocks_with_options()
all_stock_symbols = [stock["symbol"] for stock in all_stocks]

stock_selection_mode = st.sidebar.radio("Modo de Seleção", ["Todas", "Personalizada"])

if stock_selection_mode == "Personalizada":
    selected_stocks = st.sidebar.multiselect("Selecionar Ações", options=all_stock_symbols, 
                                           default=["PETR4", "VALE3", "ITUB4"])
else:
    selected_stocks = all_stock_symbols

# Sort options
sort_options = st.sidebar.selectbox(
    "Ordenar resultados por",
    ["Net Cost %", "Ideal Ratio", "Strike Difference %", "Days Difference", "Theta Advantage"],
    help="Escolha como os resultados serão ordenados"
)
sort_order = st.sidebar.radio("Ordem", ["Crescente", "Decrescente"], index=0,
                            help="Ordem crescente ou decrescente")

# Auto-scan settings
st.sidebar.header("Escaneamento Automático")
auto_scan_enabled = st.sidebar.checkbox("Ativar Escaneamento Automático", 
                                      help="Quando ativado, o scanner irá executar automaticamente em intervalos regulares")
auto_scan_interval = st.sidebar.number_input("Intervalo (minutos)", min_value=1, max_value=60, value=5,
                                          help="Intervalo de tempo entre escaneamentos automáticos")

# Add a test connection button
if st.sidebar.button("Testar Conexão API"):
    if not api_key:
        st.sidebar.error("Por favor, insira sua chave API primeiro")
    else:
        with st.sidebar:
            with st.spinner("Testando conexão..."):
                # Try to fetch options for PETR4 as a test
                test_symbol = "PETR4"
                stock_details = get_stock_details(test_symbol)
                if stock_details:
                    st.success(f"Conexão bem-sucedida! Obtidos dados da ação {test_symbol}")
                    # Show stock price
                    st.write(f"Preço atual: R$ {stock_details.get('close', 0):.2f}")
                    
                    # Try to get options
                    test_options = get_options_for_stock(test_symbol)
                    if test_options:
                        # Count PUT and CALL options
                        puts = [opt for opt in test_options if opt.get('category') == 'PUT']
                        calls = [opt for opt in test_options if opt.get('category') == 'CALL']
                        st.success(f"Obtidas {len(puts)} opções de PUT e {len(calls)} opções de CALL para {test_symbol}")
                    else:
                        st.warning(f"Não foi possível obter opções para {test_symbol}, mas a conexão com a API está funcionando.")
                else:
                    st.error("Teste de conexão falhou. Verifique sua chave API e tente novamente.")

# Main scanner
tabs = st.tabs(["Scanner", "Como Funciona", "Ajuda"])

with tabs[0]:
    st.header(f"Scanner de Calendar Spread 1:3 (PUTs e CALLs)")
try:
    from streamlit_autorefresh import st_autorefresh

    # Adicionar refresh automático se escaneamento automático estiver ativado
    if auto_scan_enabled:
        count = st_autorefresh(interval=auto_scan_interval * 60 * 1000, limit=None, key="auto_refresh")
        
        # Create columns for buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        # Manual scan button
        scan_button = col1.button("Escanear Agora", use_container_width=True)
        
        # Status indicator for auto scan
        if auto_scan_enabled:
            col2.success("Escaneamento Automático Ativado", icon="🔄")
        else:
            col2.info("Escaneamento Automático Desativado", icon="⏸️")
        
        # Last scan time
        last_scan_time = col3.empty()
        
        # Initialize session state for tracking last scan time and results
        if 'last_scan_time' not in st.session_state:
            st.session_state.last_scan_time = None
        
        if 'last_scan_results' not in st.session_state:
            st.session_state.last_scan_results = pd.DataFrame()
        
        if 'scan_count' not in st.session_state:
            st.session_state.scan_count = 0
        
        # Function to update the last scan time display
        def update_last_scan_display():
            if st.session_state.last_scan_time:
                last_scan_time.write(f"Último escaneamento: {st.session_state.last_scan_time.strftime('%H:%M:%S')} - Contagem: {st.session_state.scan_count}")
            else:
                last_scan_time.write("Nenhum escaneamento realizado ainda")
        
        # Update the last scan time display initially
        update_last_scan_display()
        
        # Create container for scan results
        scan_results_container = st.container()
        
        # Execute scan function (either manual or automatic)
        def execute_scan():
            if not api_key:
                st.error("Por favor, insira sua chave API OpLab na barra lateral.")
                return
            
            if not selected_stocks:
                st.error("Por favor, selecione pelo menos uma ação para analisar.")
                return
                
            stocks = [{"symbol": s} for s in selected_stocks]
            
            # Update session state
            st.session_state.last_scan_time = datetime.datetime.now()
            st.session_state.scan_count += 1
            
            # Update the display
            update_last_scan_display()
            
            # Run the scan with email notification
            results = run_complete_scan(
                stocks,
                max_short_days=max_short_days,
                min_long_days=min_long_days,
                max_strike_diff_pct=max_strike_diff_pct,
                otm_range_pct=otm_range_pct,
                max_ratio_diff=max_ratio_diff,
                max_net_cost_pct=max_net_cost_pct,
                interest_rate=interest_rate,
                sort_column=sort_options,
                sort_order=sort_order,
                email_notification_enabled=email_notification_enabled,
                min_opportunities=min_opportunities
            )
            
            # Store results in session state
            st.session_state.last_scan_results = results
            
            return results
        
        # Manual scan button functionality
        if scan_button:
            with scan_results_container:
                execute_scan()
        
        # Auto scan functionality
        if auto_scan_enabled:
            # Get current time
            current_time = time.time()
            
            # Calculate time since last scan
            if st.session_state.last_scan_time:
                time_since_last_scan = (datetime.datetime.now() - st.session_state.last_scan_time).total_seconds()
                # Convert auto_scan_interval from minutes to seconds
                if time_since_last_scan >= (auto_scan_interval * 60):
                    with scan_results_container:
                        execute_scan()
            else:
                # First scan when auto-scan is enabled
                with scan_results_container:
                    execute_scan()
        
        # Display previous scan results if available
        if not st.session_state.last_scan_results.empty and not scan_button and not (auto_scan_enabled and 'just_scanned' in st.session_state and st.session_state.just_scanned):
            with scan_results_container:
                st.write("Mostrando resultados do último escaneamento:")
                display_scan_results(st.session_state.last_scan_results, sort_options, sort_order)
    else:
        # If auto-refresh is not enabled, just show a scan button
        if st.button("Escanear Oportunidades"):
            if not api_key:
                st.error("Por favor, insira sua chave API OpLab na barra lateral.")
            else:
                if not selected_stocks:
                    st.error("Por favor, selecione pelo menos uma ação para analisar.")
                else:
                    stocks = [{"symbol": s} for s in selected_stocks]
                    
                    # Run the scan with email notification
                    run_complete_scan(
                        stocks,
                        max_short_days=max_short_days,
                        min_long_days=min_long_days,
                        max_strike_diff_pct=max_strike_diff_pct,
                        otm_range_pct=otm_range_pct,
                        max_ratio_diff=max_ratio_diff,
                        max_net_cost_pct=max_net_cost_pct,
                        interest_rate=interest_rate,
                        sort_column=sort_options,
                        sort_order=sort_order,
                        email_notification_enabled=email_notification_enabled,
                        min_opportunities=min_opportunities
                    )
except ImportError:
    st.warning("Para utilizar o escaneamento automático, instale o pacote 'streamlit_autorefresh': pip install streamlit-autorefresh")
    
    # Simple version without auto-refresh
    if st.button("Escanear Oportunidades"):
        if not api_key:
            st.error("Por favor, insira sua chave API OpLab na barra lateral.")
        else:
            if not selected_stocks:
                st.error("Por favor, selecione pelo menos uma ação para analisar.")
            else:
                stocks = [{"symbol": s} for s in selected_stocks]
                
                # Run the scan with email notification
                run_complete_scan(
                    stocks,
                    max_short_days=max_short_days,
                    min_long_days=min_long_days,
                    max_strike_diff_pct=max_strike_diff_pct,
                    otm_range_pct=otm_range_pct,
                    max_ratio_diff=max_ratio_diff,
                    max_net_cost_pct=max_net_cost_pct,
                    interest_rate=interest_rate,
                    sort_column=sort_options,
                    sort_order=sort_order,
                    email_notification_enabled=email_notification_enabled,
                    min_opportunities=min_opportunities
                )

with tabs[1]:
    st.header("Como Funciona o Calendar Spread 1:3")
    
    st.subheader("Princípio Básico")
    st.write("""
    Um Calendar Spread 1:3 é uma estratégia de opções que explora as diferenças no decaimento do tempo (theta) 
    entre opções de curto e longo prazo.
    
    O **time decay (theta)** é não-linear e acelera conforme a opção se aproxima do vencimento. 
    Opções de curto prazo têm um theta mais negativo do que opções de longo prazo, o que significa que 
    perdem valor mais rapidamente com o passar do tempo.
    """)
    
    st.subheader("Mecânica da Estratégia")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Para Calendar Spread de PUT:**")
        st.markdown("""
        1. **Venda 1 PUT de curto prazo** levemente OTM (strike abaixo do preço atual)
           - Recebe o prêmio imediatamente
           - Esta opção perde valor rapidamente com o tempo
        
        2. **Compra 3 PUTs de prazo mais longo** com strike similar
           - Usa o prêmio recebido da PUT curta
           - Estas opções perdem valor mais lentamente
        
        3. **Resultado esperado:**
           - A PUT curta expira sem valor (máximo lucro nesta perna)
           - As 3 PUTs longas mantêm valor e potencial
           - Proteção se o ativo cair abaixo do strike
        """)
    
    with col2:
        st.markdown("**Para Calendar Spread de CALL:**")
        st.markdown("""
        1. **Venda 1 CALL de curto prazo** levemente OTM (strike acima do preço atual)
           - Recebe o prêmio imediatamente
           - Esta opção perde valor rapidamente com o tempo
        
        2. **Compra 3 CALLs de prazo mais longo** com strike similar
           - Usa o prêmio recebido da CALL curta
           - Estas opções perdem valor mais lentamente
        
        3. **Resultado esperado:**
           - A CALL curta expira sem valor (máximo lucro nesta perna)
           - As 3 CALLs longas mantêm valor e potencial
           - Proteção se o ativo subir acima do strike
        """)
    
    st.subheader("Cenários Possíveis")
    
    st.markdown("""
    **Cenário ideal:** O ativo permanece próximo ao strike até o vencimento da opção curta. 
    A opção vendida expira sem valor (máximo lucro nesta perna) e você mantém as 3 opções longas 
    que ainda têm valor e potencial.
    
    **Se o ativo se mover na direção do strike:**
    - Para PUTs: Se o ativo cair, a PUT vendida pode ser exercida, mas as 3 PUTs longas ganham valor e oferecem proteção
    - Para CALLs: Se o ativo subir, a CALL vendida pode ser exercida, mas as 3 CALLs longas ganham valor e oferecem proteção
    
    **Se o ativo se mover na direção oposta ao strike:**
    - Para PUTs: Se o ativo subir, ambas as PUTs perdem valor, mas a PUT curta perde mais rapidamente
    - Para CALLs: Se o ativo cair, ambas as CALLs perdem valor, mas a CALL curta perde mais rapidamente
    """)
    
    st.subheader("Vantagens e Desvantagens")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Vantagens:**")
        st.markdown("""
        - Aproveita o decaimento de tempo acelerado em opções curtas
        - Potencial para lucro em múltiplos cenários
        - Custo inicial próximo a zero (baixo risco de capital)
        - Proteção contra movimentos adversos
        """)
    
    with col2:
        st.markdown("**Desvantagens:**")
        st.markdown("""
        - Requer acompanhamento constante
        - Estratégia complexa para iniciantes
        - Risco de liquidez nas opções de prazo longo
        - Impacto da volatilidade implícita nas diferentes opções
        """)

with tabs[2]:
    st.header("Ajuda e Dicas")
    
    st.subheader("Como usar este Scanner")
    
    st.markdown("""
    1. **Insira sua chave API da OpLab** na barra lateral
    2. **Configure suas notificações por email** (opcional):
       - Ative "Habilitar Notificações por Email"
       - Insira seu email Gmail e senha de aplicativo
       - Defina o número mínimo de oportunidades para receber notificações
    3. **Ajuste os parâmetros** de acordo com sua preferência:
       - Dias de vencimento para opções curtas e longas
       - Diferença máxima entre strikes
       - Faixa OTM para as opções curtas
       - Tolerância da proporção 1:3
       - Custo líquido máximo aceitável
    4. **Selecione as ações** que deseja analisar
    5. **Escolha o modo de escaneamento**:
       - Manual: Clique em "Escanear Agora" para executar uma única vez
       - Automático: Ative o "Escaneamento Automático" e defina o intervalo de tempo
    """)
    
    st.subheader("Notificações por Email")
    
    st.markdown(f"""
    Este scanner pode enviar notificações por email quando encontrar oportunidades de Calendar Spread:
    
    **Como configurar:**
    - Habilite "Notificações por Email" na barra lateral
    - Insira seu email Gmail e senha de aplicativo
    - Defina o número mínimo de oportunidades para receber notificações
    
    **Detalhes importantes:**
    - As notificações são enviadas para o email configurado ({EMAIL_RECIPIENT})
    - Você precisa usar uma **senha de aplicativo** do Gmail, não sua senha normal
    - Para criar uma senha de aplicativo, ative a verificação em duas etapas na sua conta Google
    - Visite [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) para criar uma senha de aplicativo
    
    **Conteúdo do Email:**
    - Resumo das melhores oportunidades encontradas
    - Um arquivo CSV com todas as oportunidades em detalhes
    - Informações de mercado e estatísticas das oportunidades
    """)
    
    st.subheader("Escaneamento Automático")
    
    st.markdown("""
    O escaneamento automático permite que o sistema busque oportunidades continuamente, sem necessidade de ação manual.
    
    **Como funciona:**
    - Ative a opção "Escaneamento Automático" na barra lateral
    - Defina o intervalo em minutos (por exemplo, a cada 5 minutos)
    - O scanner executará automaticamente no intervalo definido
    - Os resultados serão atualizados na tela automaticamente
    - Emails serão enviados quando novas oportunidades forem encontradas (se habilitado)
    
    **Dicas:**
    - Use intervalos mais longos (10-15 minutos) para evitar sobrecarga da API
    - Selecione um subconjunto de ações para escaneamento mais rápido
    - Mantenha a janela do navegador aberta para continuar o escaneamento
    """)
    
    st.subheader("Dicas para Maximizar o Sucesso")
    
    st.markdown("""
    **Escolha do Strike:**
    - Para PUTs: Selecione strikes levemente abaixo do preço atual (5-15%)
    - Para CALLs: Selecione strikes levemente acima do preço atual (5-15%)
    
    **Timing Ideal:**
    - Momentos de volatilidade elevada para aumentar os prêmios
    - Expectativa de mercado lateral ou estável no curto prazo
    - Quando há um diferencial significativo de volatilidade entre prazos diferentes
    
    **Gestão de Risco:**
    - Defina stop loss - quanto você está disposto a perder se o mercado se mover fortemente
    - Considere fechar a posição da opção curta se o lucro atingir 50-70% antes do vencimento
    - Monitore a volatilidade do mercado - aumentos repentinos podem afetar o perfil de risco
    
    **Liquidez:**
    - Verifique sempre o volume de negociação das opções
    - Prefira opções com spread bid/ask estreito para facilitar entradas e saídas
    - As opções mais líquidas geralmente estão nos vencimentos mais próximos
    """)
    
    st.subheader("Entendendo as Métricas")
    
    st.markdown("""
    **Ideal Ratio:** Indica quão próximo você está da proporção exata de 1:3. O valor ideal é 3.0 (significa que o prêmio da opção curta é exatamente igual ao prêmio de 3 opções longas).
    
    **Net Cost %:** O custo líquido da operação como percentual do preço da ação. Valores próximos de zero são ideais.
    
    **Theta Advantage:** A diferença entre o theta da opção curta e o theta combinado das 3 opções longas. Valores positivos indicam que você está ganhando com o passar do tempo.
    
    **Strike Difference %:** A diferença percentual entre os strikes das opções curta e longa. Valores menores significam strikes mais próximos.
    
    **Days Difference:** A diferença em dias entre os vencimentos das opções curta e longa. Valores maiores significam maior diferença de tempo para explorar o decaimento temporal.
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Calendar Spread Scanner 1:3 Automático com Notificações por Email © 2025")