import os
import datetime
from pathlib import Path

import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from supabase import create_client

# OpenAI
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
# CSS APP + GARANTE SIDEBAR EM TODAS AS PÁGINAS
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

        /* Não mata header (senão perde botão do sidebar) */
        header[data-testid="stHeader"] {
            background: transparent;
            border: none;
        }
        div[data-testid="stToolbar"] {visibility:hidden;height:0;position:fixed;}

        /* Botão do sidebar sempre visível */
        button[data-testid="stSidebarCollapseButton"]{
            position: fixed !important;
            top: 10px !important;
            left: 10px !important;
            z-index: 999999 !important;
            opacity: 0.45;
            transform: scale(1.05);
        }
        button[data-testid="stSidebarCollapseButton"]:hover{opacity: 1;}

        /* Reduz “piscadas” */
        div[data-testid="stStatusWidget"] {display:none !important;}
        div[data-testid="stDecoration"] {display:none !important;}

        /* Fundo branco clean */
        .stApp { background: #F6F7FB; }

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

        section[data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid rgba(11,27,51,0.10);
        }

        /* ==============================
           PÁGINA 2 (VISIONÁRIA) - CSS
        ============================== */
        .v2-wrap{
            border-radius: 22px;
            padding: 18px 18px 16px 18px;
            background:
              radial-gradient(circle at 15% 15%, rgba(64,93,230,0.20), rgba(0,0,0,0) 40%),
              radial-gradient(circle at 85% 25%, rgba(0,255,200,0.10), rgba(0,0,0,0) 45%),
              linear-gradient(135deg, #06122a 0%, #071a3a 60%, #052033 100%);
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow: 0 18px 40px rgba(0,0,0,0.18);
            color: #F3F7FF;
        }
        .v2-head{
            display:flex;
            justify-content:space-between;
            align-items:flex-end;
            gap: 12px;
            margin-bottom: 12px;
        }
        .v2-title{
            font-size: 16px;
            font-weight: 950;
            letter-spacing: .25px;
            text-transform: uppercase;
            color: rgba(243,247,255,0.92);
        }
        .v2-sub{
            font-size: 12px;
            color: rgba(243,247,255,0.70);
            margin-top: 4px;
        }
        .v2-pill{
            font-size: 11px;
            font-weight: 950;
            padding: 7px 12px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.06);
            color: rgba(243,247,255,0.88);
            white-space:nowrap;
        }
        .v2-grid{
            display:grid;
            grid-template-columns: repeat(3, minmax(260px, 1fr));
            gap: 14px;
            width: 100%;
        }
        .v2-card{
            border-radius: 18px;
            padding: 14px 14px 12px 14px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
            min-height: 168px;
        }
        .v2-card h4{
            margin: 0 0 10px 0;
            font-size: 12px;
            font-weight: 950;
            letter-spacing: .25px;
            color: rgba(243,247,255,0.88);
            text-transform: uppercase;
        }
        .v2-row{
            display:flex;
            justify-content:space-between;
            align-items:flex-end;
            gap: 10px;
            margin: 8px 0;
        }
        .v2-kpi{
            font-size: 22px;
            font-weight: 950;
            color: rgba(243,247,255,0.95);
            line-height: 1;
        }
        .v2-label{
            font-size: 11px;
            color: rgba(243,247,255,0.72);
            margin-top: 4px;
        }
        .v2-chip{
            font-size: 11px;
            font-weight: 900;
            padding: 6px 10px;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(0,0,0,0.18);
            color: rgba(243,247,255,0.85);
            white-space:nowrap;
        }
        .v2-line{
            margin-top: 14px;
            display:grid;
            grid-template-columns: 1.2fr .8fr;
            gap: 14px;
            width: 100%;
        }
        .v2-box{
            border-radius: 18px;
            padding: 14px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
        }
        .v2-box h5{
            margin: 0 0 10px 0;
            font-size: 12px;
            font-weight: 950;
            letter-spacing: .25px;
            color: rgba(243,247,255,0.88);
            text-transform: uppercase;
        }
        .v2-ul{
            margin:0;
            padding-left: 16px;
            color: rgba(243,247,255,0.90);
        }
        .v2-ul li{
            margin: 8px 0;
            font-size: 12px;
        }
        .v2-ia{
            font-size: 12px;
            color: rgba(243,247,255,0.92);
            white-space: pre-wrap;
            line-height: 1.35;
        }
        .v2-btn-note{
            margin-top: 10px;
            font-size: 11px;
            color: rgba(243,247,255,0.70);
        }

        @media (max-width: 1100px){
            .v2-grid{ grid-template-columns: repeat(2, minmax(260px, 1fr)); }
            .v2-line{ grid-template-columns: 1fr; }
        }
        @media (max-width: 780px){
            .v2-grid{ grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ==============================
# Parser data_hora robusto
# ==============================
def _parse_datahora(df: pd.DataFrame, col: str = "data_hora") -> pd.DataFrame:
    if df is None or df.empty or col not in df.columns:
        return df
    dt = pd.to_datetime(df[col], errors="coerce")
    if getattr(dt.dt, "tz", None) is not None:
        df[col] = dt.dt.tz_convert(TZ)
        return df
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
    if "status" in row.index and _norm(row.get("status")) in ("não conforme", "nao conforme", "reprovado"):
        return True
    if "produto_reprovado" in row.index:
        pr = row.get("produto_reprovado")
        if _is_sim(pr):
            return True
        if _is_nao(pr):
            return False
    for col in ("reprovado", "aprovado"):
        if col in row.index:
            v = row.get(col)
            if col == "reprovado" and _is_sim(v):
                return True
            if col == "aprovado" and _is_nao(v):
                return True
    return False

def calcular_aprovacao(df_checks: pd.DataFrame, df_apont: pd.DataFrame) -> tuple[float, int, int]:
    if df_checks is None or df_checks.empty or df_apont is None or df_apont.empty:
        return 0.0, 0, 0
    if "numero_serie" not in df_apont.columns or "numero_serie" not in df_checks.columns:
        return 0.0, 0, 0

    series_validas = pd.Series(df_apont["numero_serie"].dropna().unique())
    dfc = df_checks[df_checks["numero_serie"].isin(series_validas)].copy()
    if dfc.empty:
        return 0.0, 0, 0

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

def is_workday(d: datetime.date) -> bool:
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
    mask_rep = dfr.apply(_is_reprovado_row, axis=1)
    dfr = dfr[mask_rep]
    if dfr.empty:
        return []
    s = dfr[fail_col].astype(str).str.strip()
    s = s[s.ne("") & s.ne("nan")]
    if s.empty:
        return []
    top = s.value_counts().head(3)
    return [(str(idx), int(val)) for idx, val in top.items()]

# ==============================
# RESUMOS (iguais ao que você já usa)
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
    meta_acum = 0
    for h, m in meta_hora.items():
        fim = datetime.datetime.combine(hoje, h) + datetime.timedelta(hours=1)
        fim = TZ.localize(fim) if fim.tzinfo is None else fim
        if hora_atual >= fim:
            meta_acum += int(m)

    atraso = int(max(meta_acum - total, 0))
    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)

    # oee
    performance_fraction = max(1 - (atraso / meta_acum), 0) if meta_acum > 0 else 1
    quality_fraction = (aprov / 100) if aprov > 0 else 0
    oee = float(performance_fraction * quality_fraction * 100)

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
    # meta acumulada "inicio_hora"
    meta_acum = 0
    hora_fechada = hora_atual.replace(minute=0, second=0, microsecond=0)
    for h, m in meta_hora.items():
        ini = datetime.datetime.combine(hoje, h)
        ini = TZ.localize(ini) if ini.tzinfo is None else ini
        if ini < hora_fechada:
            meta_acum += int(m)

    atraso = int(max(meta_acum - total, 0))
    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)

    performance_fraction = max(1 - (atraso / meta_acum), 0) if meta_acum > 0 else 1
    quality_fraction = (aprov / 100) if aprov > 0 else 0
    oee = float(performance_fraction * quality_fraction * 100)

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
    meta_acum = 0
    for h, m in meta_hora.items():
        fim = datetime.datetime.combine(hoje, h) + datetime.timedelta(hours=1)
        fim = TZ.localize(fim) if fim.tzinfo is None else fim
        if hora_atual >= fim:
            meta_acum += int(m)

    atraso = int(max(meta_acum - total, 0))
    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)

    performance_fraction = max(1 - (atraso / meta_acum), 0) if meta_acum > 0 else 1
    quality_fraction = (aprov / 100) if aprov > 0 else 0
    oee = float(performance_fraction * quality_fraction * 100)

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
# ✅ PÁGINA 1 (INTACTA) - HTML DOS 3 CARDS
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
          grid-template-columns: repeat(3, minmax(600px, 1fr));
          gap: 18px;
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

