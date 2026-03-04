import os
import datetime
from pathlib import Path

import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from supabase import create_client

# OpenAI (SDK novo)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# ==============================
# ✅ PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="One Page Gerencial — Linhas",
    layout="wide",
    initial_sidebar_state="collapsed"  # sidebar começa recolhida
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
# ENV / SUPABASE / OPENAI
# ==============================
env_path = Path(__file__).parent / "teste.env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL / SUPABASE_KEY não encontrados no teste.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TZ = pytz.timezone("America/Sao_Paulo")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1").strip()

openai_client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# CSS (APP branco + cards azul marinho)
# + mantém botão do sidebar acessível
# + reduz “piscada” (sem esconder header totalmente)
# ==============================
def aplicar_css_app():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 0.8rem;
            padding-left: 1.2rem;
            padding-right: 1.2rem;
            max-width: 100%;
        }

        /* Não “mata” o header (senão some o botão do sidebar) */
        header[data-testid="stHeader"] {
            background: transparent;
            border: none;
        }

        /* Esconde toolbar, mas mantém header vivo */
        div[data-testid="stToolbar"] {visibility:hidden;height:0;position:fixed;}

        /* Deixa o botão do sidebar sempre acessível */
        button[data-testid="stSidebarCollapseButton"]{
            position: fixed !important;
            top: 12px !important;
            left: 10px !important;
            z-index: 999999 !important;
            opacity: 0.35;
            transform: scale(1.05);
        }
        button[data-testid="stSidebarCollapseButton"]:hover{opacity: 1;}

        /* Reduz widgets/efeitos visuais de status */
        div[data-testid="stStatusWidget"] {display:none !important;}
        div[data-testid="stDecoration"] {display:none !important;}

        /* Fundo branco clean */
        .stApp {
            background: #F6F7FB;
        }

        .op-title {
            font-size: 22px;
            font-weight: 900;
            color: #0B1B33;
            letter-spacing: 0.4px;
            margin: 2px 0 4px 0;
        }

        .op-sub {
            color: rgba(11,27,51,0.70);
            margin-bottom: 10px;
        }

        /* Sidebar clean */
        section[data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid rgba(11,27,51,0.10);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ==============================
# ✅ Parser de data_hora robusto
# ==============================
def _parse_datahora(df: pd.DataFrame, col: str = "data_hora") -> pd.DataFrame:
    if df is None or df.empty or col not in df.columns:
        return df

    dt = pd.to_datetime(df[col], errors="coerce")

    # timezone-aware
    if getattr(dt.dt, "tz", None) is not None:
        df[col] = dt.dt.tz_convert(TZ)
        return df

    # naive -> assume local
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

# ✅ TTL maior pra TV e pra não “piscar”
@st.cache_data(ttl=600, show_spinner=False)
def carregar_apontamentos():
    return _load_table_paged("apontamentos")

@st.cache_data(ttl=600, show_spinner=False)
def carregar_checklists():
    return _load_table_paged("checklists")

@st.cache_data(ttl=600, show_spinner=False)
def carregar_apontamentos_mola():
    return _load_table_paged("apontamentos_mola")

@st.cache_data(ttl=600, show_spinner=False)
def carregar_checklists_mola():
    return _load_table_paged("checklists_mola_detalhes")

@st.cache_data(ttl=600, show_spinner=False)
def carregar_apontamentos_manga_pnm():
    return _load_table_paged("apontamentos_manga_pnm")

@st.cache_data(ttl=600, show_spinner=False)
def carregar_checklists_manga_pnm():
    return _load_table_paged("checklists_manga_pnm_detalhes")

# ==============================
# Helpers
# ==============================
def filtrar_periodo(df: pd.DataFrame, data_inicio: datetime.date, data_fim: datetime.date) -> pd.DataFrame:
    if df is None or df.empty or "data_hora" not in df.columns:
        return pd.DataFrame()
    dff = df.copy()
    dff = dff[dff["data_hora"].notna()]
    return dff[(dff["data_hora"].dt.date >= data_inicio) & (dff["data_hora"].dt.date <= data_fim)]

def _norm(x) -> str:
    return str(x).strip().lower()

def _is_sim(x) -> bool:
    v = _norm(x)
    return v in ("sim", "s", "1", "true", "verdadeiro", "yes", "y")

def _is_nao(x) -> bool:
    v = _norm(x)
    return v in ("não", "nao", "n", "0", "false", "falso", "no")

def _is_reprovado_row(row: pd.Series) -> bool:
    # status
    if "status" in row.index and _norm(row.get("status")) in ("não conforme", "nao conforme", "reprovado"):
        return True

    # produto_reprovado: "Sim" = reprovado
    if "produto_reprovado" in row.index:
        pr = row.get("produto_reprovado")
        if _is_sim(pr):
            return True
        if _is_nao(pr):
            return False

    # flags alternativas
    for col in ("reprovado", "aprovado"):
        if col in row.index:
            v = row.get(col)
            if col == "reprovado" and _is_sim(v):
                return True
            if col == "aprovado" and _is_nao(v):
                return True

    return False

def calcular_aprovacao(df_checks: pd.DataFrame, df_apont: pd.DataFrame) -> tuple[float, int, int]:
    """
    Retorna: (aprovacao %, total_inspecionado, total_reprovados)
    Usa o ÚLTIMO registro por numero_serie (por data_hora se existir).
    """
    if df_checks is None or df_checks.empty or df_apont is None or df_apont.empty:
        return 0.0, 0, 0
    if "numero_serie" not in df_apont.columns or "numero_serie" not in df_checks.columns:
        return 0.0, 0, 0

    series_validas = pd.Series(df_apont["numero_serie"].dropna().unique())
    dfc = df_checks[df_checks["numero_serie"].isin(series_validas)].copy()
    if dfc.empty:
        return 0.0, 0, 0

    # ordena se tiver data_hora
    if "data_hora" in dfc.columns:
        dfc = dfc[dfc["data_hora"].notna()].copy()
        dfc = dfc.sort_values(["numero_serie", "data_hora"])
        ult = dfc.groupby("numero_serie", as_index=False).tail(1)
    else:
        ult = dfc.groupby("numero_serie", as_index=False).tail(1)

    total_inspecionado = int(ult["numero_serie"].nunique())
    if total_inspecionado == 0:
        return 0.0, 0, 0

    reprovados = 0
    for _, row in ult.iterrows():
        if _is_reprovado_row(row):
            reprovados += 1

    aprovados = total_inspecionado - reprovados
    aprovacao_perc = (aprovados / total_inspecionado) * 100
    return float(aprovacao_perc), total_inspecionado, int(reprovados)

def calcular_meta_acumulada_por_hora(meta_hora: dict, hoje: datetime.date, hora_atual: datetime.datetime, modo="fim_hora") -> int:
    meta_acumulada = 0

    if modo == "inicio_hora":
        hora_atual_fechada = hora_atual.replace(minute=0, second=0, microsecond=0)
        for h, m in meta_hora.items():
            inicio = datetime.datetime.combine(hoje, h)
            if inicio.tzinfo is None:
                inicio = TZ.localize(inicio)
            if inicio < hora_atual_fechada:
                meta_acumulada += int(m)
    else:
        for h, m in meta_hora.items():
            fim = datetime.datetime.combine(hoje, h) + datetime.timedelta(hours=1)
            if fim.tzinfo is None:
                fim = TZ.localize(fim)
            if hora_atual >= fim:
                meta_acumulada += int(m)

    return int(meta_acumulada)

def calcular_oee(atraso: int, meta_acumulada: int, aprovacao_perc: float) -> float:
    performance_fraction = max(1 - (atraso / meta_acumulada), 0) if meta_acumulada > 0 else 1
    quality_fraction = (aprovacao_perc / 100) if aprovacao_perc > 0 else 0
    return float(performance_fraction * quality_fraction * 100)

def primeiro_dia_mes(d: datetime.date) -> datetime.date:
    return d.replace(day=1)

def is_workday(d: datetime.date) -> bool:
    # Seg(0) ... Dom(6)
    return d.weekday() < 5

def meta_mes_total(meta_hora: dict, data_ini: datetime.date, data_fim: datetime.date) -> int:
    meta_dia = int(sum(int(v) for v in meta_hora.values()))
    total = 0
    d = data_ini
    while d <= data_fim:
        if is_workday(d):
            total += meta_dia
        d += datetime.timedelta(days=1)
    return int(total)

# ==============================
# Resumos (3 cards: TOTAL apontamentos, MOLA, MANGA&PNM)
# ==============================
def resumo_total_apontamentos(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists(), data_inicio, data_fim)

    meta_hora = {
        datetime.time(6,0):26, datetime.time(7,0):26, datetime.time(8,0):26,
        datetime.time(9,0):26, datetime.time(10,0):26, datetime.time(11,0):6,
        datetime.time(12,0):26, datetime.time(13,0):26, datetime.time(14,0):26,
        datetime.time(15,0):12
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    rodape = ""
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        tp = df_apont["tipo_producao"].astype(str)
        eixo = int(tp.str.contains("EIXO|ESTEIRA", case=False, na=False).sum())
        manga = int(tp.str.contains("MANGA", case=False, na=False).sum())
        pnm = int(tp.str.contains("PNM", case=False, na=False).sum())
        rodape = f"Eixo/Esteira: {eixo} | Manga: {manga} | PNM: {pnm}"

    return {
        "key": "total",
        "nome": "APONTAMENTOS (TOTAL)",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "reprovados": rep,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": rodape,
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

    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    rodape = f"Reprovados: {rep}" if insp > 0 else ""

    return {
        "key": "mola",
        "nome": "MONTAGEM MOLA",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "reprovados": rep,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": rodape,
        "oee": oee
    }

def resumo_manga_pnm(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos_manga_pnm(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists_manga_pnm(), data_inicio, data_fim)

    meta_hora = {
        datetime.time(6, 0): 4, datetime.time(7, 0): 4, datetime.time(8, 0): 4,
        datetime.time(9, 0): 4, datetime.time(10, 0): 4, datetime.time(11, 0): 0,
        datetime.time(12, 0): 4, datetime.time(13, 0): 4, datetime.time(14, 0): 4,
        datetime.time(15, 0): 4,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    rodape = ""
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        tp = df_apont["tipo_producao"].astype(str)
        manga = int(tp.str.contains("MANGA", case=False, na=False).sum())
        pnm = int(tp.str.contains("PNM", case=False, na=False).sum())
        rodape = f"MANGA: {manga} | PNM: {pnm}"

    return {
        "key": "manga_pnm",
        "nome": "MONTAGEM MANGA & PNM",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "reprovados": rep,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": rodape,
        "oee": oee
    }

# ==============================
# ONEPAGE HTML (3 cards alinhados)
# ==============================
def render_onepage_html(resumos: list[dict]) -> tuple[str, int]:
    HEIGHT = 430
    js_data = [{"key": r["key"], "oee": round(float(r["oee"]), 1)} for r in resumos]

    def pill_for(r: dict) -> tuple[str, str, str]:
        status_ok = (int(r.get("atraso", 0)) == 0)
        if status_ok:
            return "OK", "rgba(56,161,105,0.16)", "rgba(56,161,105,0.40)"
        return "ATENÇÃO", "rgba(197,48,48,0.12)", "rgba(197,48,48,0.38)"

    cards_html = []
    for r in resumos:
        pill_txt, pill_bg, pill_bd = pill_for(r)
        reprovados_txt = ""
        if int(r.get("inspecionado", 0)) > 0:
            reprovados_txt = f" • Reprovados: {int(r.get('reprovados', 0))}"

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
                <div class="mini-foot">Inspecionado: {r["inspecionado"]}{reprovados_txt}</div>
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
                <div class="gauge-axis"><span>0%</span><span>100%</span></div>
              </div>
            </div>
          </div>
        """)

    html = f"""
    <div style="width:100%;">
      <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>

      <style>
        .grid-3 {{
          display: grid;
          grid-template-columns: repeat(3, minmax(360px, 1fr));
          gap: 26px;
          align-items: stretch;
          width: 100%;
        }}

        .card {{
          border-radius: 22px;
          padding: 16px;
          background: linear-gradient(135deg, #071124 0%, #0B1B33 55%, #093A5A 100%);
          border: 1px solid rgba(255,255,255,0.10);
          box-shadow: 0 14px 26px rgba(0,0,0,0.18);
          height: 345px;
          overflow: hidden;
          color: white;
          font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
        }}

        .head {{
          display:flex;
          align-items:flex-start;
          justify-content:space-between;
          gap:10px;
          margin-bottom:12px;
        }}

        .title {{
          font-size:14px;
          font-weight:950;
          color:#F3F7FF;
          text-transform:uppercase;
          line-height:1.05;
        }}
        .sub {{
          font-size:12px;
          color: rgba(255,255,255,0.78);
          margin-top:3px;
        }}

        .pill {{
          font-size:11px;
          font-weight:950;
          padding:6px 10px;
          border-radius:999px;
          color:#F3F7FF;
          white-space:nowrap;
        }}

        .mini-grid {{
          display:grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }}

        .mini {{
          border-radius:18px;
          padding:12px 14px;
          background: rgba(255,255,255,0.06);
          border:1px solid rgba(255,255,255,0.10);
          height: 108px;
          overflow:hidden;
        }}

        .mini-title {{
          font-size:11px;
          font-weight:950;
          color:rgba(255,255,255,0.86);
          margin-bottom:6px;
          text-transform:uppercase;
          letter-spacing: .25px;
        }}

        .mini-val {{
          font-size:20px;
          font-weight:950;
          line-height:1.05;
        }}

        .mini-foot {{
          font-size:11px;
          color:rgba(255,255,255,0.72);
          margin-top:5px;
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
          height: 76px;
          width: 100%;
          margin-top: 2px;
        }}

        .gauge-axis {{
          margin-top: 2px;
          display:flex;
          justify-content:space-between;
          font-size:10px;
          color: rgba(255,255,255,0.72);
          padding: 0 2px;
        }}

        @media (max-width: 1280px) {{
          .grid-3 {{ grid-template-columns: repeat(2, minmax(360px, 1fr)); }}
        }}
        @media (max-width: 860px) {{
          .grid-3 {{ grid-template-columns: 1fr; }}
        }}
      </style>

      <div class="grid-3">
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
              axis: {{ range: [0, 100], showticklabels: false, tickwidth: 0, ticklen: 0 }},
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
            height: 76
          }};

          Plotly.newPlot(id, data, layout, {{displayModeBar:false, responsive:true}});
        }}

        dados.forEach(d => renderGauge("g_" + d.key, d.oee));
      </script>
    </div>
    """
    return html, HEIGHT

# ==============================
# Pareto Top 3 (reprovações)
# ==============================
def _guess_fail_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    candidates = [
        "falha", "defeito", "motivo", "motivo_falha", "causa",
        "nao_conformidade", "não_conformidade", "descricao_falha",
        "observacao", "observação", "item", "problema"
    ]
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None

def pareto_top3(df_checks: pd.DataFrame) -> list[tuple[str, int]]:
    if df_checks is None or df_checks.empty:
        return []
    fail_col = _guess_fail_col(df_checks)
    if not fail_col:
        return []
    dfr = df_checks.copy()
    # filtra só reprovados
    mask_rep = dfr.apply(_is_reprovado_row, axis=1)
    dfr = dfr[mask_rep]
    if dfr.empty:
        return []
    vc = dfr[fail_col].astype(str).str.strip()
    vc = vc[vc.ne("") & vc.ne("nan")]
    if vc.empty:
        return []
    top = vc.value_counts().head(3)
    return [(str(idx), int(val)) for idx, val in top.items()]

# ==============================
# Página 1: One Page (congela no refresh)
# ==============================
def page_onepage(data_inicio: datetime.date, data_fim: datetime.date):
    ph = st.empty()

    # mostra último HTML antes de recalcular
    if "last_html_onepage" in st.session_state and "last_height_onepage" in st.session_state:
        with ph.container():
            components.html(st.session_state["last_html_onepage"], height=st.session_state["last_height_onepage"], scrolling=False)

    resumos = [
        resumo_total_apontamentos(data_inicio, data_fim),
        resumo_mola(data_inicio, data_fim),
        resumo_manga_pnm(data_inicio, data_fim),
    ]

    html, height = render_onepage_html(resumos)

    with ph.container():
        components.html(html, height=height, scrolling=False)

    st.session_state["last_html_onepage"] = html
    st.session_state["last_height_onepage"] = height

# ==============================
# Página 2: Resumo Mensal + IA
# ==============================
def page_resumo_ia():
    hoje = datetime.datetime.now(TZ).date()
    ini_mes = primeiro_dia_mes(hoje)
    fim = hoje

    st.markdown("### Resumo do mês (Performance & Qualidade)")
    st.caption(f"Período: {ini_mes} até {fim}")

    # Carrega bases do mês
    a_total = filtrar_periodo(carregar_apontamentos(), ini_mes, fim)
    c_total = filtrar_periodo(carregar_checklists(), ini_mes, fim)

    a_mola = filtrar_periodo(carregar_apontamentos_mola(), ini_mes, fim)
    c_mola = filtrar_periodo(carregar_checklists_mola(), ini_mes, fim)

    a_mp = filtrar_periodo(carregar_apontamentos_manga_pnm(), ini_mes, fim)
    c_mp = filtrar_periodo(carregar_checklists_manga_pnm(), ini_mes, fim)

    # Metas (mensal)
    meta_total_hora = {
        datetime.time(6,0):26, datetime.time(7,0):26, datetime.time(8,0):26,
        datetime.time(9,0):26, datetime.time(10,0):26, datetime.time(11,0):6,
        datetime.time(12,0):26, datetime.time(13,0):26, datetime.time(14,0):26,
        datetime.time(15,0):12
    }
    meta_mola_hora = {
        datetime.time(6, 0): 14, datetime.time(7, 0): 14, datetime.time(8, 0): 14,
        datetime.time(9, 0): 14, datetime.time(10, 0): 14, datetime.time(11, 0): 14,
        datetime.time(12, 0): 0,  datetime.time(13, 0): 14, datetime.time(14, 0): 14,
        datetime.time(15, 0): 8,  datetime.time(16, 0): 14, datetime.time(17, 0): 1,
    }
    meta_mp_hora = {
        datetime.time(6, 0): 4, datetime.time(7, 0): 4, datetime.time(8, 0): 4,
        datetime.time(9, 0): 4, datetime.time(10, 0): 4, datetime.time(11, 0): 0,
        datetime.time(12, 0): 4, datetime.time(13, 0): 4, datetime.time(14, 0): 4,
        datetime.time(15, 0): 4,
    }

    meta_total_mes = meta_mes_total(meta_total_hora, ini_mes, fim)
    meta_mola_mes = meta_mes_total(meta_mola_hora, ini_mes, fim)
    meta_mp_mes = meta_mes_total(meta_mp_hora, ini_mes, fim)

    # Produção (mensal)
    prod_total = int(len(a_total))
    prod_mola = int(len(a_mola))
    prod_mp = int(len(a_mp))

    # Performance = produzido / meta
    perf_total = (prod_total / meta_total_mes * 100) if meta_total_mes > 0 else 0.0
    perf_mola = (prod_mola / meta_mola_mes * 100) if meta_mola_mes > 0 else 0.0
    perf_mp = (prod_mp / meta_mp_mes * 100) if meta_mp_mes > 0 else 0.0

    # Qualidade (mensal)
    q_total, insp_total, rep_total = calcular_aprovacao(c_total, a_total)
    q_mola, insp_mola, rep_mola = calcular_aprovacao(c_mola, a_mola)
    q_mp, insp_mp, rep_mp = calcular_aprovacao(c_mp, a_mp)

    # Pareto top3 (esteira/total)
    top3_total = pareto_top3(c_total)

    # UI minimalista
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Performance (Total)", f"{perf_total:.1f}%")
        st.caption(f"Produzido: {prod_total} | Meta mês: {meta_total_mes}")
        st.metric("Qualidade (Total)", f"{q_total:.1f}%")
        st.caption(f"Inspec.: {insp_total} | Reprov.: {rep_total}")

    with col2:
        st.metric("Performance (Mola)", f"{perf_mola:.1f}%")
        st.caption(f"Produzido: {prod_mola} | Meta mês: {meta_mola_mes}")
        st.metric("Qualidade (Mola)", f"{q_mola:.1f}%")
        st.caption(f"Inspec.: {insp_mola} | Reprov.: {rep_mola}")

    with col3:
        st.metric("Performance (Manga & PNM)", f"{perf_mp:.1f}%")
        st.caption(f"Produzido: {prod_mp} | Meta mês: {meta_mp_mes}")
        st.metric("Qualidade (Manga & PNM)", f"{q_mp:.1f}%")
        st.caption(f"Inspec.: {insp_mp} | Reprov.: {rep_mp}")

    st.divider()
    st.markdown("#### Pareto (Top 3 falhas) — Total/Esteira")
    if top3_total:
        for i, (nome, qtd) in enumerate(top3_total, start=1):
            st.write(f"**{i}. {nome}** — {qtd}")
    else:
        st.caption("Não achei coluna de falha (ex: falha/defeito/motivo) ou não há reprovações no período.")

    st.divider()

    # IA
    st.markdown("#### Insights (IA)")
    if not OPENAI_API_KEY or not openai_client:
        st.warning("OPENAI_API_KEY não configurada no teste.env (ou SDK openai não instalado).")
        st.caption("Configure OPENAI_API_KEY e reinicie o app.")
        return

    if st.button("Gerar Insights (IA)"):
        payload = {
            "mes": f"{ini_mes} a {fim}",
            "total": {
                "produzido": prod_total,
                "meta_mes": meta_total_mes,
                "performance_pct": round(perf_total, 1),
                "qualidade_pct": round(q_total, 1),
                "inspecionado": insp_total,
                "reprovados": rep_total,
                "pareto_top3": top3_total
            },
            "mola": {
                "produzido": prod_mola,
                "meta_mes": meta_mola_mes,
                "performance_pct": round(perf_mola, 1),
                "qualidade_pct": round(q_mola, 1),
                "inspecionado": insp_mola,
                "reprovados": rep_mola
            },
            "manga_pnm": {
                "produzido": prod_mp,
                "meta_mes": meta_mp_mes,
                "performance_pct": round(perf_mp, 1),
                "qualidade_pct": round(q_mp, 1),
                "inspecionado": insp_mp,
                "reprovados": rep_mp
            },
        }

        prompt = f"""
Você é um analista industrial (produção e qualidade).
Com base nos dados abaixo (JSON), gere um resumo bem minimalista e direto:

1) Situação de PERFORMANCE do mês (Total / Mola / Manga&PNM) e onde está o maior gap.
2) Situação de QUALIDADE do mês e o impacto (reprovados + pareto top3).
3) 3 ações práticas (curtas) para atacar as principais causas.
4) 3 perguntas que eu deveria fazer na reunião de produção amanhã.

