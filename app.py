import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Quantitative Screener + Valuasi", page_icon="⚖️", layout="wide")

st.title("⚖️ Quantitative Stock Screener & Valuation Dashboard")
st.caption("Dashboard otomatis analisis teknikal, fundamental, dan estimasi Nilai Wajar (DCF) pasar ID & US.")

@st.cache_data(ttl=3600)
def load_data():
    if os.path.exists("screener_data.csv"):
        return pd.read_csv("screener_data.csv")
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Data screener belum tersedia. Jalankan `python updater.py` terlebih dahulu atau tunggu GitHub Actions bekerja.")
    st.stop()

st.sidebar.header("Filter Parameter")
region_choice = st.sidebar.multiselect("Pilih Pasar:", options=df["Region"].unique(), default=list(df["Region"].unique()))
trend_choice = st.sidebar.multiselect("Status Tren (MA200):", options=df["Tren (vs MA200)"].unique(), default=list(df["Tren (vs MA200)"].unique()))
val_choice = st.sidebar.multiselect("Status Valuasi (DCF):", options=df["Status Valuasi"].unique(), default=list(df["Status Valuasi"].unique()))

filtered_df = df[
    (df["Region"].isin(region_choice)) & 
    (df["Tren (vs MA200)"].isin(trend_choice)) &
    (df["Status Valuasi"].isin(val_choice))
]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Saham Terpantau", len(filtered_df))
col2.metric("Saham Undervalued", len(filtered_df[filtered_df["Status Valuasi"] == "Undervalued (Diskon)"]))
col3.metric("Rata-rata P/E Ratio", round(pd.to_numeric(filtered_df["P/E"], errors="coerce").mean(), 1) if not filtered_df.empty else 0)
col4.metric("Rata-rata ROE (%)", round(pd.to_numeric(filtered_df["ROE (%)"], errors="coerce").mean(), 1) if not filtered_df.empty else 0)

st.markdown("---")
st.subheader("📊 Tabel Screening Lengkap (Dengan Margin of Safety)")

def color_mos(val):
    if pd.isna(val) or val == "-": return ''
    if float(val) > 15: return 'color: green; font-weight: bold'
    elif float(val) < -15: return 'color: red'
    return ''

st.dataframe(
    filtered_df.style.map(color_mos, subset=['MoS (%)']),
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")
st.subheader("🎯 Visualisasi Peluang Valuasi (Margin of Safety)")

plot_val_df = filtered_df.copy()
plot_val_df["MoS (%)"] = pd.to_numeric(plot_val_df["MoS (%)"], errors="coerce")
plot_val_df["P/E"] = pd.to_numeric(plot_val_df["P/E"], errors="coerce")
plot_val_df = plot_val_df.dropna(subset=["MoS (%)", "P/E"])

if not plot_val_df.empty:
    colors = ['green' if x > 0 else 'red' for x in plot_val_df['MoS (%)']]
    fig = go.Figure(data=[go.Bar(
        x=plot_val_df['Ticker'],
        y=plot_val_df['MoS (%)'],
        text=plot_val_df['MoS (%)'].apply(lambda x: f"{x:.1f}%"),
        textposition='auto',
        marker_color=colors
    )])
    fig.update_layout(
        title="Margin of Safety per Emiten (Lebih tinggi, lebih murah secara teori)",
        xaxis_title="Ticker",
        yaxis_title="Margin of Safety (%)",
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Data Margin of Safety tidak tersedia.")