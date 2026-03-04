import os
import datetime
from pathlib import Path
import streamlit as st
import pandas as pd
import pytz
from supabase import create_client
from dotenv import load_dotenv
import streamlit.components.v1 as components

# ==============================
# ✅ PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="One Page Gerencial — Linhas",
    layout="wide",
    initial_sidebar_state="expanded"  # ✅ sidebar aparece
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
# CSS (fundo branco / cards navy / clean) + sidebar OK
# ==============================
def aplicar_css_app():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 0.9rem;
            padding-bottom: 0.9rem;
            padding-left: 1.4rem;
            padding-right: 1.4rem;
            max-width: 100%;
        }
        header[data-testid="stHeader"] {display:none;}
        div[data-testid="stToolbar"] {visibility:hidden;height:0;position:fixed;}

        /* ✅ NÃO esconder sidebar */
        section[data-testid='stSidebar']{display:block !important;}

        .stApp { background: #f6f7fb; }

        .op-title {
            font-size: 26px;
            font-weight: 950;
            color: #0b1b3a;
            letter-spacing: 0.6px;
            margin: 4px 0 4px 0;
        }
        .op-sub {
            color: rgba(11,27,58,0.65);
            margin-bottom: 14px;
            font-weight: 600;
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

    # tz-aware
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

@st.cache_data(ttl=600)
def carregar_apontamentos():
    return _load_table_paged("apontamentos")

@st.cache_data(ttl=600)
def carregar_checklists():
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

def calcular_aprovacao(df_checks: pd.DataFrame, df_apont: pd.DataFrame) -> tuple[float, int, int]:
    """
    Retorna: (aprovacao%, inspecionado, reprovados)
    Reprovado = último status "não conforme" OU produto_reprovado != "não" OU teve reinspecao "sim".
    """
    if df_checks is None or df_checks.empty or df_apont is None or df_apont.empty:
        return 0.0, 0, 0
    if "numero_serie" not in df_apont.columns or "numero_serie" not in df_checks.columns:
        return 0.0, 0, 0

    series_prod = df_apont["numero_serie"].dropna().unique()
    dfc = df_checks[df_checks["numero_serie"].isin(series_prod)].copy()
    if dfc.empty:
        return 0.0, 0, 0

    series_unicas = dfc["numero_serie"].dropna().unique()
    aprovados = 0
    reprovados = 0

    for serie in series_unicas:
        checks = dfc[dfc["numero_serie"] == serie]
        if checks.empty:
            continue

        reinspecao = False
        if "reinspecao" in checks.columns:
            reinspecao = (checks["reinspecao"].astype(str).str.strip().str.lower() == "sim").any()

        aprovado = True
        if "produto_reprovado" in checks.columns:
            ultimo = str(checks.tail(1).iloc[0].get("produto_reprovado", "Não")).strip().lower()
            aprovado = (ultimo == "não") and (not reinspecao)
        else:
            ultimo_status = str(checks.tail(1).iloc[0].get("status", "")).strip().lower()
            aprovado = (ultimo_status != "não conforme") and (not reinspecao)

        if aprovado:
            aprovados += 1
        else:
            reprovados += 1

    total_inspecionado = int(len(series_unicas))
    aprovacao_perc = (aprovados / total_inspecionado) * 100 if total_inspecionado > 0 else 0.0
    return float(aprovacao_perc), total_inspecionado, int(reprovados)

def calcular_oee(atraso: int, meta_acumulada: int, aprovacao_perc: float) -> float:
    performance_fraction = max(1 - (atraso / meta_acumulada), 0) if meta_acumulada > 0 else 1
    quality_fraction = (aprovacao_perc / 100) if aprovacao_perc > 0 else 1
    return float(performance_fraction * quality_fraction * 100)

# ==============================
# Resumos (3 cards: Total Apontamentos / Mola / Manga&PNM)
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
        datetime.time(15,0):12, datetime.time(16,0):0,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp, reprov = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    # Rodapé por tipo_producao dentro de apontamentos (inclui MANGA/PNM também)
    rodape = ""
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        v = df_apont["tipo_producao"].astype(str)
        eixo = int(v.str.contains("EIXO|ESTEIRA", case=False, na=False).sum())
        manga = int(v.str.contains("MANGA", case=False, na=False).sum())
        pnm = int(v.str.contains("PNM", case=False, na=False).sum())
        rodape = f"Eixo/Esteira: {eixo} | Manga: {manga} | PNM: {pnm}"

    return {
        "key": "total",
        "nome": "APONTAMENTOS (TOTAL)",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "reprovados": reprov,
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
        datetime.time(15, 0): 8,  datetime.time(16, 0): 14,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="inicio_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp, reprov = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    return {
        "key": "mola",
        "nome": "MONTAGEM MOLA",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "reprovados": reprov,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": (f"Reprovados: {reprov}" if insp > 0 else ""),
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
        datetime.time(15, 0): 4, datetime.time(16, 0): 0,
    }

    total = int(len(df_apont))
    meta_acum = calcular_meta_acumulada_por_hora(meta_hora, hoje, hora_atual, modo="fim_hora")
    atraso = int(max(meta_acum - total, 0))

    aprov, insp, reprov = calcular_aprovacao(df_checks, df_apont)
    oee = calcular_oee(atraso, meta_acum, aprov)

    rodape = ""
    if not df_apont.empty and "tipo_producao" in df_apont.columns:
        v = df_apont["tipo_producao"].astype(str)
        manga = int(v.str.contains("MANGA", case=False, na=False).sum())
        pnm = int(v.str.contains("PNM", case=False, na=False).sum())
        rodape = f"MANGA: {manga} | PNM: {pnm}"

    return {
        "key": "manga_pnm",
        "nome": "MONTAGEM MANGA & PNM",
        "total": total,
        "aprovacao": aprov,
        "inspecionado": insp,
        "reprovados": reprov,
        "atraso": atraso,
        "status": ("Dentro da Meta" if atraso == 0 else f"Atraso: {atraso}"),
        "rodape": rodape,
        "oee": oee
    }

# ==============================
# Insights (sem IA externa)
# ==============================
def gerar_insights(resumos_dia: list[dict], resumos_mes: list[dict]) -> list[str]:
    msgs = []
    # 1) Alertas por atraso
    for r in resumos_dia:
        if r.get("atraso", 0) > 0:
            msgs.append(f"• {r['nome']}: atraso de **{r['atraso']}** vs meta acumulada (foco em performance).")

    # 2) Qualidade baixa
    for r in resumos_dia:
        if r.get("inspecionado", 0) >= 10 and r.get("aprovacao", 100) < 95:
            msgs.append(f"• {r['nome']}: aprovação **{r['aprovacao']:.1f}%** com **{r['reprovados']}** reprovados (foco em qualidade).")

    # 3) Comparação dia x mês (tendência)
    for rd in resumos_dia:
        rm = next((x for x in resumos_mes if x["key"] == rd["key"]), None)
        if rm and rm.get("inspecionado", 0) >= 30 and rd.get("inspecionado", 0) >= 10:
            if rd["aprovacao"] + 2 < rm["aprovacao"]:
                msgs.append(f"• {rd['nome']}: qualidade do dia abaixo do mês (**{rd['aprovacao']:.1f}%** vs **{rm['aprovacao']:.1f}%**).")
            if rd["oee"] + 2 < rm["oee"]:
                msgs.append(f"• {rd['nome']}: OEE do dia abaixo do mês (**{rd['oee']:.1f}%** vs **{rm['oee']:.1f}%**).")

    if not msgs:
        msgs.append("• Sem alertas relevantes agora. Performance e qualidade dentro do esperado.")
    return msgs

# ==============================
# ONEPAGE HTML (3 cards alinhados)
# ==============================
def render_onepage_html(resumos: list[dict]):
    HEIGHT = 430
    js_data = [{"key": r["key"], "oee": round(float(r["oee"]), 1)} for r in resumos]

    def pill_for(r: dict):
        status_ok = (int(r.get("atraso", 0)) == 0) and (r.get("inspecionado", 0) > 0)
        if status_ok:
            return "OK", "rgba(56,161,105,0.18)", "rgba(56,161,105,0.45)"
        return "ATENÇÃO", "rgba(197,48,48,0.14)", "rgba(197,48,48,0.35)"

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
                <div class="mini-foot">{r.get("rodape","")}</div>
              </div>

              <div class="mini">
                <div class="mini-title">% Aprovação</div>
                <div class="mini-val">{float(r["aprovacao"]):.1f}%</div>
                <div class="mini-foot">Inspec.: {r["inspecionado"]} • Reprov.: {r["reprovados"]}</div>
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
        .grid-3 {{
          display:grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 26px;
          align-items: stretch;
        }}

        .card {{
          border-radius:24px;
          padding:16px;
          background: linear-gradient(160deg, #081733 0%, #06122a 40%, #050f25 100%);
          border: 1px solid rgba(255,255,255,0.08);
          box-shadow: 0 18px 34px rgba(0,0,0,0.18);
          height: 340px;
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
          color:#F2F6FF;
          text-transform:uppercase;
          line-height:1.05;
          letter-spacing:.2px;
        }}
        .sub {{
          font-size:12px;
          color: rgba(255,255,255,0.72);
          margin-top:3px;
        }}

        .pill {{
          font-size:11px;
          font-weight:950;
          padding:6px 10px;
          border-radius:999px;
          color:#F2F6FF;
          white-space:nowrap;
        }}

        .mini-grid {{
          display:grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }}

        .mini {{
          border-radius:18px;
          padding:12px 12px;
          background: rgba(255,255,255,0.05);
          border:1px solid rgba(255,255,255,0.08);
          height: 108px;
          overflow:hidden;
        }}

        .mini-title {{
          font-size:11px;
          font-weight:900;
          color:rgba(255,255,255,0.82);
          margin-bottom:8px;
          text-transform:uppercase;
          letter-spacing: .2px;
        }}

        .mini-val {{
          font-size:20px;
          font-weight:950;
          line-height:1.05;
        }}

        .mini-foot {{
          font-size:11px;
          color:rgba(255,255,255,0.70);
          margin-top:6px;
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
          height: 74px;   /* ✅ não corta 0% e 100% */
          width: 100%;
          margin-top: 4px;
        }}

        @media (max-width: 1400px) {{
          .grid-3 {{ grid-template-columns: 1fr; }}
          .card {{ height: 340px; }}
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
              axis: {{ range: [0, 100], tickmode: "array", tickvals:[0,100], ticktext:["0%","100%"], tickfont:{{size:11}} }},
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
            margin: {{ l: 6, r: 6, t: 0, b: 0 }},
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            height: 74
          }};

          Plotly.newPlot(id, data, layout, {{displayModeBar:false, responsive:true}});
        }}

        dados.forEach(d => renderGauge("g_" + d.key, d.oee));
      </script>
    </div>
    """
    components.html(html, height=HEIGHT, scrolling=False)

# ==============================
# Cálculo "Mês atual"
# ==============================
def range_mes_atual() -> tuple[datetime.date, datetime.date]:
    now = datetime.datetime.now(TZ)
    inicio = now.replace(day=1).date()
    fim = now.date()
    return inicio, fim

# ==============================
# Main
# ==============================
def main():
    aplicar_css_app()

    # Autorefresh sem duplicar key
    if AUTORELOAD_AVAILABLE:
        st_autorefresh(interval=60000, key=f"autorefresh_{Path(__file__).stem}")

    now = datetime.datetime.now(TZ)
    hoje = now.date()

    # ==========================
    # Sidebar (filtros + página)
    # ==========================
    st.sidebar.markdown("## Filtros")

    modo = st.sidebar.selectbox(
        "Modo",
        ["Auto (06–16 = Dia | pós 16 = Mês)", "Turno (Dia)", "Mês (atual)"],
        index=0
    )

    pagina = st.sidebar.radio("Página", ["Dashboard", "Resumo do mês + Insights"], index=0)

    # por padrão: dia
    data_inicio = hoje
    data_fim = hoje

    # se estiver em "Turno (Dia)" deixa escolher
    if modo == "Turno (Dia)":
        data_inicio = st.sidebar.date_input("Data", hoje)
        data_fim = data_inicio

    # modo mês (manual) ou automático após 16
    auto_mes = (modo.startswith("Auto") and now.hour >= 16)
    if modo == "Mês (atual)" or auto_mes:
        data_inicio, data_fim = range_mes_atual()

    # ==========================
    # Topo
    # ==========================
    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='op-sub'>Período: <b>{data_inicio}</b> até <b>{data_fim}</b></div>",
        unsafe_allow_html=True
    )

    # ==========================
    # Resumos (Dia e Mês)
    # ==========================
    resumos = [
        resumo_total_apontamentos(data_inicio, data_fim),
        resumo_mola(data_inicio, data_fim),
        resumo_manga_pnm(data_inicio, data_fim),
    ]

    # Para Insights: sempre calcula também o mês atual (pra comparar)
    mes_i, mes_f = range_mes_atual()
    resumos_mes = [
        resumo_total_apontamentos(mes_i, mes_f),
        resumo_mola(mes_i, mes_f),
        resumo_manga_pnm(mes_i, mes_f),
    ]

    if pagina == "Dashboard":
        render_onepage_html(resumos)
    else:
        st.markdown("### Resumo do mês + Insights")
        render_onepage_html(resumos_mes)
        st.markdown("#### Insights (automáticos)")
        for m in gerar_insights(resumos, resumos_mes):
            st.markdown(m)

    hora = now.strftime("%H:%M:%S")
    st.markdown(
        f"<p style='color:rgba(11,27,58,0.55);text-align:center;margin-top:10px;'>Atualizado às <b>{hora}</b></p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
