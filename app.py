import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64

# --- 1. CONFIGURAÇÃO E LOGO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (v19) ---
engine = create_engine("sqlite:///agape_v19.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, mensagem TEXT, data TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        try: st.image(URL_LOGO, width=200) # TAMANHO DA LOGO AJUSTADO
        except: st.title("⛪ Portal Ágape")
        tab_l, tab_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with tab_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data}); st.rerun()
                    st.error("Login inválido.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.image(URL_LOGO, width=150) # LOGO MENOR NA LATERAL
    menu = st.sidebar.radio("Menu", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3, t4, t5 = st.tabs(["📢 Avisos", "📖 Bíblia", "📺 Live", "💰 Financeiro", "📜 Palavra do Dia"])

        with t3:
            st.subheader("Configurar Transmissão")
            id_video = st.text_input("Cole apenas o ID do vídeo do YouTube (Ex: jNQXAC9IVRw)")
            if st.button("Salvar Live"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_id', :v)", {"v": id_video})
                st.success("Live atualizada!")

        # ... (Mantendo as outras abas de Admin iguais às anteriores)

    else:
        if menu == "📺 Ao Vivo":
            st.title("📺 Culto Online")
            res = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_id'")
            if not res.empty:
                video_id = res.iloc[0]['valor']
                # LIVE INTERNA USANDO IFRAME (EMBED)
                st.markdown(f"""
                <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 15px;">
                    <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
                    src="https://youtube.com{video_id}" 
                    frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
                    </iframe>
                </div>
                """, unsafe_allow_html=True)
            else: st.warning("Nenhuma live configurada.")

        # ... (Restante do menu: Mural, Bíblia, Financeiro)
