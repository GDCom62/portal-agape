import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")
URL_CHAT_RAILWAY = "https://railway.app"

def aplicar_estilo():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 12px; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params=None):
    if params is None: params = {}
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params=None):
    if params is None: params = {}
    with engine.connect() as conn:
        try: return pd.read_sql_query(text(sql), conn, params=params)
        except: return pd.DataFrame()

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, mes_ref TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, titulo TEXT, dia_semana TEXT, hora TEXT)')
    
    # Bíblia Automática
    if consultar_db("SELECT id FROM biblia LIMIT 1").empty and os.path.exists("acf.json"):
        with open("acf.json", "r", encoding="utf-8") as f:
            for livro in json.load(f):
                for i, cap in enumerate(livro['chapters']):
                    for j, txt in enumerate(cap):
                        executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":livro['name'], "c":i+1, "v":j+1, "t":txt})

    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

if not st.session_state.logado:
    aplicar_estilo()
    if st.session_state.tela == "login":
        st.markdown("<h1 style='color:#1877f2; text-align:center;'>Portal Ágape</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais inválidas.")
        st.button("Criar Conta", on_click=lambda: st.session_state.update({"tela": "cadastro"}))
    else:
        with st.form("cad"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:e,:s,0)", {"n":n,"e":em,"s":generate_password_hash(se)})
                st.session_state.tela = "login"; st.rerun()
        st.button("Voltar", on_click=lambda: st.session_state.update({"tela": "login"}))

else:
    u = st.session_state.user
    aplicar_estilo()
    with st.sidebar:
        st.write(f"👤 **{u['nome']}**")
        menu = st.radio("Menu", ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"])
        adm = st.checkbox("⚙️ Admin") if u['is_admin'] else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    if menu == "💬 Chat Online":
        st.title("💬 Chat Comunitário")
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}"
        st.markdown(f'<div style="text-align:center; padding:50px; background:white; border-radius:20px; border:1px solid #ddd;"><h2>Ambiente Seguro</h2><a href="{link}" target="_blank" style="background:#1877f2; color:white !important; padding:15px 30px; text-decoration:none; border-radius:30px; font-weight:bold; display:inline-block;">ABRIR CHAT AGORA</a></div>', unsafe_allow_html=True)

    elif menu == "🏠 Mural":
        st.title("Mural Ágape")
        c1, c2 = st.columns([0.7, 0.3])
        with c1:
            for _, p in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-post">{p["conteudo"]}<br><small>{p["data"]}</small></div>', unsafe_allow_html=True)
        with c2:
            p_dia = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_dia.empty:
                st.markdown(f'<div class="palavra-destaque">"{p_dia.iloc[0]["texto"]}"<br><b>{p_dia.iloc[0]["livro"]} {p_dia.iloc[0]["cap"]}:{p_dia.iloc[0]["ver"]}</b></div>', unsafe_allow_html=True)
    # (Outros menus omitidos por brevidade, mantendo a estrutura elif...)
