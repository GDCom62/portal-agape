import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64, os

# --- 1. CONFIGURAÇÃO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# Estilos CSS
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e3a8a !important; text-align: center; }
    .versiculo-card { background: white; padding: 20px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 12px; }
    .radio-box { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); padding: 30px; border-radius: 30px; text-align: center; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (v24) ---
engine = create_engine("sqlite:///agape_v24.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        if os.path.exists(URL_LOGO): st.image(URL_LOGO, width=180)
        else: st.title("⛪ Portal Ágape")
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais inválidas.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    if os.path.exists(URL_LOGO): st.sidebar.image(URL_LOGO, width=120)
    
    # MENU COM TODAS AS OPÇÕES
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📻 Rádio Ágape", "🎥 Reunião & Chat", "📺 Ao Vivo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        tab1, tab2, tab3 = st.tabs(["📢 Avisos", "📻 Config Rádio/Live", "💰 Financeiro"])
        with tab2:
            r_url = st.text_input("Link da Rádio (Streaming .mp3)")
            v_id = st.text_input("ID do YouTube (Live)")
            if st.button("Gravar Configurações"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :r)", {"r": r_url})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_id', :v)", {"v": v_id})
                st.success("Salvo!")

    else:
        if menu == "📻 Rádio Ágape":
            st.title("📻 Rádio Ágape")
            res = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
            url = res.iloc[0]['valor'] if not res.empty else ""
            if url:
                st.markdown(f"""
                <div class="radio-box">
                    <h3>No Ar: Louvor e Adoração</h3>
                    <audio controls autoplay style="width: 100%;"><source src="{url}" type="audio/mpeg"></audio>
                </div>
                """, unsafe_allow_html=True)
            else: st.warning("Rádio não configurada no Admin.")

        elif menu == "🎥 Reunião & Chat":
            st.title("🎥 Sala de Reunião e Bate-papo")
            # Sala fixa para a igreja
            st.markdown(f'<iframe src="https://jit.si" allow="camera; microphone; fullscreen; display-capture; autoplay" style="height:650px; width:100%; border-radius:20px; border:0;"></iframe>', unsafe_allow_html=True)

        elif menu == "📢 Mural":
            st.title("📢 Mural")
            # Palavra aleatória
            bib = consultar_db("SELECT livro, capitulo, versiculo, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not bib.empty:
                st.info(f"✨ **Palavra do Dia**: {bib.iloc[0]['livro']} {bib.iloc[0]['capitulo']}:{bib.iloc[0]['versiculo']}\n\n{bib.iloc[0]['texto']}")
            
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="versiculo-card"><b>{a["titulo"]}</b><br>{a["conteudo"]}</div>', unsafe_allow_html=True)