Responda em português, com bullets curtos (sem texto longo).
JSON:
{payload}
""".strip()

        with st.spinner("Gerando insights..."):
            # Exemplo oficial do endpoint /responses (SDK novo usa client.responses.create). :contentReference[oaicite:1]{index=1}
            resp = openai_client.responses.create(
                model=OPENAI_MODEL,
                input=prompt
            )

        # extrai texto (tenta o campo mais comum)
        out_text = ""
        try:
            # SDK geralmente traz output_text agregada em resp.output_text
            out_text = getattr(resp, "output_text", "") or ""
        except Exception:
            out_text = ""

        if not out_text:
            # fallback: varre a estrutura
            try:
                for item in resp.output:
                    if item.get("type") == "message":
                        for c in item.get("content", []):
                            if c.get("type") in ("output_text", "text"):
                                out_text += c.get("text", "") + "\n"
            except Exception:
                pass

        st.success("Insights gerados:")
        st.markdown(out_text if out_text else "_Não consegui extrair texto do retorno. Se acontecer, me mande o log do resp._")

# ==============================
# Main
# ==============================
def main():
    aplicar_css_app()

    # ✅ autorefresh com key fixa
    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key="autorefresh_onepage_linhas")

    agora = datetime.datetime.now(TZ)
    hoje = agora.date()

    # Sidebar: navegação + filtros
    st.sidebar.markdown("## Menu")
    default_resumo = (agora.hour >= 16)

    page_options = ["One Page (TV)", "Resumo Mensal + IA"]
    page_default_index = 1 if default_resumo else 0
    pagina = st.sidebar.radio("Página", page_options, index=page_default_index)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtro (Data) — One Page")
    data_inicio = st.sidebar.date_input("Início", hoje, key="f_ini")
    data_fim = st.sidebar.date_input("Fim", hoje, key="f_fim")

    if st.sidebar.button("Atualizar agora"):
        st.cache_data.clear()

    # Header
    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>", unsafe_allow_html=True)

    if pagina == "One Page (TV)":
        st.markdown(
            f"<div class='op-sub'>Período: <b>{data_inicio}</b> até <b>{data_fim}</b></div>",
            unsafe_allow_html=True
        )
        page_onepage(data_inicio, data_fim)
    else:
        st.markdown(
            f"<div class='op-sub'>Modo: <b>Resumo Mensal + IA</b></div>",
            unsafe_allow_html=True
        )
        page_resumo_ia()

    hora = agora.strftime("%H:%M:%S")
    st.markdown(
        f"<p style='color:rgba(11,27,51,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{hora}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
