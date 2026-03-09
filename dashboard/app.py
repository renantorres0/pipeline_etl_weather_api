import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from pathlib import Path
import time

load_dotenv(Path(__file__).parent.parent / "config" / ".env")

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weather Dashboard — São Paulo",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilo ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2d3250;
        text-align: center;
    }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #7eb8f7; }
    .metric-label { font-size: 0.85rem; color: #8892a4; margin-top: 4px; }
    .last-update { font-size: 0.75rem; color: #5a6478; }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-green { background: #1a3d2b; color: #4ade80; }
    .badge-blue  { background: #1a2d4d; color: #60a5fa; }
</style>
""", unsafe_allow_html=True)

# ── DB ────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    user     = os.getenv("user")
    password = os.getenv("password")
    database = os.getenv("database")
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "5433")
    return create_engine(
        f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{database}"
    )

@st.cache_data(ttl=60)          # cache curto — será invalidado pelo query param
def load_data(hours: int, _ts: int) -> pd.DataFrame:
    """Carrega dados das últimas `hours` horas. `_ts` força re-fetch após trigger."""
    engine = get_engine()
    since  = datetime.now() - timedelta(hours=hours)
    query  = text("""
        SELECT datetime, temperature, feels_like, temp_min, temp_max,
               humidity, pressure, wind_speed, wind_deg, clouds,
               visibility, weather_main, weather_description,
               sunrise, sunset, latitude, longitude, city_name
        FROM   sp_weather
        WHERE  datetime >= :since
        ORDER  BY datetime ASC
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"since": since})
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://openweathermap.org/img/wn/10d@2x.png", width=60)
    st.title("⚙️ Configurações")

    hours = st.slider("Janela de tempo (horas)", 6, 168, 24, step=6)
    st.divider()

    st.markdown("### 🔄 Última atualização")
    last_trigger = st.query_params.get("ts", "—")
    if last_trigger != "—":
        try:
            ts_dt = datetime.fromtimestamp(int(last_trigger))
            st.success(f"Airflow trigger em\n**{ts_dt.strftime('%d/%m/%Y %H:%M:%S')}**")
        except Exception:
            st.info(last_trigger)
    else:
        st.info("Aguardando próximo trigger do Airflow…")

    st.divider()
    if st.button("🔁 Recarregar agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("""
    <div class='last-update'>
    Dashboard conectado ao PostgreSQL.<br>
    Atualizado automaticamente após cada DAG run via webhook.
    </div>
    """, unsafe_allow_html=True)

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown("## 🌦️ Weather Pipeline — São Paulo")
col_title, col_badge = st.columns([8, 2])
with col_badge:
    st.markdown(
        "<div class='badge badge-green'>● Pipeline ativo</div>",
        unsafe_allow_html=True,
    )

# ── Carregar dados ────────────────────────────────────────────────────────────
ts_param = int(st.query_params.get("ts", 0))

try:
    df = load_data(hours, ts_param)
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    st.stop()

if df.empty:
    st.warning("Nenhum dado encontrado para o período selecionado.")
    st.stop()

latest = df.iloc[-1]

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown("### 📊 Leitura atual")
k1, k2, k3, k4, k5, k6 = st.columns(6)

def kpi(col, icon, value, label):
    col.markdown(f"""
    <div class='metric-card'>
        <div style='font-size:1.5rem'>{icon}</div>
        <div class='metric-value'>{value}</div>
        <div class='metric-label'>{label}</div>
    </div>""", unsafe_allow_html=True)

kpi(k1, "🌡️", f"{latest['temperature']:.1f}°C",  "Temperatura")
kpi(k2, "🤔", f"{latest['feels_like']:.1f}°C",   "Sensação térmica")
kpi(k3, "💧", f"{latest['humidity']}%",           "Umidade")
kpi(k4, "💨", f"{latest['wind_speed']:.1f} m/s",  "Vento")
kpi(k5, "☁️", f"{latest['clouds']}%",             "Nuvens")
kpi(k6, "👁️", f"{latest['visibility']//1000} km", "Visibilidade")

st.markdown("<br>", unsafe_allow_html=True)

# ── Gráficos principais ───────────────────────────────────────────────────────
st.markdown("### 📈 Histórico")

tab1, tab2, tab3 = st.tabs(["🌡️ Temperatura", "💧 Umidade & Pressão", "💨 Vento & Nuvens"])

COLORS = {"temp": "#7eb8f7", "feels": "#f7a25e", "min": "#60dfa9", "max": "#f76e7e",
          "hum": "#60a5fa", "pres": "#a78bfa", "wind": "#34d399", "clouds": "#94a3b8"}

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["temperature"],
                             name="Temperatura", line=dict(color=COLORS["temp"], width=2.5),
                             fill="tozeroy", fillcolor="rgba(126,184,247,0.08)"))
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["feels_like"],
                             name="Sensação", line=dict(color=COLORS["feels"], width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["temp_max"],
                             name="Máx", line=dict(color=COLORS["max"], width=1, dash="dash")))
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["temp_min"],
                             name="Mín", line=dict(color=COLORS["min"], width=1, dash="dash")))
    fig.update_layout(template="plotly_dark", height=380,
                      yaxis_title="°C", xaxis_title=None,
                      legend=dict(orientation="h", y=1.1),
                      margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df["datetime"], y=df["humidity"],
                         name="Umidade (%)", marker_color=COLORS["hum"], opacity=0.7))
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["pressure"],
                             name="Pressão (hPa)", line=dict(color=COLORS["pres"], width=2)),
                  secondary_y=True)
    fig.update_layout(template="plotly_dark", height=380,
                      legend=dict(orientation="h", y=1.1),
                      margin=dict(l=0, r=0, t=30, b=0))
    fig.update_yaxes(title_text="Umidade (%)", secondary_y=False)
    fig.update_yaxes(title_text="Pressão (hPa)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df["datetime"], y=df["wind_speed"],
                             name="Vento (m/s)", line=dict(color=COLORS["wind"], width=2.5),
                             fill="tozeroy", fillcolor="rgba(52,211,153,0.08)"))
    fig.add_trace(go.Bar(x=df["datetime"], y=df["clouds"],
                         name="Nuvens (%)", marker_color=COLORS["clouds"], opacity=0.5),
                  secondary_y=True)
    fig.update_layout(template="plotly_dark", height=380,
                      legend=dict(orientation="h", y=1.1),
                      margin=dict(l=0, r=0, t=30, b=0))
    fig.update_yaxes(title_text="Vento (m/s)", secondary_y=False)
    fig.update_yaxes(title_text="Nuvens (%)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

# ── Distribuição de condições ─────────────────────────────────────────────────
st.markdown("### 🗂️ Condições climáticas")
c1, c2 = st.columns([1, 2])

with c1:
    cond_counts = df["weather_main"].value_counts().reset_index()
    cond_counts.columns = ["Condição", "Ocorrências"]
    fig_pie = px.pie(cond_counts, names="Condição", values="Ocorrências",
                     hole=0.55, template="plotly_dark",
                     color_discrete_sequence=px.colors.sequential.Blues_r)
    fig_pie.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                          showlegend=True,
                          legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.markdown("##### Últimas 10 leituras")
    display_cols = ["datetime", "temperature", "feels_like", "humidity",
                    "wind_speed", "clouds", "weather_description"]
    recent = df[display_cols].tail(10).copy()
    recent["datetime"] = recent["datetime"].dt.strftime("%d/%m %H:%M")
    recent.columns = ["Data/Hora", "Temp °C", "Sensação °C", "Umidade %",
                      "Vento m/s", "Nuvens %", "Condição"]
    st.dataframe(recent.iloc[::-1], use_container_width=True, hide_index=True)

# ── Rodapé ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<div class='last-update' style='text-align:center'>"
    f"🗄️ {len(df)} registros carregados | "
    f"⏱️ Período: {df['datetime'].min().strftime('%d/%m %H:%M')} → "
    f"{df['datetime'].max().strftime('%d/%m %H:%M')} | "
    f"Fonte: OpenWeatherMap + PostgreSQL"
    f"</div>",
    unsafe_allow_html=True,
)