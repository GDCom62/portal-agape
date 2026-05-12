import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json, redis

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")
URL_CHAT_RAILWAY = "https://chat-agape-production.up.railway.app/"
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    st.error("Erro ao conectar ao Redis.")

def aplicar_estilo():
    st.markdown("""<style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 12px; text-align: center; }
    </style>""", unsafe_allow_html=True)

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
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

if not st.session_state.logado:
    aplicar_estilo()
    if st.session_state.tela == "login":
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    r_db.set(f"online:{res.iloc[0]['nome']}", "online", ex=60)
                    st.rerun()
        st.button("Cadastrar", on_click=lambda: st.session_state.update({"tela": "cadastro"}))
    else:
        with st.form("cad"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Salvar"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:e,:s,0)", {"n":n,"e":em,"s":generate_password_hash(se)})
                st.session_state.update({"tela": "login"}); st.rerun()

else:
    u = st.session_state.user
    r_db.set(f"online:{u['nome']}", "online", ex=60)
    aplicar_estilo()
    with st.sidebar:
        st.write(f"👤 **{u['nome']}**")
        menu = st.radio("Menu", ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"])
        # CORREÇÃO MODO ADMIN:
        adm_mode = False
        if u['is_admin'] == 1:
            st.divider()
            adm_mode = st.checkbox("⚙️ Modo Administrador")
        if st.button("Sair"):
            r_db.delete(f"online:{u['nome']}")
            st.session_state.clear(); st.rerun()

    if adm_mode:
        st.title("⚙️ Administração")
        t1, t2 = st.tabs(["Mural/Agenda", "Financeiro"])
        with t1:
            with st.form("f_adm"):
                msg = st.text_area("Aviso")
                if st.form_submit_button("Postar"):
                    executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c,:d)", {"c":msg, "d":datetime.now().strftime("%d/%m")}); st.rerun()
        with t2:
            with st.form("f_fin"):
                d, v = st.text_input("Desc"), st.number_input("Valor")
                t = st.selectbox("Tipo", ["Ativo (Entrada)", "Passivo (Saída)"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, mes_ref) VALUES (:d,:v,:t,:dt,:m)",
                                   {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m"),"m":datetime.now().strftime("%m/%y")}); st.rerun()
    elif menu == "💬 Chat Online":
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}"
        st.markdown(f'<div style="text-align:center; padding:50px; background:white; border-radius:20px;"><a href="{link}" target="_blank" style="background:#1877f2; color:white; padding:20px 40px; text-decoration:none; border-radius:30px; font-weight:bold;">ABRIR CHAT PREMIUM</a></div>', unsafe_allow_html=True)
    
    elif menu == "🏠 Mural":
        st.title("Mural Ágape")
        posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, p in posts.iterrows(): st.markdown(f'<div class="card-post">{p["conteudo"]}<br><small>{p["data"]}</small></div>', unsafe_allow_html=True)
    
    elif menu == "💰 Financeiro":
        st.title("Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            st.table(df)
            st.metric("Saldo", f"R$ {df[df['tipo'].str.contains('Ativo')]['valor'].sum() - df[df['tipo'].str.contains('Passivo')]['valor'].sum():.2f}")

    # (Adicione elifs para Bíblia, Agenda, Ofertas e Orações conforme códigos anteriores)
