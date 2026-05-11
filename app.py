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
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        .chat-container { border-radius: 15px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

# MUDANÇA AQUI: params=None (sem chaves)
def executar_query(sql, params=None):
    if params is None:
        params = {}
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params=None):
    if params is None:
        params = {}
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGICA ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    st.title("Portal Ágape")
    with st.form("login"):
        e = st.text_input("E-mail")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
            if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                st.rerun()
            st.error("Erro no login")
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    menu = st.sidebar.radio("Menu", ["Feed", "Chat Online"])
    
    if menu == "Chat Online":
        st.title("💬 Chat Comunitário")
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=Geral"
        st.markdown(f'<iframe src="{link}" width="100%" height="700px" allow="camera; microphone" style="border:none;"></iframe>', unsafe_allow_html=True)
    else:
        st.write(f"Bem-vindo, {u['nome']}!")
        if st.sidebar.button("Sair"):
            st.session_state.clear()
            st.rerun()
