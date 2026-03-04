import os
import uuid
import datetime
from pathlib import Path

import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from supabase import create_client

# ==============================
# ✅ PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="One Page Gerencial — Linhas",
    layout="wide",
    initial_sidebar_state="collapsed"  # sidebar existe, mas começa recolhida
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
# CSS (APP branco + cards azul marinho)
# + esconde indicador/flash de atualização
# ==============================
def aplicar_css_app():
    st.markdown(
        """
        <style>
        /* Área principal */
        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 0.8rem;
            padding-left: 1.2rem;
            padding-right: 1.2rem;
            max-width: 100%;
        }

        /* Esconde header/toolbar */
        header[data-testid="stHeader"] {display:none;}
        div[data-testid="stToolbar"] {visibility:hidden;height:0;position:fixed;}

        /* Esconde widgets de status/running do Streamlit (reduz "branco" e piscada) */
        div[data-testid="stStatusWidget"] {display:none !important;}
        div[data-testid="stDecoration"] {display:none !important;}
        div[data-testid="stSpinner"] {display:none !important;}

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

        /* Deixa o botão da sidebar mais discreto */
        button[kind="header"] {opacity: 0.25;}
        button[kind="header"]:hover {opacity: 1;}

        /* ====== Resumo + IA (futurista minimalista) ====== */
        .rx-wrap {
            background: linear-gradient(135deg, #071124 0%, #0B1B33 55%, #093A5A 100%);
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow: 0 14px 26px rgba(0,0,0,0.10);
            border-radius: 18px;
            padding: 14px 16px;
            color: #F3F7FF;
        }
        .rx-h {
            font-weight: 950;
            letter-spacing: .2px;
            text-transform: uppercase;
            font-size: 12px;
            color: rgba(243,247,255,0.88);
            margin-bottom: 10px;
        }
        .rx-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(220px, 1fr));
            gap: 10px;
        }
        .rx-kpi {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
            padding: 10px 12px;
            min-height: 74px;
        }
        .rx-kpi .k {
            font-size: 10px;
            font-weight: 900;
            text-transform: uppercase;
            color: rgba(243,247,255,0.75);
            margin-bottom: 6px;
        }
        .rx-kpi .v {
            font-size: 18px;
            font-weight: 950;
            color: rgba(243,247,255,0.95);
            line-height: 1.0;
        }
        .rx-kpi .s {
            font-size: 10px;
            color: rgba(243,247,255,0.70);
            margin-top: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .rx-line {
            margin-top: 10px;
            display: grid;
            grid-template-columns: 1.1fr .9fr;
            gap: 10px;
        }
        .rx-box {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 14px;
            padding: 12px;
        }
        .rx-box h4 {
            margin: 0 0 8px 0;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: .2px;
            color: rgba(243,247,255,0.85);
        }
        .rx-ul { margin: 0; padding-left: 16px; color: rgba(243,247,255,0.88); }
        .rx-ul li { margin: 6px 0; font-size: 12px; }
        @media (max-width: 1200px) {
            .rx-grid { grid-template-columns: 1fr; }
            .rx-line { grid-template-columns: 1fr; }
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

    # Se já vier timezone-aware
    if getattr(dt.dt, "tz", None) is not None:
        df[col] = dt.dt.tz_convert(TZ)
        return df

    # Se vier naive, assume horário local
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

def _norm(x) -> str:
    return str(x).strip().lower()

def _is_sim(x) -> bool:
    v = _norm(x)
    return v in ("sim", "s", "1", "true", "verdadeiro", "yes", "y")

def _is_nao(x) -> bool:
    v = _norm(x)
    return v in ("não", "nao", "n", "0", "false", "falso", "no")

def _is_reprovado_row(row: pd.Series) -> bool:
    # 1) status
    if "status" in row.index and _norm(row.get("status")) in ("não conforme", "nao conforme", "reprovado"):
        return True

    # 2) produto_reprovado (padrões: "Sim"=reprovado, "Não"=ok)
    if "produto_reprovado" in row.index:
        pr = row.get("produto_reprovado")
        if _is_sim(pr):
            return True
        if _is_nao(pr):
            return False

    # 3) flags alternativas comuns
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

    Regra robusta:
    - Para cada número de série, usa o último registro (por data_hora se existir),
      senão usa o último por ordem de carregamento.
    - Reprovado se status == "não conforme" OU produto_reprovado == "Sim" (ou equivalentes).
    """
    if df_checks is None or df_checks.empty or df_apont is None or df_apont.empty:
        return 0.0, 0, 0
    if "numero_serie" not in df_apont.columns or "numero_serie" not in df_checks.columns:
        return 0.0, 0, 0

    series_validas = pd.Series(df_apont["numero_serie"].dropna().unique())
    dfc = df_checks[df_checks["numero_serie"].isin(series_validas)].copy()
    if dfc.empty:
        return 0.0, 0, 0

    # garante ordenação (se tiver data_hora no checklist)
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

def calcular_oee(atraso: int, meta_acumulada: int, aprovacao_perc: float) -> float:
    performance_fraction = max(1 - (atraso / meta_acumulada), 0) if meta_acumulada > 0 else 1
    quality_fraction = (aprovacao_perc / 100) if aprovacao_perc > 0 else 0
    return float(performance_fraction * quality_fraction * 100)

# ==============================
# Resumos (3 cards: APONTAMENTOS total, MOLA, MANGA&PNM)
# ==============================
def resumo_esteira(data_inicio: datetime.date, data_fim: datetime.date) -> dict:
    hoje = datetime.datetime.now(TZ).date()
    hora_atual = datetime.datetime.now(TZ)

    df_apont = filtrar_periodo(carregar_apontamentos(), data_inicio, data_fim)
    df_checks = filtrar_periodo(carregar_checklists(), data_inicio, data_fim)

    # ✅ NÃO FILTRA MAIS: pega tudo da tabela "apontamentos"
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
        "key": "esteira",
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

    aprov, insp, rep = calcular_aprovacao(df_checks, df_apont)  # ✅ robusto
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
# ONEPAGE (1 iframe, 3 cards alinhados)
# + eixo 0% e 100% visíveis
# (NÃO MEXER NA ESTRUTURA DA 1ª PÁGINA)
# ==============================
def render_onepage_html(resumos: list[dict]) -> str:
    HEIGHT = 430
    js_data = [{"key": r["key"], "oee": round(float(r["oee"]), 1)} for r in resumos]

    def pill_for(r: dict) -> tuple[str, str, str]:
        status_ok = (int(r.get("atraso", 0)) == 0) and ("sem fonte" not in str(r.get("status", "")).lower())
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
        /* ✅ 3 cards lado a lado */
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
# Pareto TOP 3 (falhas) - robusto
# ==============================
def _find_falha_col(df: pd.DataFrame) -> str | None:
    candidatos = [
        "falha", "defeito", "motivo", "nao_conformidade", "não_conformidade",
        "descricao_falha", "descrição_falha", "tipo_falha", "ocorrencia",
        "item", "ponto", "anomalia", "causa", "problema"
    ]
    cols = {c.lower(): c for c in df.columns}
    for c in candidatos:
        if c.lower() in cols:
            return cols[c.lower()]
    return None

def pareto_top3_falhas(df_checks_periodo: pd.DataFrame) -> list[tuple[str, int]]:
    """
    Conta TOP 3 falhas somente em linhas reprovadas (por linha, não por série).
    Se não existir coluna de falha, retorna vazio.
    """
    if df_checks_periodo is None or df_checks_periodo.empty:
        return []

    falha_col = _find_falha_col(df_checks_periodo)
    if not falha_col:
        return []

    d = df_checks_periodo.copy()
    # marca reprovados por linha
    d["__reprov"] = d.apply(_is_reprovado_row, axis=1)
    d = d[d["__reprov"] == True].copy()
    if d.empty:
        return []

    d[falha_col] = d[falha_col].astype(str).str.strip()
    d = d[d[falha_col] != ""]
    if d.empty:
        return []

    top = d[falha_col].value_counts().head(3)
    return [(idx, int(val)) for idx, val in top.items()]

# ==============================
# IA (OpenAI) - funciona por ENV ou por campo no sidebar
# ==============================
def call_openai_insights(api_key: str, modelo: str, payload_texto: str) -> str:
    """
    Tenta usar SDK novo (openai). Se não tiver, cai fora com erro claro.
    """
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("Biblioteca 'openai' não instalada no ambiente. Adicione em requirements.txt: openai") from e

    client = OpenAI(api_key=api_key)

    prompt = f"""
Você é um analista Lean/Produção e Qualidade.
Gere um resumo minimalista e acionável (máx 10 linhas), em português do Brasil.
- Performance = atraso/meta + OEE
- Qualidade = aprovação + reprovados
- Cite os TOP 3 do pareto como foco de ataque
- Sugira ações práticas (check rápido) sem inventar fatos.

DADOS:
{payload_texto}
""".strip()

    resp = client.responses.create(
        model=modelo,
        input=prompt,
    )
    try:
        return resp.output_text.strip()
    except Exception:
        return str(resp).strip()

# ==============================
# Página 2: Resumo minimalista + IA
# ==============================
def render_resumo_com_ia(
    data_inicio: datetime.date,
    data_fim: datetime.date,
    api_key_ia: str,
    modelo_ia: str
):
    # Resumos (mesmo cálculo dos cards)
    r1 = resumo_esteira(data_inicio, data_fim)
    r2 = resumo_mola(data_inicio, data_fim)
    r3 = resumo_manga_pnm(data_inicio, data_fim)

    # Pareto na ESTEIRA (checklists geral) no período
    df_checks = filtrar_periodo(carregar_checklists(), data_inicio, data_fim)
    top3 = pareto_top3_falhas(df_checks)

    top3_txt = " | ".join([f"{n} ({q})" for n, q in top3]) if top3 else "Sem coluna de falha / sem reprovações"

    # bloco futurista minimalista (não mexe nos cards)
    html = f"""
    <div class="rx-wrap">
        <div class="rx-h">Resumo do período • Minimalista</div>

        <div class="rx-grid">
            <div class="rx-kpi">
                <div class="k">Performance (Total)</div>
                <div class="v">OEE {r1['oee']:.1f}% • Atraso {r1['atraso']}</div>
                <div class="s">Produzido: {r1['total']} • Meta acumulada: (via horário)</div>
            </div>
            <div class="rx-kpi">
                <div class="k">Qualidade (Total)</div>
                <div class="v">{r1['aprovacao']:.1f}% • Reprov. {int(r1['reprovados'])}</div>
                <div class="s">Inspec.: {int(r1['inspecionado'])}</div>
            </div>
            <div class="rx-kpi">
                <div class="k">Pareto Top 3 (Esteira)</div>
                <div class="v" style="font-size:13px; line-height:1.2;">{top3_txt}</div>
                <div class="s">Foco de ataque do dia/mês</div>
            </div>
        </div>

        <div class="rx-line">
            <div class="rx-box">
                <h4>Linhas (visão rápida)</h4>
                <ul class="rx-ul">
                    <li><b>{r2['nome']}</b> — OEE {r2['oee']:.1f}% • Atraso {r2['atraso']} • Qualidade {r2['aprovacao']:.1f}% • Reprov. {int(r2['reprovados'])}</li>
                    <li><b>{r3['nome']}</b> — OEE {r3['oee']:.1f}% • Atraso {r3['atraso']} • Qualidade {r3['aprovacao']:.1f}% • Reprov. {int(r3['reprovados'])}</li>
                </ul>
            </div>

            <div class="rx-box">
                <h4>Insights</h4>
                <div style="font-size:12px; color:rgba(243,247,255,0.88);">
                    Clique em <b>Gerar Insights IA</b> para recomendações.
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # Payload para IA
    payload = {
        "periodo": f"{data_inicio} até {data_fim}",
        "total": r1,
        "mola": r2,
        "manga_pnm": r3,
        "pareto_top3": top3
    }
    payload_texto = str(payload)

    # Botão IA
    col1, col2 = st.columns([1, 2])
    with col1:
        gerar = st.button("Gerar Insights IA", use_container_width=True)
    with col2:
        st.caption("Se não sair nada, falta configurar a API Key (sidebar).")

    if "ia_texto" not in st.session_state:
        st.session_state["ia_texto"] = ""

    if gerar:
        if not api_key_ia:
            st.warning("Falta a OpenAI API Key. Cole na sidebar (campo 'OpenAI API Key') ou configure no env.")
        else:
            try:
                with st.spinner("Gerando insights..."):
                    texto = call_openai_insights(api_key_ia, modelo_ia, payload_texto)
                st.session_state["ia_texto"] = texto
            except Exception as e:
                st.error(str(e))

    if st.session_state.get("ia_texto"):
        st.text_area("Insights IA (salvo até você gerar de novo)", value=st.session_state["ia_texto"], height=220)

# ==============================
# Main
# - Sidebar com pagina + modo resumo
# - Dashboard preservado (cards)
# ==============================
def main():
    aplicar_css_app()

    # ✅ Autorefresh com key fixa (evita DuplicateElementKey)
    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key="autorefresh_onepage_linhas")

    now = datetime.datetime.now(TZ)
    hoje = now.date()

    # ==========================
    # Sidebar: navegação
    # ==========================
    st.sidebar.markdown("## Menu")
    pagina = st.sidebar.radio("Página", ["Dashboard", "Resumo + IA"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Filtro (Data)")
    data_inicio = st.sidebar.date_input("Início", hoje, key="f_ini")
    data_fim = st.sidebar.date_input("Fim", hoje, key="f_fim")

    if st.sidebar.button("Atualizar agora"):
        st.cache_data.clear()

    # ==========================
    # Sidebar: Resumo + IA
    # ==========================
    st.sidebar.markdown("---")
    st.sidebar.markdown("## IA (opcional)")
    # permite colar sem saber env
    if "openai_key_ui" not in st.session_state:
        st.session_state["openai_key_ui"] = ""

    openai_key_ui = st.sidebar.text_input(
        "OpenAI API Key",
        value=st.session_state["openai_key_ui"],
        type="password",
        help="Cole aqui para habilitar IA (não aparece na tela). Depois te mostro como pôr no env."
    )
    st.session_state["openai_key_ui"] = openai_key_ui

    modelo_ia = st.sidebar.text_input("Modelo", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Resumo (Auto 16h)")
    modo_resumo = st.sidebar.selectbox(
        "Modo do resumo",
        ["Auto (>=16h = mês)", "Dia (manual)", "Mês atual"],
        index=0
    )

    # ==========================
    # Topo
    # ==========================
    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='op-sub'>Período: <b>{data_inicio}</b> até <b>{data_fim}</b></div>",
        unsafe_allow_html=True
    )

    # ==========================
    # DASHBOARD (1ª página) - PRESERVADO
    # ==========================
    if pagina == "Dashboard":
        # ✅ Placeholder: renderiza último HTML primeiro (evita ficar branco durante atualização)
        ph = st.empty()

        if "last_html" in st.session_state and "last_height" in st.session_state:
            with ph.container():
                components.html(st.session_state["last_html"], height=st.session_state["last_height"], scrolling=False)

        resumos = [
            resumo_esteira(data_inicio, data_fim),
            resumo_mola(data_inicio, data_fim),
            resumo_manga_pnm(data_inicio, data_fim),
        ]

        html, height = render_onepage_html(resumos)

        with ph.container():
            components.html(html, height=height, scrolling=False)

        st.session_state["last_html"] = html
        st.session_state["last_height"] = height

    # ==========================
    # RESUMO + IA (2ª página) - NOVO
    # ==========================
    else:
        # define período do resumo
        if modo_resumo == "Mês atual" or (modo_resumo.startswith("Auto") and now.hour >= 16):
            ini = now.replace(day=1).date()
            fim = now.date()
        else:
            ini = data_inicio
            fim = data_fim

        # pega key da UI ou do env
        api_key_ia = (openai_key_ui or os.getenv("OPENAI_API_KEY", "")).strip()

        render_resumo_com_ia(
            data_inicio=ini,
            data_fim=fim,
            api_key_ia=api_key_ia,
            modelo_ia=modelo_ia.strip() or "gpt-4o-mini"
        )

    # ==========================
    # Rodapé
    # ==========================
    hora = now.strftime("%H:%M:%S")
    st.markdown(
        f"<p style='color:rgba(11,27,51,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{hora}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
