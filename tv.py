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
        section[data-testid="stSidebar"] {background: #FFFFFF;}

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

        /* Deixa o botão da sidebar mais discreto */
        button[kind="header"] {opacity: 0.25;}
        button[kind="header"]:hover {opacity: 1;}

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
    - Se reinspecao == "Sim" e houver reprovação no último registro, continua reprovado.
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

    # reinspecao (se existir)
    reinspecao_sim = None
    if "reinspecao" in ult.columns:
        reinspecao_sim = ult["reinspecao"].astype(str).map(_is_sim)

    reprovados = 0
    for i, row in ult.iterrows():
        rep = _is_reprovado_row(row)
        # Se reinspecao existir e for "Sim", mantemos o resultado do último registro
        # (se o último ainda está reprovado, conta como reprovado).
        if rep:
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

    # rodapé com split por tipo_producao (se existir)
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

    # ✅ Aprovação robusta (corrige 100% indevido quando há reprovados)
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
# ONEPAGE (1 iframe, 3 cards alinhados)
# + eixo 0% e 100% visíveis
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
# Main
# - Sidebar com filtro de data (oculta/recolhida, mas disponível)
# - Congela visual enquanto recalcula (mostra último HTML imediatamente)
# ==============================
def main():
    aplicar_css_app()

    # ✅ Autorefresh com key única (evita DuplicateElementKey)
    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key="autorefresh_onepage_linhas")

    hoje = datetime.datetime.now(TZ).date()

    # Sidebar (recolhida por padrão, mas existe)
    st.sidebar.markdown("### Filtro (Data)")
    data_inicio = st.sidebar.date_input("Início", hoje, key="f_ini")
    data_fim = st.sidebar.date_input("Fim", hoje, key="f_fim")

    # Botão opcional de atualizar manualmente (sem “piscada” a cada clique no navegador)
    if st.sidebar.button("Atualizar agora"):
        st.cache_data.clear()

    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='op-sub'>Período: <b>{data_inicio}</b> até <b>{data_fim}</b></div>",
        unsafe_allow_html=True
    )

    # ✅ Placeholder: renderiza o último HTML primeiro (evita ficar branco durante atualização)
    ph = st.empty()

    if "last_html" in st.session_state and "last_height" in st.session_state:
        with ph.container():
            components.html(st.session_state["last_html"], height=st.session_state["last_height"], scrolling=False)

    # ✅ Calcula dados (cache ajuda a ser rápido)
    resumos = [
        resumo_esteira(data_inicio, data_fim),
        resumo_mola(data_inicio, data_fim),
        resumo_manga_pnm(data_inicio, data_fim),
    ]

    html, height = render_onepage_html(resumos)

    # Atualiza o placeholder com o HTML novo
    with ph.container():
        components.html(html, height=height, scrolling=False)

    # Guarda para “congelar” no próximo refresh
    st.session_state["last_html"] = html
    st.session_state["last_height"] = height

    hora = datetime.datetime.now(TZ).strftime("%H:%M:%S")
    st.markdown(
        f"<p style='color:rgba(11,27,51,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{hora}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
