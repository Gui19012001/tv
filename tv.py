import streamlit as st
import pandas as pd
import datetime
import pytz
from supabase import create_client
import os
from dotenv import load_dotenv
from pathlib import Path
import streamlit.components.v1 as components

# ==============================
# ✅ PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="One Page Gerencial — Linhas",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================
# Autorefresh
# ==============================
try:
    from streamlit_autorefresh import st_autorefresh
    AUTORELOAD_AVAILABLE = True
except ImportError:
    AUTORELOAD_AVAILABLE = False

# ==============================
# ENV / SUPABASE
# ==============================
env_path = Path(__file__).parent / "teste.env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL / SUPABASE_KEY não encontrados no teste.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TZ = pytz.timezone("America/Sao_Paulo")

# ==============================
# CSS APP
# ==============================
def aplicar_css_app():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.6rem;
            padding-bottom: 0.8rem;
            padding-left: 1.2rem;
            padding-right: 1.2rem;
            max-width: 100%;
        }
        header[data-testid="stHeader"] {display:none;}
        div[data-testid="stToolbar"] {visibility:hidden;height:0%;position:fixed;}
        section[data-testid='stSidebar']{display:none;}

        .stApp {
            background: radial-gradient(circle at 15% 15%, rgba(64,93,230,0.55), rgba(0,0,0,0) 40%),
                        radial-gradient(circle at 85% 25%, rgba(0,255,200,0.18), rgba(0,0,0,0) 40%),
                        linear-gradient(135deg, #05070d 0%, #071124 55%, #0a1630 100%);
        }

        .op-title {
            font-size: 22px;
            font-weight: 900;
            color: #EAF2FF;
            letter-spacing: 0.5px;
            margin: 2px 0 6px 0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ==============================
# ✅ Parser de data_hora robusto (corrige MOLA no "atual")
# ==============================
def _parse_datahora(df: pd.DataFrame, col: str = "data_hora") -> pd.DataFrame:
    if df is None or df.empty or col not in df.columns:
        return df

    dt = pd.to_datetime(df[col], errors="coerce")

    # Se já vier com timezone (ex: "...Z" ou offset)
    if getattr(dt.dt, "tz", None) is not None:
        df[col] = dt.dt.tz_convert(TZ)
        return df

    # Se veio "naive" (sem tz), assume que foi gravado no horário local
    df[col] = dt.dt.tz_localize(TZ)
    return df

# ==============================
# Supabase load (paginado)
# ==============================
def _load_table_paged(table_name: str, date_col="data_hora") -> pd.DataFrame:
    data_total = []
    inicio = 0
    passo = 1000
    while True:
        resp = supabase.table(table_name).select("*").range(inicio, inicio + passo - 1).execute()
        dados = resp.data
        if not dados:
            break
        data_total.extend(dados)
        inicio += passo

    df = pd.DataFrame(data_total)
    if not df.empty and date_col in df.columns:
        df = _parse_datahora(df, date_col)
    return df

# ✅ TTL maior (600s) pra não estourar consulta e ficar leve na TV
@st.cache_data(ttl=600)
def carregar_apontamentos_esteira():
    return _load_table_paged("apontamentos")

@st.cache_data(ttl=600)
def carregar_checklists_esteira():
    return _load_table_paged("checklists")

@st.cache_data(ttl=600)
def carregar_apontamentos_mola():
    return _load_table_paged("apontamentos_mola")

@st.cache_data(ttl=600)
def carregar_checklists_mola():
    return _load_table_paged("checklists_mola_detalhes")

@st.cache_data(ttl=600)
def carregar_apontamentos_manga_pnm():
    return _load_table_paged("apontamentos_manga_pnm")

@st.cache_data(ttl=600)
def carregar_checklists_manga_pnm():
    return _load_table_paged("checklists_manga_pnm_detalhes")

# ==============================
# Helpers cálculo
# ==============================
def filtrar_periodo(df: pd.DataFrame, data_inicio: datetime.date, data_fim: datetime.date) -> pd.DataFrame:
    if df is None or df.empty or "data_hora" not in df.columns:
        return pd.DataFrame()
    dff = df.copy()
    dff = dff[dff["data_hora"].notna()]
    return dff[(dff["data_hora"].dt.date >= data_inicio) & (dff["data_hora"].dt.date <= data_fim)]

def calcular_meta_acumulada_por_hora(meta_hora: dict, hoje: datetime.date, hora_atual: datetime.datetime, modo="fim_hora") -> int:
    meta_acumulada = 0
    if modo == "inicio_hora":
        hora_atual_fechada = hora_atual.replace(minute=0, second=0, microsecond=0)
        for h, m in meta_hora.items():
            horario_inicio = datetime.datetime.combine(hoje, h)
            if horario_inicio.tzinfo is None:
                horario_inicio = TZ.localize(horario_inicio)
            if horario_inicio < hora_atual_fechada:
                meta_acumulada += int(m)
    else:
        for h, m in meta_hora.items():
            horario_fim = datetime.datetime.combine(hoje, h) + datetime.timedelta(hours=1)
            if horario_fim.tzinfo is None:
                horario_fim = TZ.localize(horario_fim)
            if hora_atual >= horario_fim:
                meta_acumulada += int(m)
    return int(meta_acumulada)

def calcular_aprovacao(df_checks: pd.DataFrame, df_apont: pd.DataFrame) -> tuple[float, int]:
    if df_checks is None or df_checks.empty or df_apont is None or df_apont.empty:
        return 0.0, 0
    if "numero_serie" not in df_apont.columns or "numero_serie" not in df_checks.columns:
        return 0.0, 0

    df_checks_filtrado = df_checks[df_checks["numero_serie"].isin(df_apont["numero_serie"].unique())].copy()
    if df_checks_filtrado.empty:
        return 0.0, 0

    series_unicas = df_checks_filtrado["numero_serie"].dropna().unique()
    aprovados = 0

    for serie in series_unicas:
        checks = df_checks_filtrado[df_checks_filtrado["numero_serie"] == serie]
        if checks.empty:
            continue

        teve_reinspecao = False
        if "reinspecao" in checks.columns:
            teve_reinspecao = (checks["reinspecao"].astype(str).str.strip().str.lower() == "sim").any()

        aprovado = True
        if "produto_reprovado" in checks.columns:
            ultimo = str(checks.tail(1).iloc[0].get("produto_reprovado", "Não")).strip().lower()
            aprovado = (ultimo == "não") and (not teve_reinspecao)
        else:
            ultimo_status = str(checks.tail(1).iloc[0].get("status", "")).strip().lower()
            aprovado = (ultimo_status != "não conforme") and (not teve_reinspecao)

        if aprovado:
            aprovados += 1

    total_inspecionado = int(len(series_unicas))
    aprovacao_perc = (aprovados / total_inspecionado) * 100 if total_inspecionado > 0 else 0.0
    return float(aprovacao_perc), total_inspecionado

def calcular_oee(atraso: int, meta_acumulada: int, aprovacao_perc: float) -> float:
    performance_fraction = max(1 - (atraso / meta_acumulada), 0) if meta_acumulada > 0 else 1
    quality_fraction = (aprovacao_perc / 100) if aprovacao_perc > 0 else 1
    return float(performance_fraction * quality_fraction * 100)

# ==============================
# Resumos (4 cards: Esteira, Mola, Manga, PNM)
# ==============================
def resumo_esteira(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos_esteira(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists_esteira(), data_inicio, data_fim)

    # ESTEIRA/EIXO na base geral
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        df_apont = df_apont[df_apont["tipo_producao"].astype(str).str.contains("ESTEIRA|EIXO", case=False, na=False)]

    meta_hora = {
        datetime.time(6,0):26, datetime.time(7,0):26, datetime.time(8,0):26,
        datetime.time(9,0):26, datetime.time(10,0):26, datetime.time(11,0):6,
        datetime.time(12,0):26, datetime.time(13,0):26, datetime.time(14,0):26,
        datetime.time(15,0):12
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    return {
        "key": "esteira",
        "nome": "ESTEIRA",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": "",
        "oee": oee
    }

def resumo_mola(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos_mola(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists_mola(), data_inicio, data_fim)

    meta_hora = {
        datetime.time(6, 0): 14, datetime.time(7, 0): 14, datetime.time(8, 0): 14,
        datetime.time(9, 0): 14, datetime.time(10, 0): 14, datetime.time(11, 0): 14,
        datetime.time(12, 0): 0,  datetime.time(13, 0): 14, datetime.time(14, 0): 14,
        datetime.time(15, 0): 8,  datetime.time(16, 0): 14, datetime.time(17, 0): 1,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="inicio_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    return {
        "key": "mola",
        "nome": "MONTAGEM MOLA",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": "",
        "oee": oee
    }

def resumo_manga(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos_manga_pnm(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists_manga_pnm(), data_inicio, data_fim)

    # ✅ separa só MANGA (na base manga_pnm)
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        df_apont = df_apont[df_apont["tipo_producao"].astype(str).str.contains("MANGA", case=False, na=False)]
    if not df_checks.empty and "tipo_producao" in df_checks.columns:
        df_checks = df_checks[df_checks["tipo_producao"].astype(str).str.contains("MANGA", case=False, na=False)]

    meta_hora = {
        datetime.time(6, 0): 4, datetime.time(7, 0): 4, datetime.time(8, 0): 4,
        datetime.time(9, 0): 4, datetime.time(10, 0): 4, datetime.time(11, 0): 0,
        datetime.time(12, 0): 4, datetime.time(13, 0): 4, datetime.time(14, 0): 4,
        datetime.time(15, 0): 4,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    return {
        "key": "manga",
        "nome": "MONTAGEM MANGA",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": "",
        "oee": oee
    }

def resumo_pnm(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos_manga_pnm(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists_manga_pnm(), data_inicio, data_fim)

    # ✅ separa só PNM (na base manga_pnm)
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        df_apont = df_apont[df_apont["tipo_producao"].astype(str).str.contains("PNM", case=False, na=False)]
    if not df_checks.empty and "tipo_producao" in df_checks.columns:
        df_checks = df_checks[df_checks["tipo_producao"].astype(str).str.contains("PNM", case=False, na=False)]

    meta_hora = {
        datetime.time(6, 0): 4, datetime.time(7, 0): 4, datetime.time(8, 0): 4,
        datetime.time(9, 0): 4, datetime.time(10, 0): 4, datetime.time(11, 0): 0,
        datetime.time(12, 0): 4, datetime.time(13, 0): 4, datetime.time(14, 0): 4,
        datetime.time(15, 0): 4,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    return {
        "key": "pnm",
        "nome": "MONTAGEM PNM",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": "",
        "oee": oee
    }

# ==============================
# ONEPAGE (1 iframe, 4 cards alinhados)
# ==============================
def render_onepage_html(resumos: list[dict]):
    HEIGHT = 380

    js_data = [{"key": r["key"], "oee": round(float(r["oee"]), 1)} for r in resumos]

    def pill_for(r: dict) -> tuple[str, str, str]:
        status_ok = (int(r.get("atraso", 0)) == 0) and ("sem fonte" not in str(r.get("status", "")).lower())
        if status_ok:
            return "OK", "rgba(56,161,105,0.25)", "rgba(56,161,105,0.55)"
        return "ATENÇÃO", "rgba(197,48,48,0.22)", "rgba(197,48,48,0.55)"

    cards_html = []
    for r in resumos:
        pill_txt, pill_bg, pill_bd = pill_for(r)
        cards_html.append(f"""
          <div class="card">
            <div class="head">
              <div>
                <div class="title">{r["nome"]}</div>
                <div class="sub">One Page • Produção & Qualidade</div>
              </div>
              <div class="pill" style="background:{pill_bg}; border:1px solid {pill_bd};">{pill_txt}</div>
            </div>

            <div class="mini-grid">
              <div class="mini">
                <div class="mini-title">Total produzido</div>
                <div class="mini-val">{r["total"]}</div>
                <div class="mini-foot">{r["rodape"]}</div>
              </div>

              <div class="mini">
                <div class="mini-title">% Aprovação</div>
                <div class="mini-val">{float(r["aprovacao"]):.1f}%</div>
                <div class="mini-foot">Inspecionado: {r["inspecionado"]}</div>
              </div>

              <div class="mini">
                <div class="mini-title">Status</div>
                <div class="mini-val" style="font-size:16px;">{r["status"]}</div>
                <div class="mini-foot">Meta vs Real (acumulado)</div>
              </div>

              <div class="mini">
                <div class="oee-row">
                  <div class="mini-title" style="margin:0;">OEE</div>
                  <div class="mini-val" style="font-size:16px;">{float(r["oee"]):.1f}%</div>
                </div>
                <div id="g_{r["key"]}" class="gauge"></div>
              </div>
            </div>
          </div>
        """)

    html = f"""
    <div style="width:100%;">
      <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>

      <style>
        .grid-4 {{
          display:grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 26px;
          align-items: stretch;
        }}

        .card {{
          border-radius:22px;
          padding:14px 14px 12px 14px;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.10);
          box-shadow: 0 14px 30px rgba(0,0,0,0.35);
          backdrop-filter: blur(10px);
          height: 330px;
          overflow: hidden;
          color: white;
          font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
        }}

        .head {{
          display:flex;
          align-items:flex-start;
          justify-content:space-between;
          gap:10px;
          margin-bottom:10px;
        }}

        .title {{
          font-size:14px;
          font-weight:950;
          color:#EAF2FF;
          text-transform:uppercase;
          line-height:1.05;
        }}
        .sub {{
          font-size:12px;
          color: rgba(255,255,255,0.70);
          margin-top:3px;
        }}

        .pill {{
          font-size:11px;
          font-weight:950;
          padding:6px 10px;
          border-radius:999px;
          color:#EAF2FF;
          white-space:nowrap;
        }}

        .mini-grid {{
          display:grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }}

        .mini {{
          border-radius:18px;
          padding:10px 12px;
          background: rgba(0,0,0,0.28);
          border:1px solid rgba(255,255,255,0.10);
          height: 96px;
          overflow:hidden;
        }}

        .mini-title {{
          font-size:11px;
          font-weight:950;
          color:rgba(255,255,255,0.84);
          margin-bottom:6px;
          text-transform:uppercase;
          letter-spacing: .2px;
        }}

        .mini-val {{
          font-size:18px;
          font-weight:950;
          line-height:1.05;
        }}

        .mini-foot {{
          font-size:11px;
          color:rgba(255,255,255,0.70);
          margin-top:4px;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }}

        .oee-row {{
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:10px;
        }}

        .gauge {{
          height: 64px;
          width: 100%;
          margin-top: 2px;
        }}

        @media (max-width: 1400px) {{
          .grid-4 {{ grid-template-columns: repeat(2, 1fr); }}
          .card {{ height: 330px; }}
        }}
      </style>

      <div class="grid-4">
        {''.join(cards_html)}
      </div>

      <script>
        const dados = {js_data};

        function renderGauge(id, val) {{
          const data = [{{
            type: "indicator",
            mode: "gauge",
            value: val,
            gauge: {{
              axis: {{ range: [0, 100], tickwidth: 0, ticklen: 0 }},
              bar: {{ color: "#1E90FF", thickness: 0.35 }},
              steps: [
                {{ range: [0, 60], color: "#FF4C4C" }},
                {{ range: [60, 85], color: "#FFD700" }},
                {{ range: [85, 100], color: "#4CAF50" }}
              ],
              threshold: {{
                line: {{ color: "black", width: 2 }},
                thickness: 0.65,
                value: 85
              }}
            }}
          }}];

          const layout = {{
            margin: {{ l: 0, r: 0, t: 0, b: 0 }},
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            height: 64
          }};

          Plotly.newPlot(id, data, layout, {{displayModeBar:false, responsive:true}});
        }}

        dados.forEach(d => renderGauge("g_" + d.key, d.oee));
      </script>
    </div>
    """

    components.html(html, height=HEIGHT, scrolling=False)

# ==============================
# Main
# ==============================
def main():
    aplicar_css_app()

    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key="onepage_refresh")

    hoje = datetime.datetime.now(TZ).date()

    params = st.query_params
    inicio_str = params.get("inicio", None)
    fim_str = params.get("fim", None)

    if inicio_str and fim_str:
        try:
            data_inicio = datetime.datetime.strptime(inicio_str, "%Y-%m-%d").date()
            data_fim = datetime.datetime.strptime(fim_str, "%Y-%m-%d").date()
        except Exception:
            data_inicio = hoje
            data_fim = hoje
    else:
        data_inicio = hoje
        data_fim = hoje

    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:rgba(255,255,255,0.70); margin-bottom:10px;'>Período: <b>{data_inicio}</b> até <b>{data_fim}</b></div>",
        unsafe_allow_html=True
    )

    # ✅ 4 CARDS: ESTEIRA, MOLA, MANGA, PNM
    resumos = [
        resumo_esteira(data_inicio, data_fim),
        resumo_mola(data_inicio, data_fim),
        resumo_manga(data_inicio, data_fim),
        resumo_pnm(data_inicio, data_fim),
    ]

    render_onepage_html(resumos)

    hora = datetime.datetime.now(TZ).strftime("%H:%M:%S")
    st.markdown(
        f"<p style='color:rgba(255,255,255,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{hora}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
