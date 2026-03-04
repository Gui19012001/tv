import os
import datetime
from pathlib import Path
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from supabase import create_client

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="One Page Gerencial — Linhas",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================
# TIMEZONE
# ==============================
TZ = pytz.timezone("America/Sao_Paulo")

# ==============================
# ENV
# ==============================
env_path = Path(__file__).parent / "teste.env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==============================
# CSS GLOBAL
# ==============================
def aplicar_css():

    st.markdown("""
<style>

.block-container{
padding-top:1rem;
padding-bottom:1rem;
max-width:100%;
}

.stApp{
background:#F5F7FB;
}

/* BOTÃO SIDEBAR */
button[data-testid="stSidebarCollapseButton"]{
position:fixed;
top:12px;
left:12px;
z-index:999;
opacity:.6;
}

/* TITULO */
.op-title{
font-size:24px;
font-weight:900;
margin-bottom:4px;
}

.op-sub{
color:#555;
margin-bottom:12px;
}

</style>
""", unsafe_allow_html=True)


# ==============================
# DATA LOAD
# ==============================
def carregar_tabela(nome):

    inicio = 0
    passo = 1000
    dados_total = []

    while True:

        resp = supabase.table(nome).select("*").range(inicio, inicio+passo-1).execute()
        dados = resp.data

        if not dados:
            break

        dados_total.extend(dados)
        inicio += passo

    df = pd.DataFrame(dados_total)

    if not df.empty and "data_hora" in df.columns:
        df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")

    return df


# ==============================
# FILTRO DATA
# ==============================
def filtrar(df, ini, fim):

    if df.empty:
        return df

    df = df[df["data_hora"].notna()]

    return df[(df["data_hora"].dt.date >= ini) & (df["data_hora"].dt.date <= fim)]


# ==============================
# APROVAÇÃO
# ==============================
def calcular_aprovacao(df_checks, df_apont):

    if df_checks.empty or df_apont.empty:
        return 0,0,0

    if "numero_serie" not in df_checks.columns:
        return 0,0,0

    ult = df_checks.sort_values("data_hora").groupby("numero_serie").tail(1)

    total = len(ult)

    if total == 0:
        return 0,0,0

    reprov = ult["status"].astype(str).str.contains("reprov",case=False).sum()

    aprov = total - reprov

    perc = aprov/total*100

    return perc,total,reprov


# ==============================
# RESUMOS
# ==============================
def resumo(df_apont, df_check, nome):

    total = len(df_apont)

    aprov,inspec,rep = calcular_aprovacao(df_check,df_apont)

    atraso = max(50-total,0)

    oee = (aprov/100)*100 if aprov>0 else 0

    return {
        "nome":nome,
        "total":total,
        "aprovacao":aprov,
        "inspecionado":inspec,
        "reprovados":rep,
        "atraso":atraso,
        "status":"Dentro da Meta" if atraso==0 else f"Atraso:{atraso}",
        "oee":oee
    }


# ==============================
# HTML CARDS
# ==============================
def render_cards(resumos):

    HEIGHT = 460

    cards = ""

    for r in resumos:

        cards += f"""

<div class="card">

<div class="head">

<div>
<div class="title">{r['nome']}</div>
<div class="sub">One Page • Produção & Qualidade</div>
</div>

</div>

<div class="gridmini">

<div class="mini">
<div class="mini-title">TOTAL PRODUZIDO</div>
<div class="mini-val">{r['total']}</div>
</div>

<div class="mini">
<div class="mini-title">% APROVAÇÃO</div>
<div class="mini-val">{r['aprovacao']:.1f}%</div>
<div class="mini-foot">Inspecionado:{r['inspecionado']}</div>
</div>

<div class="mini">
<div class="mini-title">STATUS</div>
<div class="mini-val">{r['status']}</div>
</div>

<div class="mini">
<div class="mini-title">OEE</div>
<div class="mini-val">{r['oee']:.1f}%</div>
</div>

</div>

</div>

"""

    html = f"""

<style>

/* container TV */

.wrap {{
width:100%;
max-width:2000px;
margin:auto;
}}

/* GRID PRINCIPAL */

.grid3 {{
display:grid;
grid-template-columns:repeat(3,1fr);
gap:18px;
width:100%;
}}

/* CARD */

.card{{
background:linear-gradient(135deg,#071124,#093A5A);
padding:20px;
border-radius:22px;
height:360px;
color:white;
box-shadow:0 10px 25px rgba(0,0,0,.2);
}}

.head{{
display:flex;
justify-content:space-between;
margin-bottom:10px;
}}

.title{{
font-weight:900;
font-size:14px;
}}

.sub{{
font-size:12px;
opacity:.8;
}}

.gridmini{{
display:grid;
grid-template-columns:1fr 1fr;
gap:12px;
}}

.mini{{
background:rgba(255,255,255,.07);
padding:14px;
border-radius:14px;
}}

.mini-title{{
font-size:11px;
font-weight:900;
margin-bottom:6px;
}}

.mini-val{{
font-size:22px;
font-weight:900;
}}

.mini-foot{{
font-size:11px;
opacity:.7;
}}

@media (max-width:1200px)
{{
.grid3{{grid-template-columns:repeat(2,1fr);}}
}}

@media (max-width:800px)
{{
.grid3{{grid-template-columns:1fr;}}
}}

</style>

<div class="wrap">

<div class="grid3">

{cards}

</div>

</div>

"""

    return html,HEIGHT


# ==============================
# PAGE ONE
# ==============================
def page_one(data_ini,data_fim):

    a_total = filtrar(carregar_tabela("apontamentos"),data_ini,data_fim)
    c_total = filtrar(carregar_tabela("checklists"),data_ini,data_fim)

    a_mola = filtrar(carregar_tabela("apontamentos_mola"),data_ini,data_fim)
    c_mola = filtrar(carregar_tabela("checklists_mola_detalhes"),data_ini,data_fim)

    a_mp = filtrar(carregar_tabela("apontamentos_manga_pnm"),data_ini,data_fim)
    c_mp = filtrar(carregar_tabela("checklists_manga_pnm_detalhes"),data_ini,data_fim)

    resumos=[

        resumo(a_total,c_total,"APONTAMENTOS (TOTAL)"),
        resumo(a_mola,c_mola,"MONTAGEM MOLA"),
        resumo(a_mp,c_mp,"MONTAGEM MANGA & PNM")

    ]

    html,h=render_cards(resumos)

    components.html(html,height=h)


# ==============================
# MAIN
# ==============================
def main():

    aplicar_css()

    hoje=datetime.date.today()

    st.sidebar.markdown("## Menu")

    pagina=st.sidebar.radio("Página",["One Page (TV)"])

    st.sidebar.markdown("### Filtro")

    data_ini=st.sidebar.date_input("Inicio",hoje)
    data_fim=st.sidebar.date_input("Fim",hoje)

    st.markdown("<div class='op-title'>ONE PAGE GERENCIAL — LINHAS</div>",unsafe_allow_html=True)

    st.markdown(f"<div class='op-sub'>Período:{data_ini} até {data_fim}</div>",unsafe_allow_html=True)

    page_one(data_ini,data_fim)


if __name__=="__main__":
    main()
