import os
from typing import List

import pandas as pd
import streamlit as st

from short_strangle_strategy import DEFAULT_SYMBOLS, ScannerConfig, scan_short_strangles


st.set_page_config(
    page_title="Short Strangle Top Opportunities",
    page_icon="📈",
    layout="wide",
)


DISPLAY_COLUMNS = [
    "Placement",
    "Rank (1-10)",
    "Score (0-100)",
    "Stock",
    "Expiry",
    "Days to Expiry",
    "Call Option",
    "Call Strike",
    "Call Bid",
    "Call Ask",
    "Call Delta",
    "Put Option",
    "Put Strike",
    "Put Bid",
    "Put Ask",
    "Put Delta",
    "Total Premium",
    "Premium (%)",
    "Probability of Profit (%)",
    "Avg Distance (sigma)",
    "Weekly Return (%)",
    "IV Rank",
    "Put Breakeven",
    "Call Breakeven",
]


def format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    formatted = df.copy()
    money_columns = [
        "Call Strike",
        "Put Strike",
        "Call Bid",
        "Call Ask",
        "Put Bid",
        "Put Ask",
        "Total Premium",
        "Put Breakeven",
        "Call Breakeven",
    ]
    pct_columns = [
        "Premium (%)",
        "Probability of Profit (%)",
        "Weekly Return (%)",
        "IV Rank",
    ]
    decimal_columns = ["Score (0-100)", "Call Delta", "Put Delta", "Avg Distance (sigma)"]

    for column in money_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"R$ {float(value):.2f}")

    for column in pct_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{float(value):.2f}%")

    for column in decimal_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{float(value):.2f}")

    return formatted


def build_config(api_key: str, symbols: List[str], max_results: int) -> ScannerConfig:
    return ScannerConfig(
        symbols=symbols,
        api_key=api_key,
        max_results=max_results,
    )


def show_top_cards(df: pd.DataFrame) -> None:
    top = df.head(3)
    if top.empty:
        return

    st.subheader("Top picks")
    columns = st.columns(len(top))
    for column, (_, row) in zip(columns, top.iterrows()):
        with column:
            st.metric(
                label=f"{row['Stock']} | Rank {int(row['Rank (1-10)'])}",
                value=f"Score {row['Score (0-100)']:.2f}",
                delta=f"POP {row['Probability of Profit (%)']:.2f}%",
            )
            st.caption(
                f"Expiry {row['Expiry']} | Premium {row['Premium (%)']:.2f}% | "
                f"Call {row['Call Strike']:.2f} / Put {row['Put Strike']:.2f}"
            )


def main() -> None:
    st.title("Scanner de Short Strangle")
    st.caption("Versao web com filtros profissionais pre-selecionados e ranking automatico de 1 a 10.")

    default_api_key = os.getenv("OPLAB_API_KEY", "")

    with st.sidebar:
        st.header("Configuracao")
        api_key = st.text_input("Chave API OpLab", value=default_api_key, type="password")
        symbols = st.multiselect("Ativos", DEFAULT_SYMBOLS, default=DEFAULT_SYMBOLS)
        max_results = st.slider("Maximo de resultados", min_value=5, max_value=30, value=10, step=1)
        run_scan = st.button("Buscar oportunidades", use_container_width=True)

        st.divider()
        st.markdown("**Filtros padrao**")
        st.write("IV Rank >= 50")
        st.write("POP >= 70%")
        st.write("Delta por perna: 0.10 a 0.20")
        st.write("DTE: 21 a 45")
        st.write("Distancia media >= 1.2 sigma")
        st.write("Liquidez minima por bid/ask/volume")

    if not run_scan:
        st.info("Informe a chave da OpLab na lateral e clique em `Buscar oportunidades`.")
        return

    if not api_key:
        st.error("Informe a chave da API OpLab para executar o scanner.")
        return

    with st.spinner("Buscando as melhores oportunidades de Short Strangle..."):
        config = build_config(api_key=api_key, symbols=symbols, max_results=max_results)
        df = scan_short_strangles(config)

    if df.empty:
        st.warning("Nenhuma oportunidade encontrada com os filtros atuais.")
        return

    show_top_cards(df)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Oportunidades", len(df))
    with col2:
        st.metric("Melhor rank", int(df["Rank (1-10)"].max()))
    with col3:
        st.metric("POP medio", f"{df['Probability of Profit (%)'].mean():.2f}%")
    with col4:
        st.metric("IV Rank medio", f"{df['IV Rank'].mean():.2f}")

    st.subheader("Tabela")
    display_df = df[[column for column in DISPLAY_COLUMNS if column in df.columns]].copy()
    st.dataframe(format_dataframe(display_df), use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar CSV",
        data=csv_bytes,
        file_name="short_strangle_top.csv",
        mime="text/csv",
        use_container_width=True,
    )

    with st.expander("Checklist profissional usado no ranking"):
        st.write("Ativo liquido.")
        st.write("IV Rank alto para venda de volatilidade.")
        st.write("POP minima de 70%.")
        st.write("Deltas conservadores nas duas pernas.")
        st.write("Distancia minima de 1.2 sigma.")
        st.write("Apenas as melhores montagens por ativo.")


if __name__ == "__main__":
    main()
