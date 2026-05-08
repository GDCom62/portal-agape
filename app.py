import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, re, unicodedata
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        html, body, [class*="st-"], .stMarkdown { font-family: Arial, Helvetica, sans-serif !important; }
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 20px !important; font-weight: 500 !important; }
        .texto-biblico { font-size: 28px !important; color: #000000 !important; line-height: 1.6 !important; margin-bottom: 15px; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; font-size: 19px !important; }
        .card-post { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 20px; border: 1px solid #ced0d4; color: black !important; }
        h1, h2, h3 { color: #1877f2 !important; font-weight: bold !important; }
        .aviso-urgente { background-color: #fa3e3e; color: white !important; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 2px solid #b30000; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

def exibir_logo(largura=120):
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.sidebar.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<h2 style='text-align:center; color:white;'>⛪ ÁGAPE</h2>", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS E FUNÇÕES ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, urgente INTEGER DEFAULT 0, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, data TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def gerar_pdf(df):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica-Bold", 16); p.drawString(100, 800, "Relatório Financeiro - Portal Ágape")
    p.setFont("Helvetica", 12); y = 750
    for _, row in df.iterrows():
        p.drawString(100, y, f"{row['data']} - {row['descricao']} ({row['tipo']}): R$ {row['valor']:.2f}")
        y -= 20
        if y < 50: p.showPage(); y = 800
    p.save(); buffer.seek(0)
    return buffer

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h1 style='text-align:center;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("entrar"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Dados incorretos.")
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        exibir_logo()
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Navegação", ["🏠 Feed", "📖 Bíblia", "👥 Comunhão", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if adm and st.button("📥 Importar acf.json"):
            with open("acf.json", "r", encoding="utf-8") as f:
                data = json.load(f); executar_query("DELETE FROM biblia")
                for livro in data:
                    for i, cap in enumerate(livro['chapters']):
                        for j, texto in enumerate(cap):
                            executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l, :c, :v, :t)", {"l": livro['name'], "c": i+1, "v": j+1, "t": texto})
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- AVISO URGENTE (TOPO) ---
    avisos_urgentes = consultar_db("SELECT * FROM avisos WHERE urgente=1 ORDER BY id DESC LIMIT 1")
    if not avisos_urgentes.empty:
        st.markdown(f'<div class="aviso-urgente">🚨 AVISO IMPORTANTE: {avisos_urgentes.iloc[0]["conteudo"]}</div>', unsafe_allow_html=True)

    # --- LÓGICA DOS MENUS ---
    if menu == "🏠 Feed":
        col_f, col_d = st.columns([2, 1])
        with col_f:
            if adm:
                with st.form("post_form", clear_on_submit=True):
                    txt = st.text_area("No que está pensando?")
                    urg = st.checkbox("Marcar como Urgente (Fica no topo)")
                    if st.form_submit_button("Publicar"):
                        executar_query("INSERT INTO avisos (conteudo, urgente, data) VALUES (:c, :u, :d)", {"c":txt, "u":1 if urg else 0, "d":datetime.now().strftime("%d/%m/%Y %H:%M")}); st.rerun()
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows():
                st.markdown(f"<div class='card-post'><b>Igreja Ágape</b> • {p['data']}<p>{p['conteudo']}</p></div>", unsafe_allow_html=True)
                if adm:
                    if st.button(f"🗑️ Excluir Post #{p['id']}", key=f"del_{p['id']}"):
                        executar_query("DELETE FROM avisos WHERE id=:id", {"id": p['id']}); st.rerun()
        with col_d:
            res_b = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_b.empty:
                b = res_b.iloc[0]
                st.markdown(f'<div class="palavra-destaque"><small>PALAVRA DO DIA</small><br><i>"{b["texto"]}"</i><br><b>{b["livro"]} {b["cap"]}:{b["ver"]}</b></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        res_l = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not res_l.empty:
            l_sel = st.selectbox("Livro", res_l['livro'].tolist())
            res_c = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap", {"l":l_sel})
            c_sel = st.selectbox("Capítulo", res_c['cap'].tolist())
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver", {"l":l_sel, "c":c_sel})
            for _, v in versos.iterrows(): st.markdown(f'<p class="texto-biblico"><b>{v["ver"]}</b> {v["texto"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        if adm:
            with st.expander("➕ Novo Lançamento / Editar"):
                with st.form("fin_form"):
                    id_ed = st.number_input("ID para editar (0 para novo)", min_value=0, step=1)
                    desc = st.text_input("Descrição")
                    val = st.number_input("Valor", 0.0)
                    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                    if st.form_submit_button("Salvar / Alterar"):
                        if id_ed == 0:
                            executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":desc,"v":val,"t":tipo,"dt":datetime.now().strftime("%d/%m/%Y")})
                        else:
                            executar_query("UPDATE financeiro SET descricao=:d, valor=:v, tipo=:t WHERE id=:id", {"d":desc,"v":val,"t":tipo,"id":id_ed})
                        st.rerun()

        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            if adm:
                col_id, col_btn = st.columns([1, 4])
                id_del = col_id.number_input("ID para excluir", min_value=1, step=1, key="del_fin_id")
                if col_btn.button("🗑️ Remover Lançamento Selecionado"):
                    executar_query("DELETE FROM financeiro WHERE id=:id", {"id":id_del}); st.rerun()
            pdf = gerar_pdf(df); st.download_button("📥 Baixar PDF", pdf, "financeiro.pdf", "application/pdf")
            e = df[df['tipo']=='Entrada']['valor'].sum(); s = df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo", f"R$ {e-s:,.2f}", f"E: {e} | S: {s}")
