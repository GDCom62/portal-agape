import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# URL DO SEU CHAT NO RAILWAY
URL_CHAT_RAILWAY = "https://railway.app"

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .chat-container { border-radius: 15px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.2); background: white; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params=None):
    if params is None: params = {}
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params=None):
    if params is None: params = {}
    with engine.connect() as conn: 
        try:
            return pd.read_sql_query(text(sql), conn, params=params)
        except:
            return pd.DataFrame()

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, titulo TEXT, dia_semana TEXT, hora TEXT)')
    # Verifica se Admin existe
    res = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
    if res.empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

# Garante que o banco inicie antes de qualquer coisa
init_db()

# --- 3. ESTADOS DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

# --- 4. TELAS DE LOGIN E CADASTRO ---
if not st.session_state.logado:
    aplicar_estilo_facebook()
    st.markdown("<h1 style='color:#1877f2; text-align:center;'>Portal Ágape</h1>", unsafe_allow_html=True)
    
    if st.session_state.tela == "login":
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("E-mail ou senha incorretos.")
        if st.button("Não tem conta? Cadastre-se aqui"):
            st.session_state.tela = "cadastro"
            st.rerun()

    elif st.session_state.tela == "cadastro":
        with st.form("form_cadastro"):
            st.subheader("Criar Nova Conta")
            n = st.text_input("Nome Completo")
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                if n and em and se:
                    try:
                        pw_hash = generate_password_hash(se)
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, 'MEM-001', :p, 0)", 
                                       {"n":n, "e":em, "p":pw_hash})
                        st.success("Cadastro realizado! Faça login.")
                        st.session_state.tela = "login"
                        st.rerun()
                    except:
                        st.error("E-mail já cadastrado.")
        if st.button("Voltar para o Login"):
            st.session_state.tela = "login"
            st.rerun()

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        st.write(f"👤 **{u['nome']}**")
        menu = st.radio("Navegação", ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"])
        
        adm_mode = False
        if u['is_admin'] == 1:
            st.divider()
            adm_mode = st.checkbox("⚙️ Painel Admin")
        
        if st.button("Sair"): 
            st.session_state.clear()
            st.rerun()

    if adm_mode:
        st.title("⚙️ Painel de Administração")
        st.write("Gerencie membros e conteúdos aqui.")
        membros = consultar_db("SELECT id, nome, email, is_admin FROM membros")
        st.dataframe(membros, use_container_width=True)
        if st.button("Limpar Banco de Dados (Cuidado!)"):
            executar_query("DELETE FROM membros WHERE is_admin=0")
            st.warning("Membros removidos.")

    elif menu == "💬 Chat Online":
        st.title("💬 Chat Ágape")
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=Geral"
        st.markdown(f'<div class="chat-container"><iframe src="{link}" width="100%" height="700px" allow="camera; microphone; display-capture" style="border:none;"></iframe></div>', unsafe_allow_html=True)

    elif menu == "🏠 Mural":
        st.title("Mural da Igreja")
        posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if posts.empty:
            st.info("Nenhum aviso no momento.")
        else:
            for _, p in posts.iterrows():
                st.markdown(f'<div class="card-post"><b>{p["data"]}</b><br>{p["conteudo"]}</div>', unsafe_allow_html=True)
    
    # ... (Os demais menus como Bíblia e Financeiro seguem a mesma lógica)
