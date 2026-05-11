import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

URL_CHAT_RAILWAY = "https://railway.app"

def aplicar_estilo_facebook():
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #f0f2f5; }}
        p, span, label {{ color: #000000 !important; font-size: 18px !important; }}
        [data-testid="stSidebar"] {{ background-color: #1c1e21 !important; }}
        .card-post {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }}
        .chat-container {{ border-radius: 15px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.2); background: white; }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params=None):
    if params is None: params = {}
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params=None):
    if params is None: params = {}
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    st.markdown("<h1 style='color:#1877f2; text-align:center;'>Portal Ágape</h1>", unsafe_allow_html=True)
    with st.form("login"):
        e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
            if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                st.rerun()
            st.error("Login inválido.")
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                img = base64.b64encode(f.read()).decode()
                st.markdown(f'<p align="center"><img src="data:image/png;base64,{img}" width="120"></p>', unsafe_allow_html=True)
        st.write(f"👤 **{u['nome']}**")
        
        # Menu Completo
        opcoes = ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"]
        menu = st.radio("Navegação", opcoes)
        
        # Acesso Exclusivo Admin
        adm = False
        if u['is_admin'] == 1:
            st.divider()
            adm = st.checkbox("⚙️ Painel do Administrador")
        
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- LÓGICA DE TELAS ---
    if adm:
        st.title("⚙️ Gestão Administrativa")
        st.warning("Você está no modo de controle total.")
        # Adicione aqui seus botões de excluir membros, ver logs, etc.

    elif menu == "💬 Chat Online":
        st.title("💬 Chat Ágape")
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=Geral"
        st.markdown(f"""
            <div class="chat-container">
                <iframe src="{link}" width="100%" height="700px" allow="camera; microphone; display-capture" style="border:none;"></iframe>
            </div>
        """, unsafe_allow_html=True)

    elif menu == "🏠 Mural":
        st.title("Mural da Igreja")
        # Exemplo de listagem de posts
        posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, p in posts.iterrows():
            st.markdown(f'<div class="card-post"><b>{p["data"]}</b><br>{p["conteudo"]}</div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        st.info("Consulte os livros e capítulos abaixo.")
        # Seu código da bíblia original entra aqui

    elif menu == "🙏 Orações":
        st.title("🙏 Pedidos de Oração")
        # Seu código de orações original entra aqui

    elif menu == "💰 Financeiro":
        st.title("💰 Gestão Financeira")
        if u['is_admin']:
            st.write("Relatório detalhado de entradas e saídas.")
        else:
            st.error("Acesso restrito ao tesoureiro.")
