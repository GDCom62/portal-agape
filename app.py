import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import redis, random

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")
URL_CHAT_RAILWAY = "https://railway.app" # Verifique se esta é sua URL real
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    st.error("Erro ao conectar ao Redis.")

# --- ESTILOS ---
def aplicar_estilo():
    st.markdown("""<style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #1c1e21 !important; font-size: 16px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 5px; border: 1px solid #ced0d4; }
        .floating-louvor { position: fixed; bottom: 25px; right: 25px; width: 300px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-left: 6px solid #1877f2; border-radius: 12px; padding: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); z-index: 999999; }
    </style>""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)
def executar_query(sql, params=None):
    with engine.begin() as conn: conn.execute(text(sql), params or {})
def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: return pd.read_sql_query(text(sql), conn, params=params or {})
        except: return pd.DataFrame()

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT, autor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS curtidas (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT, texto TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- LÓGICA DE COMPONENTES ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        df = consultar_db("SELECT * FROM biblia")
        st.session_state.versiculo_dia = df.sample(1).iloc[0] if not df.empty else {"texto":"Deus é amor","livro":"1 João","cap":4,"ver":8}
    v = st.session_state.versiculo_dia
    st.markdown(f'<div class="floating-louvor"><small style="color:#1877f2;font-weight:bold">PALAVRA DE VIDA</small><br><i>"{v["texto"]}"</i><br><div style="text-align:right"><b>{v["livro"]} {v["cap"]}:{v["ver"]}</b></div></div>', unsafe_allow_html=True)

def verificar_notificacoes():
    n = r_db.get("ultima_notificacao")
    if n: st.toast(n, icon="📢")

# --- APP ---
if 'logado' not in st.session_state: st.session_state.logado = False
aplicar_estilo()

if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    with st.form("login"):
        e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
            if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                st.rerun()
else:
    u = st.session_state.user
    r_db.set(f"online:{u['nome']}", "online", ex=60)
    verificar_notificacoes()
    render_louvor()

    with st.sidebar:
        st.write(f"👤 **{u['nome']}**")
        qtd_on = len(r_db.keys("online:*"))
        st.success(f"● {qtd_on} Irmãos Online")
        menu = st.radio("Menu", ["🏠 Mural", "💬 Chat Ágape"])
        if st.button("Sair"):
            r_db.delete(f"online:{u['nome']}")
            st.session_state.clear(); st.rerun()

    if menu == "💬 Chat Ágape":
        st.components.v1.iframe(f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=agape_oficial", height=700)
    else:
        st.title("🏠 Mural da Comunidade")
        with st.expander("📢 Nova Postagem"):
            msg = st.text_area("O que Deus colocou no seu coração?")
            if st.button("Publicar"):
                executar_query("INSERT INTO avisos (conteudo, data, autor) VALUES (:c,:d,:a)", {"c":msg,"d":datetime.now().strftime("%H:%M"),"a":u['nome']})
                r_db.set("ultima_notificacao", f"Novo post de {u['nome']}", ex=10)
                st.rerun()

        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-post"><b>@{av["autor"]}</b> • <small>{av["data"]}</small><p>{av["conteudo"]}</p></div>', unsafe_allow_html=True)
            col1, col2 = st.columns([0.2, 0.8])
            if u['is_admin'] and col1.button("🗑️", key=f"del_{av['id']}"):
                executar_query("DELETE FROM avisos WHERE id=:id", {"id":av['id']})
                st.rerun()