def page_onepage(data_inicio: datetime.date, data_fim: datetime.date):
    ph = st.empty()
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
# ✅ PÁGINA 2 (VISIONÁRIA) - RESUMO + PARETO + IA
# ==============================
def _chip_perf(p: float) -> str:
    if p >= 100:
        return "ACIMA DA META"
    if p >= 95:
        return "NA META"
    if p >= 85:
        return "ABAIXO"
    return "CRÍTICO"

def _chip_qual(q: float) -> str:
    if q >= 98:
        return "EXCELENTE"
    if q >= 95:
        return "OK"
    if q >= 90:
        return "ATENÇÃO"
    return "CRÍTICO"

def _fmt_top3(top3: list[tuple[str, int]]) -> str:
    if not top3:
        return "Sem reprovações no período (ou sem coluna de falha)."
    return " • ".join([f"{i+1}) {n} ({q})" for i, (n, q) in enumerate(top3)])

def page_resumo_ia():
    now = datetime.datetime.now(TZ)
    hoje = now.date()
    ini_mes = hoje.replace(day=1)

    # período do resumo (auto após 16h, ou manual)
    modo = st.sidebar.selectbox(
        "Resumo (Página 2)",
        ["Auto (>=16h = mês atual)", "Mês atual", "Usar filtro do One Page (Início/Fim)"],
        index=0
    )

    if modo in ("Auto (>=16h = mês atual)", "Mês atual"):
        data_ini = ini_mes
        data_fim = hoje
    else:
        data_ini = st.session_state.get("f_ini_val", hoje)
        data_fim = st.session_state.get("f_fim_val", hoje)

    # bases do período
    a_total = filtrar_periodo(carregar_apontamentos(), data_ini, data_fim)
    c_total = filtrar_periodo(carregar_checklists(), data_ini, data_fim)

    a_mola = filtrar_periodo(carregar_apontamentos_mola(), data_ini, data_fim)
    c_mola = filtrar_periodo(carregar_checklists_mola(), data_ini, data_fim)

    a_mp = filtrar_periodo(carregar_apontamentos_manga_pnm(), data_ini, data_fim)
    c_mp = filtrar_periodo(carregar_checklists_manga_pnm(), data_ini, data_fim)

    # metas diárias -> mensal (dias úteis)
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

    meta_total = meta_mes_total(meta_total_hora, data_ini, data_fim)
    meta_mola = meta_mes_total(meta_mola_hora, data_ini, data_fim)
    meta_mp = meta_mes_total(meta_mp_hora, data_ini, data_fim)

    prod_total = int(len(a_total))
    prod_mola = int(len(a_mola))
    prod_mp = int(len(a_mp))

    perf_total = (prod_total / meta_total * 100) if meta_total > 0 else 0.0
    perf_mola = (prod_mola / meta_mola * 100) if meta_mola > 0 else 0.0
    perf_mp = (prod_mp / meta_mp * 100) if meta_mp > 0 else 0.0

    q_total, insp_total, rep_total = calcular_aprovacao(c_total, a_total)
    q_mola, insp_mola, rep_mola = calcular_aprovacao(c_mola, a_mola)
    q_mp, insp_mp, rep_mp = calcular_aprovacao(c_mp, a_mp)

    top3_total = pareto_top3(c_total)
    top3_mola = pareto_top3(c_mola)
    top3_mp = pareto_top3(c_mp)

    # UI “visionária”
    st.markdown(
        f"""
        <div class="v2-wrap">
          <div class="v2-head">
            <div>
              <div class="v2-title">Resumo Inteligente • Performance & Qualidade</div>
              <div class="v2-sub">Período: <b>{data_ini}</b> até <b>{data_fim}</b> • Atualizado: <b>{now.strftime("%H:%M:%S")}</b></div>
            </div>
            <div class="v2-pill">ONE PAGE • MONTH MODE</div>
          </div>

          <div class="v2-grid">
            <div class="v2-card">
              <h4>Linha de Montagem / Esteira (Total)</h4>

              <div class="v2-row">
                <div>
                  <div class="v2-kpi">{perf_total:.1f}%</div>
                  <div class="v2-label">Performance (Produzido / Meta)</div>
                </div>
                <div class="v2-chip">{_chip_perf(perf_total)}</div>
              </div>

              <div class="v2-row">
                <div>
                  <div class="v2-kpi">{q_total:.1f}%</div>
                  <div class="v2-label">Qualidade • Inspec.: {insp_total} • Reprov.: {rep_total}</div>
                </div>
                <div class="v2-chip">{_chip_qual(q_total)}</div>
              </div>

              <div class="v2-label">Produzido: <b>{prod_total}</b> • Meta: <b>{meta_total}</b></div>
            </div>

            <div class="v2-card">
              <h4>Montagem Mola</h4>

              <div class="v2-row">
                <div>
                  <div class="v2-kpi">{perf_mola:.1f}%</div>
                  <div class="v2-label">Performance (Produzido / Meta)</div>
                </div>
                <div class="v2-chip">{_chip_perf(perf_mola)}</div>
              </div>

              <div class="v2-row">
                <div>
                  <div class="v2-kpi">{q_mola:.1f}%</div>
                  <div class="v2-label">Qualidade • Inspec.: {insp_mola} • Reprov.: {rep_mola}</div>
                </div>
                <div class="v2-chip">{_chip_qual(q_mola)}</div>
              </div>

              <div class="v2-label">Produzido: <b>{prod_mola}</b> • Meta: <b>{meta_mola}</b></div>
            </div>

            <div class="v2-card">
              <h4>Montagem Manga & PNM</h4>

              <div class="v2-row">
                <div>
                  <div class="v2-kpi">{perf_mp:.1f}%</div>
                  <div class="v2-label">Performance (Produzido / Meta)</div>
                </div>
                <div class="v2-chip">{_chip_perf(perf_mp)}</div>
              </div>

              <div class="v2-row">
                <div>
                  <div class="v2-kpi">{q_mp:.1f}%</div>
                  <div class="v2-label">Qualidade • Inspec.: {insp_mp} • Reprov.: {rep_mp}</div>
                </div>
                <div class="v2-chip">{_chip_qual(q_mp)}</div>
              </div>

              <div class="v2-label">Produzido: <b>{prod_mp}</b> • Meta: <b>{meta_mp}</b></div>
            </div>
          </div>

          <div class="v2-line">
            <div class="v2-box">
              <h5>Pareto • Top 3 falhas (somente reprovações)</h5>
              <ul class="v2-ul">
                <li><b>Total/Esteira:</b> {_fmt_top3(top3_total)}</li>
                <li><b>Mola:</b> {_fmt_top3(top3_mola)}</li>
                <li><b>Manga & PNM:</b> {_fmt_top3(top3_mp)}</li>
              </ul>
              <div class="v2-btn-note">Se o Pareto ficar vazio e você sabe que reprovou, me mande o nome das colunas do checklist (pra eu mapear 100%).</div>
            </div>

            <div class="v2-box">
              <h5>Insights (IA)</h5>
              <div class="v2-btn-note">Clique para gerar um resumo acionável (curto) para reunião.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Botão de IA + saída (fora do HTML pra funcionar sem gambiarra)
    st.write("")
    cols = st.columns([1, 2])
    with cols[0]:
        gerar = st.button("Gerar Insights (IA)", use_container_width=True)
    with cols[1]:
        st.caption("Precisa de OPENAI_API_KEY no teste.env e pacote openai no requirements.txt.")

    if "insight_ia_mes" not in st.session_state:
        st.session_state["insight_ia_mes"] = ""

    if gerar:
        if not OPENAI_AVAILABLE:
            st.error("Pacote 'openai' não instalado. Adicione em requirements.txt: openai")
        elif not openai_client:
            st.error("OPENAI_API_KEY não configurada no teste.env (ou inválida).")
        else:
            payload = {
                "periodo": f"{data_ini} até {data_fim}",
                "total": {"performance_pct": perf_total, "qualidade_pct": q_total, "produzido": prod_total, "meta": meta_total,
                          "inspecionado": insp_total, "reprovados": rep_total, "pareto_top3": top3_total},
                "mola": {"performance_pct": perf_mola, "qualidade_pct": q_mola, "produzido": prod_mola, "meta": meta_mola,
                         "inspecionado": insp_mola, "reprovados": rep_mola, "pareto_top3": top3_mola},
                "manga_pnm": {"performance_pct": perf_mp, "qualidade_pct": q_mp, "produzido": prod_mp, "meta": meta_mp,
                              "inspecionado": insp_mp, "reprovados": rep_mp, "pareto_top3": top3_mp},
            }

            prompt = f"""
Você é um analista de produção/qualidade.
Faça um resumo visionário mas objetivo (máx 12 linhas), em pt-br.

Regras:
- Performance = Produzido vs Meta (mês)
- Qualidade = Aprovação + Reprovados
- Use o Pareto Top3 como foco
- Entregue: (1) Diagnóstico curto (2) 3 ações práticas (3) 3 perguntas para a reunião

Dados:
{payload}
""".strip()

            with st.spinner("Gerando insights..."):
                resp = openai_client.responses.create(model=OPENAI_MODEL, input=prompt)

            txt = getattr(resp, "output_text", "") or ""
            st.session_state["insight_ia_mes"] = txt.strip()

    if st.session_state.get("insight_ia_mes"):
        st.markdown("### Resultado IA")
        st.text_area("", value=st.session_state["insight_ia_mes"], height=240)

# ==============================
# MAIN
# ==============================
def main():
    aplicar_css_app()

    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key="autorefresh_onepage_linhas")

    now = datetime.datetime.now(TZ)
    hoje = now.date()

    # Sidebar sempre disponível
    st.sidebar.markdown("## Menu")
    pagina = st.sidebar.radio("Página", ["One Page (TV)", "Resumo Mensal + IA"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtro (Data) — One Page")
    data_inicio = st.sidebar.date_input("Início", hoje, key="f_ini")
    data_fim = st.sidebar.date_input("Fim", hoje, key="f_fim")

    # guarda pra página 2 poder usar se quiser
    st.session_state["f_ini_val"] = data_inicio
    st.session_state["f_fim_val"] = data_fim

    if st.sidebar.button("Atualizar agora"):
        st.cache_data.clear()

    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>", unsafe_allow_html=True)

    if pagina == "One Page (TV)":
        st.markdown(
            f"<div class='op-sub'>Período: <b>{data_inicio}</b> até <b>{data_fim}</b></div>",
            unsafe_allow_html=True
        )
        # ✅ página 1 intacta
        page_onepage(data_inicio, data_fim)

    else:
        st.markdown(
            f"<div class='op-sub'>Modo: <b>Resumo Mensal + IA</b></div>",
            unsafe_allow_html=True
        )
        # ✅ página 2 visionária
        page_resumo_ia()

    st.markdown(
        f"<p style='color:rgba(11,27,51,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{now.strftime('%H:%M:%S')}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
