import os
import datetime
from pathlib import Path
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from supabase import create_client
import textwrap
import google.generativeai as genai
import json
import calendar
import holidays
from streamlit_mic_recorder import speech_to_text

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

# tenta carregar .env local (para rodar no seu PC)
env_path = Path(__file__).parent / "teste.env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# ==============================
# ENV / SUPABASE / GEMINI
# ==============================
env_path = Path(__file__).parent / "teste.env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL / SUPABASE_KEY não encontrados (env ou secrets).")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TZ = pytz.timezone("America/Sao_Paulo")

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")).strip()
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")).strip()

GEMINI_AVAILABLE = bool(GEMINI_API_KEY)
if GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)

# ==============================
# CSS APP + GARANTE SIDEBAR EM TODAS AS PÁGINAS
# ==============================
def aplicar_css_app():
    st.markdown(
        """
        <style>
        /* =========================
           ✅ TV FIX: usar tela toda
           ========================= */
        html, body, [data-testid="stAppViewContainer"]{
            width: 100%;
            max-width: 100%;
        }
        section.main > div{
            max-width: 100% !important;
        }
        .block-container{
            max-width: 100% !important;
            padding-left: 0.10rem !important;
            padding-right: 0.10rem !important;
            padding-top: 0.8rem;
            padding-bottom: 0.8rem;
        }

        /* ✅ NÃO esconder o toolbar inteiro */
        div[data-testid="stToolbar"]{
            visibility: visible !important;
            height: auto !important;
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            z-index: 999990 !important;
            background: transparent !important;
        }

        /* esconder apenas ações do toolbar */
        div[data-testid="stToolbar"] [data-testid="stToolbarActions"],
        div[data-testid="stToolbar"] [data-testid="stToolbarActionItems"]{
            opacity: 0 !important;
            pointer-events: none !important;
        }

        /* Header */
        header[data-testid="stHeader"]{
            background: transparent !important;
            border: none !important;
            visibility: visible !important;
            height: auto !important;
            z-index: 999980 !important;
        }

        /* botão sidebar */
        button[data-testid="stSidebarCollapseButton"],
        button[data-testid="baseButton-headerNoPadding"],
        button[aria-label="Open sidebar"],
        button[aria-label="Close sidebar"],
        button[title="Open sidebar"],
        button[title="Close sidebar"]{
            position: fixed !important;
            top: 10px !important;
            left: 10px !important;
            z-index: 2147483647 !important;
            opacity: 1 !important;
            display: flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
            transform: scale(1.15) !important;

            background: rgba(11,27,51,0.10) !important;
            border: 1px solid rgba(11,27,51,0.18) !important;
            border-radius: 10px !important;
            box-shadow: 0 6px 18px rgba(0,0,0,0.10) !important;
            backdrop-filter: blur(6px) !important;
        }

        header[data-testid="stHeader"] *{
            pointer-events: auto;
        }

        div[data-testid="stStatusWidget"] {display:none !important;}
        div[data-testid="stDecoration"] {display:none !important;}

        /* fundo app */
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

        /* =========================
           SIDEBAR (COR AJUSTADA)
           ========================= */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #071124 0%, #0B1B33 60%, #0A2747 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
        }

        /* ==============================
           PÁGINA 2 (VISIONÁRIA)
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
            padding: 14px;
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

# ✅ CORRIGIDO: filtra por data_hora OU created_at/timestamp quando não existir data_hora
def filtrar_periodo(df: pd.DataFrame, data_inicio: datetime.date, data_fim: datetime.date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    # tenta colunas comuns de data (checklists às vezes não tem data_hora)
    for col in ("data_hora", "created_at", "createdAt", "timestamp", "data", "dt"):
        if col in df.columns:
            dff = df.copy()
            dff[col] = pd.to_datetime(dff[col], errors="coerce")

            # timezone-aware -> converte; naive -> localiza no TZ local
            if getattr(dff[col].dt, "tz", None) is not None:
                dff[col] = dff[col].dt.tz_convert(TZ)
            else:
                dff[col] = dff[col].dt.tz_localize(TZ)

            dff = dff[dff[col].notna()]
            return dff[(dff[col].dt.date >= data_inicio) & (dff[col].dt.date <= data_fim)]

    # sem coluna de data: devolve tudo (melhor do que zerar)
    return df.copy()

def _norm(x) -> str:
    return str(x).strip().lower()

def _is_sim(x) -> bool:
    v = _norm(x)
    return v in ("sim", "s", "1", "true", "verdadeiro", "yes", "y", "ok")

def _is_nao(x) -> bool:
    v = _norm(x)
    return v in ("não", "nao", "n", "0", "false", "falso", "no", "nok")

# ✅ CORRIGIDO: detecta reprovação em mais colunas comuns
def _is_reprovado_row(row: pd.Series) -> bool:
    # 1) status explícito
    if "status" in row.index:
        stt = _norm(row.get("status"))
        if stt in ("não conforme", "nao conforme", "reprovado", "nc", "nok", "falha", "fail"):
            return True

    # 2) produto_reprovado: "Sim" = reprovado / "Não" = ok
    if "produto_reprovado" in row.index:
        pr = row.get("produto_reprovado")
        if _is_sim(pr):   # aqui "sim" significa "reprovado"
            return True
        if _is_nao(pr):
            return False

    # 3) chaves comuns de resultado/conformidade/aprovação
    for col in (
        "resultado", "resultado_final", "conformidade", "conforme",
        "aprovado", "aprovacao", "aprovacao_final", "reprovado",
        "nao_conforme", "não_conforme", "nc", "ok_nok", "oknok", "resultado_ok"
    ):
        if col in row.index:
            v = _norm(row.get(col))
            if v in ("não conforme", "nao conforme", "reprovado", "nc", "nok", "falha", "fail", "0", "false"):
                return True
            if v in ("conforme", "aprovado", "ok", "1", "true"):
                return False

    # 4) fallback: se alguma coluna “item/criterio/teste” estiver marcada como NOK/NC etc.
    for c in row.index:
        cl = str(c).strip().lower()
        if any(k in cl for k in ("item", "check", "criterio", "critério", "etapa", "teste")):
            v = _norm(row.get(c))
            if v in ("não conforme", "nao conforme", "reprovado", "nc", "nok", "falha", "fail"):
                return True

    return False

# ✅ CORRIGIDO: último registro por série (por data) + fallback “qualquer falha na série”
def calcular_aprovacao(df_checks: pd.DataFrame, df_apont: pd.DataFrame) -> tuple[float, int, int]:
    if df_checks is None or df_checks.empty or df_apont is None or df_apont.empty:
        return 0.0, 0, 0

    if "numero_serie" not in df_apont.columns:
        return 0.0, 0, 0

    # checklist pode usar outro nome de série
    serie_col = None
    for cand in ("numero_serie", "nr_serie", "serie", "serial", "serial_number"):
        if cand in df_checks.columns:
            serie_col = cand
            break
    if not serie_col:
        return 0.0, 0, 0

    series_validas = pd.Series(df_apont["numero_serie"].dropna().unique())
    dfc = df_checks[df_checks[serie_col].isin(series_validas)].copy()
    if dfc.empty:
        return 0.0, 0, 0

    # coluna de data do checklist (se existir)
    date_col = None
    for cand in ("data_hora", "created_at", "createdAt", "timestamp", "data", "dt"):
        if cand in dfc.columns:
            date_col = cand
            break

    if date_col:
        dfc[date_col] = pd.to_datetime(dfc[date_col], errors="coerce")
        dfc = dfc[dfc[date_col].notna()].copy()

        # timezone
        if getattr(dfc[date_col].dt, "tz", None) is not None:
            dfc[date_col] = dfc[date_col].dt.tz_convert(TZ)
        else:
            dfc[date_col] = dfc[date_col].dt.tz_localize(TZ)

        dfc = dfc.sort_values([serie_col, date_col])
        ult = dfc.groupby(serie_col, as_index=False).tail(1)
    else:
        ult = dfc.groupby(serie_col, as_index=False).tail(1)

    total_inspecionado = int(ult[serie_col].nunique())
    if total_inspecionado == 0:
        return 0.0, 0, 0

    # reprovação pelo último registro da série
    reprovados_ult = int(ult.apply(_is_reprovado_row, axis=1).sum())

    # fallback: se QUALQUER registro da série tiver reprovação, conta reprovação
    falha_por_serie = dfc.assign(__rep=dfc.apply(_is_reprovado_row, axis=1)) \
                         .groupby(serie_col)["__rep"].any()
    reprovados_any = int(falha_por_serie.sum())

    reprovados = max(reprovados_ult, reprovados_any)

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
# RESUMOS
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
        datetime.time(15, 0): 2,
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
# ✅ TV: FORÇA 3 colunas usando AUTO-SCALE
# ==============================
def render_onepage_html(resumos: list[dict]) -> tuple[str, int]:
    # altura do iframe (um pouco maior pra acomodar o scale)
    HEIGHT = 520

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

    # ✅ AUTO-SCALE:
    BASE_W = 1000  # largura base de design pros 3 cards
    BASE_H = 300   # (não usado aqui, mas mantive igual ao seu)

    html = f"""
    <div id="wrap" style="width:100%; max-width:100%; overflow:hidden;">
      <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>

      <style>
        :root {{
          --scale: 1;
        }}

        /* Conteúdo em tamanho base; TV reduz com scale */
        #stage {{
          width: {BASE_W}px;
          transform: scale(var(--scale));
          transform-origin: top left;
        }}

        .grid-3 {{
          display: grid;
          grid-template-columns: repeat(3, 1fr); /* ✅ sempre 3 */
          gap: 26px;
          width: {BASE_W}px;
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
          min-width: 0;
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
          min-width: 0;
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

        /* ✅ ATUALIZADO: mini-foot em até 2 linhas (sem cortar) */
        .mini-foot {{
          font-size: 11px;
          color: rgba(255,255,255,0.72);
          margin-top: 6px;

          white-space: normal;
          overflow: hidden;

          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;

          word-break: break-word;
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
      </style>

      <div id="stage">
        <div class="grid-3">
          {''.join(cards_html)}
        </div>
      </div>

      <script>
        const dados = {js_data};

        function calcScale() {{
          const vw = (window.innerWidth || document.documentElement.clientWidth || {BASE_W}) - 20;
          const s = Math.min(1, vw / {BASE_W});
          document.documentElement.style.setProperty("--scale", s.toFixed(4));
        }}

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

        // escala primeiro
        calcScale();
        window.addEventListener("resize", () => {{
          calcScale();
        }});

        // gauges
        dados.forEach(d => renderGauge("g_" + d.key, d.oee));
      </script>
    </div>
    """
    return html, HEIGHT

def page_onepage(data_inicio: datetime.date, data_fim: datetime.date):
    ph = st.empty()
    if "last_html_onepage" in st.session_state and "last_height_onepage" in st.session_state:
        with ph.container():
            components.html(
                st.session_state["last_html_onepage"],
                height=st.session_state["last_height_onepage"],
                scrolling=False
            )

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

def _status_class(perf: float, qual: float) -> tuple[str, str]:
    score = (perf * 0.55) + (qual * 0.45)
    if score >= 98:
        return "FORTE", "p2-ok"
    if score >= 90:
        return "ATENÇÃO", "p2-warn"
    return "CRÍTICO", "p2-critical"

def _guess_fail_col(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None

    cols_map = {str(c).strip().lower(): c for c in df.columns}

    prioridade_alta = [
        "item",
        "falha",
        "defeito",
        "motivo_falha",
        "motivo",
        "causa",
        "descricao_falha",
        "descrição_falha",
        "nao_conformidade",
        "não_conformidade",
        "problema"
    ]

    for cand in prioridade_alta:
        if cand in cols_map:
            return cols_map[cand]

    prioridade_baixa = [
        "observacao",
        "observação",
        "comentario",
        "comentário",
        "descricao",
        "descrição"
    ]

    for cand in prioridade_baixa:
        if cand in cols_map:
            return cols_map[cand]

    return None

def pareto_top3(df_checks: pd.DataFrame) -> list[tuple[str, int]]:
    if df_checks is None or df_checks.empty:
        return []

    fail_col = _guess_fail_col(df_checks)
    if not fail_col or fail_col not in df_checks.columns:
        return []

    dfr = df_checks.copy()

    mask_rep = dfr.apply(_is_reprovado_row, axis=1)
    dfr = dfr[mask_rep].copy()
    if dfr.empty:
        return []

    s = dfr[fail_col].astype(str).str.strip()
    s = (
        s.str.replace(r"\s+", " ", regex=True)
         .str.replace("_", " ", regex=False)
         .str.strip()
    )

    invalidos = {"", "nan", "none", "null", "-", "--", "n/a"}
    s = s[~s.str.lower().isin(invalidos)]

    if s.empty:
        return []

    top = s.value_counts(dropna=True).head(3)
    return [(str(idx), int(val)) for idx, val in top.items()]

def pareto_top3_mola(df_checks: pd.DataFrame) -> list[tuple[str, int]]:
    if df_checks is None or df_checks.empty:
        return []

    if "item" not in df_checks.columns:
        return pareto_top3(df_checks)

    dfr = df_checks.copy()
    mask_rep = dfr.apply(_is_reprovado_row, axis=1)
    dfr = dfr[mask_rep].copy()
    if dfr.empty:
        return []

    s = dfr["item"].astype(str).str.strip()
    s = (
        s.str.replace(r"\s+", " ", regex=True)
         .str.replace("_", " ", regex=False)
         .str.strip()
    )

    invalidos = {"", "nan", "none", "null", "-", "--", "n/a"}
    s = s[~s.str.lower().isin(invalidos)]

    if s.empty:
        return []

    top = s.value_counts(dropna=True).head(3)
    return [(str(idx), int(val)) for idx, val in top.items()]

def dias_uteis_mes_brasil(ano: int, mes: int) -> dict:
    feriados_br = holidays.Brazil(years=ano)
    ultimo_dia = calendar.monthrange(ano, mes)[1]

    total = 0
    passados = 0
    restantes = 0

    hoje = datetime.datetime.now(TZ).date()

    for dia in range(1, ultimo_dia + 1):
        dt = datetime.date(ano, mes, dia)
        eh_util = dt.weekday() < 5 and dt not in feriados_br
        if eh_util:
            total += 1
            if dt <= hoje:
                passados += 1
            else:
                restantes += 1

    return {
        "total": total,
        "passados": passados,
        "restantes": restantes,
    }

def montar_payload_operacional(data_ini: datetime.date, data_fim: datetime.date) -> dict:
    a_total = filtrar_periodo(carregar_apontamentos(), data_ini, data_fim)
    c_total = filtrar_periodo(carregar_checklists(), data_ini, data_fim)

    a_mola = filtrar_periodo(carregar_apontamentos_mola(), data_ini, data_fim)
    c_mola = filtrar_periodo(carregar_checklists_mola(), data_ini, data_fim)

    a_mp = filtrar_periodo(carregar_apontamentos_manga_pnm(), data_ini, data_fim)
    c_mp = filtrar_periodo(carregar_checklists_manga_pnm(), data_ini, data_fim)

    meta_total_hora = {
        datetime.time(6, 0): 26, datetime.time(7, 0): 26, datetime.time(8, 0): 26,
        datetime.time(9, 0): 26, datetime.time(10, 0): 26, datetime.time(11, 0): 6,
        datetime.time(12, 0): 26, datetime.time(13, 0): 26, datetime.time(14, 0): 26,
        datetime.time(15, 0): 12
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
    top3_mola = pareto_top3_mola(c_mola)
    top3_mp = pareto_top3(c_mp)

    agora = datetime.datetime.now(TZ)
    dias_uteis = dias_uteis_mes_brasil(agora.year, agora.month)

    return {
        "data_contexto": {
            "agora_iso": agora.isoformat(),
            "data_hoje": str(agora.date()),
            "hora_atual": agora.strftime("%H:%M:%S"),
            "mes_atual": agora.strftime("%m/%Y"),
            "dias_uteis_brasil_mes_atual": dias_uteis,
            "timezone": "America/Sao_Paulo",
        },
        "periodo_operacional": {
            "inicio": str(data_ini),
            "fim": str(data_fim),
        },
        "total": {
            "performance_pct": round(perf_total, 2),
            "qualidade_pct": round(q_total, 2),
            "produzido": prod_total,
            "meta": meta_total,
            "inspecionado": insp_total,
            "reprovados": rep_total,
            "pareto_top3": top3_total
        },
        "mola": {
            "performance_pct": round(perf_mola, 2),
            "qualidade_pct": round(q_mola, 2),
            "produzido": prod_mola,
            "meta": meta_mola,
            "inspecionado": insp_mola,
            "reprovados": rep_mola,
            "pareto_top3": top3_mola
        },
        "manga_pnm": {
            "performance_pct": round(perf_mp, 2),
            "qualidade_pct": round(q_mp, 2),
            "produzido": prod_mp,
            "meta": meta_mp,
            "inspecionado": insp_mp,
            "reprovados": rep_mp,
            "pareto_top3": top3_mp
        },
    }

def _build_page2_html(data_ini, data_fim, now, cards, paretos):
    def card_html(c):
        return f"""
        <div class="p2-card">
            <div class="p2-card-top">
                <div>
                    <div class="p2-card-title">{c['nome']}</div>
                    <div class="p2-card-sub">Produzido: <b>{c['produzido']}</b> • Meta: <b>{c['meta']}</b></div>
                </div>
                <div class="p2-badge {c['status_class']}">{c['status_txt']}</div>
            </div>

            <div class="p2-kpi-grid">
                <div class="p2-kpi-box">
                    <div class="p2-kpi-label">Performance</div>
                    <div class="p2-kpi-value">{c['performance']:.1f}%</div>
                    <div class="p2-kpi-foot">Produzido / Meta</div>
                </div>

                <div class="p2-kpi-box">
                    <div class="p2-kpi-label">Qualidade</div>
                    <div class="p2-kpi-value">{c['qualidade']:.1f}%</div>
                    <div class="p2-kpi-foot">Inspec.: {c['inspecionado']} • Reprov.: {c['reprovados']}</div>
                </div>
            </div>

            <div class="p2-progress-wrap">
                <div class="p2-progress-head">
                    <span>Performance</span>
                    <span>{c['performance']:.1f}%</span>
                </div>
                <div class="p2-progress">
                    <div style="width:min({c['performance']:.1f}%,100%)"></div>
                </div>
            </div>

            <div class="p2-progress-wrap">
                <div class="p2-progress-head">
                    <span>Qualidade</span>
                    <span>{c['qualidade']:.1f}%</span>
                </div>
                <div class="p2-progress quality">
                    <div style="width:min({c['qualidade']:.1f}%,100%)"></div>
                </div>
            </div>
        </div>
        """

    def pareto_html(label, itens):
        if not itens:
            lis = "<li>Sem reprovações no período ou sem coluna de falha mapeada.</li>"
        else:
            lis = "".join(
                [f"<li><span>{i+1}. {nome}</span><b>{qtd}</b></li>" for i, (nome, qtd) in enumerate(itens)]
            )

        return f"""
        <div class="p2-pareto-card">
            <div class="p2-pareto-title">{label}</div>
            <ul>{lis}</ul>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <style>
            * {{
                box-sizing: border-box;
                font-family: Inter, Segoe UI, Arial, sans-serif;
            }}

            body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color: #EAF2FF;
            }}

            .p2-wrap {{
                width: 100%;
                border-radius: 26px;
                padding: 18px;
                background:
                    radial-gradient(circle at top left, rgba(0, 153, 255, 0.20), transparent 28%),
                    radial-gradient(circle at top right, rgba(0, 255, 200, 0.12), transparent 30%),
                    linear-gradient(135deg, #041224 0%, #071C38 55%, #0A2747 100%);
                border: 1px solid rgba(255,255,255,0.10);
                box-shadow: 0 18px 40px rgba(0,0,0,0.24);
            }}

            .p2-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                margin-bottom: 18px;
                flex-wrap: wrap;
            }}

            .p2-title {{
                font-size: 20px;
                font-weight: 900;
                letter-spacing: .4px;
                text-transform: uppercase;
            }}

            .p2-sub {{
                font-size: 12px;
                color: rgba(234,242,255,0.72);
                margin-top: 4px;
            }}

            .p2-pill {{
                padding: 8px 14px;
                border-radius: 999px;
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.12);
                font-size: 11px;
                font-weight: 900;
                color: #DDEBFF;
            }}

            .p2-cards {{
                display: grid;
                grid-template-columns: repeat(3, minmax(260px, 1fr));
                gap: 14px;
                margin-bottom: 16px;
            }}

            .p2-card {{
                border-radius: 20px;
                padding: 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
                min-height: 250px;
            }}

            .p2-card-top {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 8px;
                margin-bottom: 14px;
            }}

            .p2-card-title {{
                font-size: 13px;
                font-weight: 900;
                text-transform: uppercase;
                color: #F5F9FF;
            }}

            .p2-card-sub {{
                font-size: 11px;
                margin-top: 5px;
                color: rgba(234,242,255,0.72);
            }}

            .p2-badge {{
                padding: 7px 10px;
                border-radius: 999px;
                font-size: 10px;
                font-weight: 900;
                white-space: nowrap;
                border: 1px solid transparent;
            }}

            .p2-ok {{
                background: rgba(0, 210, 140, 0.14);
                color: #8BFFD1;
                border-color: rgba(0, 210, 140, 0.24);
            }}

            .p2-warn {{
                background: rgba(255, 196, 0, 0.14);
                color: #FFE48A;
                border-color: rgba(255, 196, 0, 0.22);
            }}

            .p2-critical {{
                background: rgba(255, 82, 82, 0.14);
                color: #FFB0B0;
                border-color: rgba(255, 82, 82, 0.22);
            }}

            .p2-kpi-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-bottom: 14px;
            }}

            .p2-kpi-box {{
                border-radius: 16px;
                padding: 12px;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
            }}

            .p2-kpi-label {{
                font-size: 11px;
                text-transform: uppercase;
                color: rgba(234,242,255,0.74);
                font-weight: 800;
                margin-bottom: 8px;
            }}

            .p2-kpi-value {{
                font-size: 28px;
                font-weight: 950;
                line-height: 1;
                color: #FFFFFF;
            }}

            .p2-kpi-foot {{
                margin-top: 7px;
                font-size: 11px;
                color: rgba(234,242,255,0.70);
            }}

            .p2-progress-wrap {{
                margin-top: 10px;
            }}

            .p2-progress-head {{
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: rgba(234,242,255,0.84);
                margin-bottom: 6px;
            }}

            .p2-progress {{
                height: 10px;
                border-radius: 999px;
                overflow: hidden;
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.08);
            }}

            .p2-progress > div {{
                height: 100%;
                border-radius: 999px;
                background: linear-gradient(90deg, #00C2FF 0%, #3D8BFF 100%);
            }}

            .p2-progress.quality > div {{
                background: linear-gradient(90deg, #00E5A8 0%, #00B894 100%);
            }}

            .p2-bottom {{
                display: grid;
                grid-template-columns: 1.2fr .8fr;
                gap: 14px;
            }}

            .p2-panel {{
                border-radius: 20px;
                padding: 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
            }}

            .p2-panel-title {{
                font-size: 13px;
                font-weight: 900;
                text-transform: uppercase;
                margin-bottom: 12px;
                color: #F5F9FF;
            }}

            .p2-pareto-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 12px;
            }}

            .p2-pareto-card {{
                border-radius: 16px;
                padding: 12px;
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.08);
            }}

            .p2-pareto-title {{
                font-size: 11px;
                font-weight: 900;
                text-transform: uppercase;
                color: #DCEBFF;
                margin-bottom: 10px;
            }}

            .p2-pareto-card ul {{
                padding-left: 18px;
                margin: 0;
            }}

            .p2-pareto-card li {{
                margin: 7px 0;
                font-size: 12px;
                color: rgba(234,242,255,0.90);
                display: flex;
                justify-content: space-between;
                gap: 10px;
            }}

            .p2-side-note {{
                font-size: 12px;
                line-height: 1.5;
                color: rgba(234,242,255,0.84);
            }}

            .p2-side-note b {{
                color: #FFFFFF;
            }}

            @media (max-width: 1100px) {{
                .p2-cards {{
                    grid-template-columns: 1fr;
                }}

                .p2-bottom {{
                    grid-template-columns: 1fr;
                }}

                .p2-pareto-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="p2-wrap">
            <div class="p2-header">
                <div>
                    <div class="p2-title">Resumo Inteligente • Performance & Qualidade</div>
                    <div class="p2-sub">Período: <b>{data_ini}</b> até <b>{data_fim}</b> • Atualizado às <b>{now.strftime("%H:%M:%S")}</b></div>
                </div>
                <div class="p2-pill">ONE PAGE • IA OPERACIONAL</div>
            </div>

            <div class="p2-cards">
                {''.join(card_html(c) for c in cards)}
            </div>

            <div class="p2-bottom">
                <div class="p2-panel">
                    <div class="p2-panel-title">Pareto • Top 3 falhas</div>
                    <div class="p2-pareto-grid">
                        {pareto_html("Total / Esteira", paretos["total"])}
                        {pareto_html("Montagem Mola", paretos["mola"])}
                        {pareto_html("Manga & PNM", paretos["manga_pnm"])}
                    </div>
                </div>

                <div class="p2-panel">
                    <div class="p2-panel-title">Leitura executiva</div>
                    <div class="p2-side-note">
                        <b>Como usar:</b><br>
                        Gere insights automáticos e depois converse com a IA logo abaixo.<br><br>
                        Você pode perguntar, por exemplo:<br>
                        • qual linha está pior e por quê?<br>
                        • quais ações atacar hoje?<br>
                        • monte uma fala de 1 minuto para reunião<br>
                        • compare performance x qualidade
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def _gemini_generate_text(prompt: str) -> str:
    if not GEMINI_AVAILABLE:
        return "GEMINI_API_KEY não configurada."

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        txt = getattr(resp, "text", "") or ""
        return txt.strip() if txt else "Não consegui gerar resposta desta vez."
    except Exception as e:
        return f"Erro ao consultar Gemini: {e}"

def limpar_texto_para_fala(texto: str) -> str:
    if not texto:
        return ""

    txt = str(texto)

    txt = re.sub(r"\*\*(.*?)\*\*", r"\1", txt)
    txt = re.sub(r"\*(.*?)\*", r"\1", txt)
    txt = re.sub(r"__(.*?)__", r"\1", txt)
    txt = re.sub(r"_(.*?)_", r"\1", txt)
    txt = re.sub(r"`(.*?)`", r"\1", txt)

    txt = re.sub(r"^\s*#{1,6}\s*", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"^\s*[-•]\s*", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"^\s*\d+\.\s*", "", txt, flags=re.MULTILINE)

    txt = txt.replace("%", " por cento")
    txt = txt.replace("&", " e ")
    txt = txt.replace("/", " barra ")

    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def falar_no_navegador(texto: str):
    texto_limpo = limpar_texto_para_fala(texto)
    texto_js = json.dumps(texto_limpo)

    html_js = f"""
    <script>
      const texto = {texto_js};

      function falar() {{
        const synth = window.speechSynthesis;
        if (!synth || !texto) return;

        synth.cancel();

        const u = new SpeechSynthesisUtterance(texto);
        u.lang = "pt-BR";
        u.rate = 1.03;
        u.pitch = 1.0;
        u.volume = 1.0;

        const voices = synth.getVoices() || [];

        const preferidas = [
          "Microsoft Francisca",
          "Microsoft Antonio",
          "Francisca",
          "Antonio",
          "Google português do Brasil",
          "Google português",
          "Luciana",
          "Felipe"
        ];

        let vozEscolhida = null;

        for (const nome of preferidas) {{
          vozEscolhida = voices.find(v =>
            (v.name || "").toLowerCase().includes(nome.toLowerCase())
          );
          if (vozEscolhida) break;
        }}

        if (!vozEscolhida) {{
          vozEscolhida = voices.find(v =>
            (v.lang || "").toLowerCase().startsWith("pt-br")
          );
        }}

        if (!vozEscolhida) {{
          vozEscolhida = voices.find(v =>
            (v.lang || "").toLowerCase().startsWith("pt")
          );
        }}

        if (vozEscolhida) {{
          u.voice = vozEscolhida;
        }}

        synth.speak(u);
      }}

      if (speechSynthesis.getVoices().length === 0) {{
        speechSynthesis.onvoiceschanged = falar;
      }} else {{
        falar();
      }}
    </script>
    """
    components.html(html_js, height=0)

def render_jarvis_avatar_html():
    html_avatar = """
    <div style="width:100%;display:flex;justify-content:center;align-items:center;margin:8px 0 16px 0;">
      <div style="width:100%;max-width:980px;border-radius:28px;padding:22px;background:
        radial-gradient(circle at 50% 35%, rgba(0,255,255,0.12), transparent 22%),
        radial-gradient(circle at 20% 20%, rgba(0,140,255,0.18), transparent 28%),
        linear-gradient(135deg,#041224 0%,#071C38 55%,#0A2747 100%);
        border:1px solid rgba(255,255,255,0.08);
        box-shadow:0 18px 40px rgba(0,0,0,0.24);">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
          <div>
            <div style="font-size:26px;font-weight:900;color:#F4F9FF;letter-spacing:.8px;">JARVIS INDUSTRIAL</div>
            <div style="font-size:13px;color:rgba(234,242,255,0.78);margin-top:4px;">
              Voz, contexto operacional e perguntas gerais de apoio executivo
            </div>
          </div>
          <div style="padding:8px 14px;border-radius:999px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);font-size:11px;font-weight:900;color:#DDEBFF;">
            VOICE READY
          </div>
        </div>

        <div style="display:flex;justify-content:center;align-items:center;margin-top:24px;">
          <div class="jarvis-orb-wrap">
            <div class="jarvis-ring ring1"></div>
            <div class="jarvis-ring ring2"></div>
            <div class="jarvis-ring ring3"></div>
            <div class="jarvis-core"></div>
          </div>
        </div>

        <div style="display:flex;justify-content:center;gap:8px;margin-top:18px;">
          <div class="jarvis-bar"></div>
          <div class="jarvis-bar"></div>
          <div class="jarvis-bar"></div>
          <div class="jarvis-bar"></div>
          <div class="jarvis-bar"></div>
          <div class="jarvis-bar"></div>
        </div>
      </div>
    </div>

    <style>
      .jarvis-orb-wrap{
        position:relative;width:180px;height:180px;display:flex;align-items:center;justify-content:center;
      }
      .jarvis-core{
        width:62px;height:62px;border-radius:50%;
        background:radial-gradient(circle at 35% 35%, #9BFFFF 0%, #37D8FF 35%, #0E89FF 100%);
        box-shadow:0 0 30px rgba(55,216,255,.55), 0 0 60px rgba(14,137,255,.35);
        animation: jarvisPulse 2.2s ease-in-out infinite;
      }
      .jarvis-ring{
        position:absolute;border-radius:50%;border:2px solid rgba(120,220,255,.6);
        box-shadow:0 0 18px rgba(0,194,255,.18);
      }
      .ring1{width:92px;height:92px;animation: spinA 5s linear infinite;}
      .ring2{width:132px;height:132px;border-style:dashed;animation: spinB 8s linear infinite;}
      .ring3{width:176px;height:176px;opacity:.7;animation: spinA 11s linear infinite;}
      .jarvis-bar{
        width:8px;height:22px;border-radius:999px;
        background:linear-gradient(180deg,#7DF6FF 0%, #159DFF 100%);
        animation: eq 1.2s ease-in-out infinite;
      }
      .jarvis-bar:nth-child(2){animation-delay:.15s}
      .jarvis-bar:nth-child(3){animation-delay:.3s}
      .jarvis-bar:nth-child(4){animation-delay:.45s}
      .jarvis-bar:nth-child(5){animation-delay:.6s}
      .jarvis-bar:nth-child(6){animation-delay:.75s}
      @keyframes spinA{from{transform:rotate(0)}to{transform:rotate(360deg)}}
      @keyframes spinB{from{transform:rotate(360deg)}to{transform:rotate(0)}}
      @keyframes jarvisPulse{
        0%,100%{transform:scale(1)}
        50%{transform:scale(1.16)}
      }
      @keyframes eq{
        0%,100%{height:14px;opacity:.7}
        50%{height:34px;opacity:1}
      }
    </style>
    """
    components.html(html_avatar, height=360, scrolling=False)

def page_resumo_ia():
    st.markdown(
        """
        <style>
        .ia-wrap{
            border-radius: 22px;
            padding: 16px;
            background:
              radial-gradient(circle at top left, rgba(0,153,255,0.10), transparent 30%),
              linear-gradient(135deg, #041224 0%, #071C38 55%, #0A2747 100%);
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 14px 30px rgba(0,0,0,0.18);
            margin-top: 12px;
        }

        .ia-title{
            color: #F3F7FF;
            font-size: 18px;
            font-weight: 900;
            margin-bottom: 12px;
        }

        div[data-testid="stChatMessage"]{
            background: linear-gradient(180deg, rgba(7,17,36,0.92) 0%, rgba(11,27,51,0.92) 100%) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 16px !important;
            padding: 10px 14px !important;
            margin-bottom: 10px !important;
            color: #EAF2FF !important;
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] span,
        div[data-testid="stChatMessage"] div,
        div[data-testid="stChatMessage"] strong,
        div[data-testid="stChatMessage"] li{
            color: #EAF2FF !important;
        }

        div[data-testid="stChatInput"]{
            background: linear-gradient(180deg, #071124 0%, #0B1B33 100%) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 16px !important;
            padding: 8px !important;
        }

        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input{
            background: transparent !important;
            color: #FFFFFF !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] input::placeholder{
            color: rgba(234,242,255,0.60) !important;
        }

        div[data-testid="stChatInput"] button{
            background: rgba(255,255,255,0.08) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            border-radius: 12px !important;
        }

        .p2-btn-wrap .stButton button{
            background: linear-gradient(180deg, #071124 0%, #0B1B33 100%) !important;
            color: #F3F7FF !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            border-radius: 12px !important;
            font-weight: 800 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    now = datetime.datetime.now(TZ)
    hoje = now.date()
    ini_mes = hoje.replace(day=1)

    modo = st.sidebar.selectbox(
        "Resumo (Página 2)",
        ["Auto (>=16h = mês atual)", "Mês atual", "Usar filtro do One Page (Início/Fim)"],
        index=0,
        key="p2_modo_resumo"
    )

    if modo in ("Auto (>=16h = mês atual)", "Mês atual"):
        data_ini = ini_mes
        data_fim = hoje
    else:
        data_ini = st.session_state.get("f_ini_val", hoje)
        data_fim = st.session_state.get("f_fim_val", hoje)

    payload = montar_payload_operacional(data_ini, data_fim)

    cards = [
        {
            "nome": "Linha de Montagem / Esteira (Total)",
            "produzido": payload["total"]["produzido"],
            "meta": payload["total"]["meta"],
            "performance": payload["total"]["performance_pct"],
            "qualidade": payload["total"]["qualidade_pct"],
            "inspecionado": payload["total"]["inspecionado"],
            "reprovados": payload["total"]["reprovados"],
            "status_txt": _status_class(payload["total"]["performance_pct"], payload["total"]["qualidade_pct"])[0],
            "status_class": _status_class(payload["total"]["performance_pct"], payload["total"]["qualidade_pct"])[1],
        },
        {
            "nome": "Montagem Mola",
            "produzido": payload["mola"]["produzido"],
            "meta": payload["mola"]["meta"],
            "performance": payload["mola"]["performance_pct"],
            "qualidade": payload["mola"]["qualidade_pct"],
            "inspecionado": payload["mola"]["inspecionado"],
            "reprovados": payload["mola"]["reprovados"],
            "status_txt": _status_class(payload["mola"]["performance_pct"], payload["mola"]["qualidade_pct"])[0],
            "status_class": _status_class(payload["mola"]["performance_pct"], payload["mola"]["qualidade_pct"])[1],
        },
        {
            "nome": "Montagem Manga & PNM",
            "produzido": payload["manga_pnm"]["produzido"],
            "meta": payload["manga_pnm"]["meta"],
            "performance": payload["manga_pnm"]["performance_pct"],
            "qualidade": payload["manga_pnm"]["qualidade_pct"],
            "inspecionado": payload["manga_pnm"]["inspecionado"],
            "reprovados": payload["manga_pnm"]["reprovados"],
            "status_txt": _status_class(payload["manga_pnm"]["performance_pct"], payload["manga_pnm"]["qualidade_pct"])[0],
            "status_class": _status_class(payload["manga_pnm"]["performance_pct"], payload["manga_pnm"]["qualidade_pct"])[1],
        },
    ]

    paretos = {
        "total": payload["total"]["pareto_top3"],
        "mola": payload["mola"]["pareto_top3"],
        "manga_pnm": payload["manga_pnm"]["pareto_top3"],
    }

    dashboard_html = _build_page2_html(data_ini, data_fim, now, cards, paretos)
    components.html(dashboard_html, height=560, scrolling=False)

    st.write("")
    st.markdown("<div class='ia-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='ia-title'>Assistente IA da Operação</div>", unsafe_allow_html=True)

    st.markdown("<div class='p2-btn-wrap'>", unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        gerar = st.button("Gerar resumo para reunião", use_container_width=True, key="btn_gerar_insight_p2")
    with col2:
        limpar_chat = st.button("Limpar conversa", use_container_width=True, key="btn_limpar_chat_p2")
    st.markdown("</div>", unsafe_allow_html=True)

    if "p2_chat_messages" not in st.session_state:
        st.session_state["p2_chat_messages"] = [
            {
                "role": "assistant",
                "content": "Estou pronto. Pergunte sobre performance, qualidade, Pareto, ações prioritárias ou peça uma fala para reunião."
            }
        ]

    if limpar_chat:
        st.session_state["p2_chat_messages"] = [
            {
                "role": "assistant",
                "content": "Conversa limpa. Pode me perguntar novamente sobre os indicadores do período."
            }
        ]

    if gerar:
        if not GEMINI_AVAILABLE:
            st.error("GEMINI_API_KEY não configurada.")
        else:
            prompt_resumo = f"""
Você é um analista sênior de produção e qualidade.
Responda em português do Brasil, de forma objetiva, executiva e prática.
Escreva em texto limpo, sem markdown, sem asteriscos e sem bullets decorativos.

Monte um resumo para reunião com esta estrutura:
Diagnóstico geral do período.
Pior ponto de atenção.
Três ações imediatas.
Fechamento em linguagem de gestor.

Dados:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()

            with st.spinner("Gerando resumo..."):
                txt = _gemini_generate_text(prompt_resumo)

            if txt:
                st.session_state["p2_chat_messages"].append(
                    {"role": "assistant", "content": txt}
                )

    for msg in st.session_state["p2_chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta = st.chat_input("Pergunte algo sobre os indicadores da página 2...")
    if pergunta:
        st.session_state["p2_chat_messages"].append(
            {"role": "user", "content": pergunta}
        )

        with st.chat_message("user"):
            st.markdown(pergunta)

        if not GEMINI_AVAILABLE:
            resposta = "A GEMINI_API_KEY não foi encontrada."
        else:
            historico_txt = []
            for m in st.session_state["p2_chat_messages"][-8:]:
                papel = "Usuário" if m["role"] == "user" else "Assistente"
                historico_txt.append(f"{papel}: {m['content']}")

            system_prompt = f"""
Você é um copiloto de produção e qualidade industrial.
Sempre responda em português do Brasil.
Seja direto, executivo e útil.
Baseie-se SOMENTE nos dados abaixo.
Quando fizer recomendação, conecte com performance, qualidade e Pareto.
Não invente números.
Responda em texto limpo, sem markdown, sem asteriscos e sem formatação decorativa.

Base de dados do período:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Histórico recente:
{chr(10).join(historico_txt)}
""".strip()

            try:
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        resposta = _gemini_generate_text(system_prompt)

                    if not resposta:
                        resposta = "Não consegui gerar resposta desta vez."

                    st.markdown(resposta)
            except Exception as e:
                resposta = f"Erro ao consultar Gemini: {e}"
                with st.chat_message("assistant"):
                    st.markdown(resposta)

            st.session_state["p2_chat_messages"].append(
                {"role": "assistant", "content": resposta}
            )

    st.markdown("</div>", unsafe_allow_html=True)

def page_jarvis():
    st.markdown(
        """
        <style>
        .jarvis-wrap{
            border-radius:22px;
            padding:16px;
            background:
              radial-gradient(circle at top left, rgba(0,153,255,0.10), transparent 30%),
              linear-gradient(135deg, #041224 0%, #071C38 55%, #0A2747 100%);
            border:1px solid rgba(255,255,255,0.08);
            box-shadow:0 14px 30px rgba(0,0,0,0.18);
            margin-top:12px;
        }
        .jarvis-title{
            color:#F3F7FF;
            font-size:18px;
            font-weight:900;
            margin-bottom:12px;
        }
        div[data-testid="stChatMessage"]{
            background: linear-gradient(180deg, rgba(7,17,36,0.92) 0%, rgba(11,27,51,0.92) 100%) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 16px !important;
            padding: 10px 14px !important;
            margin-bottom: 10px !important;
            color: #EAF2FF !important;
        }
        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] span,
        div[data-testid="stChatMessage"] div,
        div[data-testid="stChatMessage"] strong,
        div[data-testid="stChatMessage"] li{
            color: #EAF2FF !important;
        }
        div[data-testid="stChatInput"]{
            background: linear-gradient(180deg, #071124 0%, #0B1B33 100%) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 16px !important;
            padding: 8px !important;
        }
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input{
            background: transparent !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] input::placeholder{
            color: rgba(234,242,255,0.60) !important;
        }
        .jarvis-button .stButton button{
            background: linear-gradient(180deg, #071124 0%, #0B1B33 100%) !important;
            color: #F3F7FF !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            border-radius: 12px !important;
            font-weight: 800 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    now = datetime.datetime.now(TZ)
    hoje = now.date()
    ini_mes = hoje.replace(day=1)

    modo = st.sidebar.selectbox(
        "Modo JARVIS",
        ["Mês atual", "Usar filtro do One Page (Início/Fim)"],
        index=0,
        key="jarvis_modo"
    )

    if modo == "Mês atual":
        data_ini = ini_mes
        data_fim = hoje
    else:
        data_ini = st.session_state.get("f_ini_val", hoje)
        data_fim = st.session_state.get("f_fim_val", hoje)

    payload = montar_payload_operacional(data_ini, data_fim)
    render_jarvis_avatar_html()

    st.markdown("<div class='jarvis-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='jarvis-title'>JARVIS • Assistente Executivo-Industrial</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        auto_falar = st.toggle("Falar resposta", value=True, key="jarvis_auto_falar")
    with col2:
        usar_mic = st.toggle("Usar microfone", value=True, key="jarvis_mic_toggle")
    with col3:
        if st.button("Limpar conversa", use_container_width=True, key="jarvis_limpar"):
            st.session_state["jarvis_messages"] = [
                {
                    "role": "assistant",
                    "content": "Sou o JARVIS. Posso analisar seus dados operacionais e também responder perguntas gerais, como dias úteis do mês, datas, cálculos simples e apoio executivo."
                }
            ]
            st.rerun()

    if "jarvis_messages" not in st.session_state:
        st.session_state["jarvis_messages"] = [
            {
                "role": "assistant",
                "content": "Sou o JARVIS. Posso analisar seus dados operacionais e também responder perguntas gerais, como dias úteis do mês, datas, cálculos simples e apoio executivo."
            }
        ]

    st.markdown(
        f"""
        <div style="margin:10px 0 14px 0;padding:12px 14px;border-radius:16px;
                    background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);color:#EAF2FF;">
            <b>Contexto carregado:</b> período operacional de <b>{payload["periodo_operacional"]["inicio"]}</b> até
            <b>{payload["periodo_operacional"]["fim"]}</b> • hoje <b>{payload["data_contexto"]["data_hoje"]}</b> •
            dias úteis do mês no Brasil: <b>{payload["data_contexto"]["dias_uteis_brasil_mes_atual"]["total"]}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    pergunta_voz = None
    if usar_mic:
        st.markdown("<div class='jarvis-button'>", unsafe_allow_html=True)
        pergunta_voz = speech_to_text(
            language="pt-BR",
            start_prompt="🎤 Falar com JARVIS",
            stop_prompt="⏹️ Parar",
            just_once=True,
            use_container_width=True,
            key="jarvis_stt"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    for msg in st.session_state["jarvis_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pergunta_texto = st.chat_input("Pergunte qualquer coisa ao JARVIS...")
    pergunta = pergunta_voz or pergunta_texto

    if pergunta:
        st.session_state["jarvis_messages"].append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        historico_txt = []
        for m in st.session_state["jarvis_messages"][-10:]:
            papel = "Usuário" if m["role"] == "user" else "Assistente"
            historico_txt.append(f"{papel}: {m['content']}")

        prompt = f"""
Você é o JARVIS, um assistente executivo-industrial em português do Brasil.

SEU PAPEL:
- Responder sobre os dados do painel operacional com precisão.
- Também responder perguntas gerais úteis para gestão, como calendário, dias úteis do mês no Brasil, contagens de datas, matemática simples, organização, comunicação, resumos, comparações e apoio executivo.
- Quando a pergunta for sobre produção, qualidade, Pareto, meta, aprovação, atraso, indicadores ou linhas, use SOMENTE os dados do payload.
- Quando a pergunta for geral e puder ser respondida com data, calendário, raciocínio ou o contexto já fornecido, responda normalmente.
- Se a pergunta exigir internet, notícia atual, legislação detalhada ou algo não presente no payload/contexto, diga com clareza que não está no painel.
- Seja direto, útil e com linguagem executiva.
- Não invente números.
- Responda como fala humana, natural, curta e fluida.
- Não use markdown.
- Não use asteriscos.
- Não use listas decorativas.
- Evite títulos artificiais.
- Fale como um assistente premium, estilo navegação guiada.

CONTEXTO DO PAINEL:
{json.dumps(payload, ensure_ascii=False, indent=2)}

HISTÓRICO RECENTE:
{chr(10).join(historico_txt)}

PERGUNTA ATUAL:
{pergunta}
""".strip()

        with st.chat_message("assistant"):
            with st.spinner("JARVIS processando..."):
                resposta = _gemini_generate_text(prompt)
            st.markdown(resposta)

        st.session_state["jarvis_messages"].append({"role": "assistant", "content": resposta})

        if auto_falar and resposta and not resposta.lower().startswith("erro ao consultar"):
            falar_no_navegador(resposta)

    st.markdown("</div>", unsafe_allow_html=True)

# ==============================
# MAIN
# ==============================
def main():
    aplicar_css_app()

    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key="autorefresh_onepage_linhas")

    now = datetime.datetime.now(TZ)
    hoje = now.date()

    st.sidebar.markdown("## Menu")
    pagina = st.sidebar.radio(
        "Página",
        ["One Page (TV)", "Resumo Inteligente + IA", "JARVIS Voice"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filtro (Data) — One Page")
    data_inicio = st.sidebar.date_input("Início", hoje, key="f_ini")
    data_fim = st.sidebar.date_input("Fim", hoje, key="f_fim")

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
        page_onepage(data_inicio, data_fim)

    elif pagina == "Resumo Inteligente + IA":
        st.markdown(
            "<div class='op-sub'>Modo: <b>Resumo Inteligente + IA</b></div>",
            unsafe_allow_html=True
        )
        page_resumo_ia()

    else:
        st.markdown(
            "<div class='op-sub'>Modo: <b>JARVIS Voice</b></div>",
            unsafe_allow_html=True
        )
        page_jarvis()

    st.markdown(
        f"<p style='color:rgba(11,27,51,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{now.strftime('%H:%M:%S')}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
