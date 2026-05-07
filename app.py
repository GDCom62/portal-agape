import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, re, unicodedata
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# Estilo Visual Único
st.markdown("""
    <style>
    .stApp { background: #fdfbf0; }
    .bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); font-size: 16px; }
    .mine { background-color: #dcf8c6; align-self: flex-end; border-bottom-right-radius: 2px; }
    .others { background-color: white; align-self: flex-start; border-bottom-left-radius: 2px; }
    .chat-container { display: flex; flex-direction: column; gap: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar(sql, p={}):
    with engine.begin() as conn: conn.execute(text(sql), p)

def consultar(sql, p={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=p)

# Inicializa Tabelas
executar('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
executar('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
executar('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
executar('CREATE TABLE IF NOT EXISTS chat_agape (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, texto TEXT, hora TEXT)')

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("⛪ Bem-vindo ao Portal Ágape")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Entrar", "📝 Criar Conta"])
        with tab1:
            with st.form("l"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar("SELECT * FROM membros WHERE email=:e", {"e":e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Erro no login.")
        with tab2:
            with st.form("c"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    executar("INSERT INTO membros (nome,email,senha,is_admin) VALUES (:n,:e,:s,0)", 
                             {"n":n,"e":em,"s":generate_password_hash(se)})
                    st.success("Conta criada!")

# --- ÁREA LOGADA ---
else:
    u = st.session_state.user
    menu = st.sidebar.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Comunhão"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    if menu == "📢 Mural":
        st.title("📢 Mural da Fé")
        avisos = consultar("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div style="background:white;padding:15px;border-radius:10px;margin-bottom:10px;border:1px solid #ddd"><h3>{av["titulo"]}</h3><p>{av["conteudo"]}</p></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        # Mostra versículo aleatório se o banco não estiver vazio
        try:
            b = consultar("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1").iloc[0]
            st.info(f"**{b['livro']} {b['cap']}:{b['ver']}** - {b['texto']}")
        except: st.warning("Bíblia ainda não carregada no banco.")

    elif menu == "🎥 Comunhão":
        # ATUALIZA O CHAT AUTOMATICAMENTE A CADA 4 SEGUNDOS
        st_autorefresh(interval=4000, key="chat_ref")
        st.title("💬 Comunhão Realtime")
        
        # Exibição das Mensagens
        chat_placeholder = st.container(height=400)
        with chat_placeholder:
            msgs = consultar("SELECT * FROM chat_agape ORDER BY id ASC LIMIT 100")
            for _, m in msgs.iterrows():
                is_mine = m['usuario'] == u['nome']
                align = "flex-end" if is_mine else "flex-start"
                classe = "mine" if is_mine else "others"
                st.markdown(f"""
                    <div style="display: flex; flex-direction: column; align-items: {align};">
                        <div class="bubble {classe}">
                            <small><b>{m['usuario']}</b></small><br>{m['texto']}
                            <br><small style="color:gray; font-size:10px; float:right;">{m['hora']}</small>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        # Envio de Mensagem
        with st.form("f_chat", clear_on_submit=True):
            col_t, col_b = st.columns([0.85, 0.15])
            with col_t: txt = st.text_input("Sua mensagem", label_visibility="collapsed")
            with col_b: env = st.form_submit_button("➤")
            
            if env and txt:
                executar("INSERT INTO chat_agape (usuario, texto, hora) VALUES (:u, :t, :h)",
                         {"u":u['nome'], "t":txt, "h":datetime.now().strftime("%H:%M")})
                st.rerun()

        st.link_button("🎥 ENTRAR EM VÍDEO CHAMADA", "https://jit.si")
