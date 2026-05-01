import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    # ... (Seu código de login aqui)
    t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
    with t_l:
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
    # (Fim login)

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        tam_fonte = st.select_slider("Tamanho da Letra", options=range(18, 36, 2), value=22) if menu in ["📢 Mural", "📖 Bíblia"] else 18
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    st.markdown(f"""
        <style>
        .stApp {{ background-color: #f8fafc; }}
        .caixa-leitura {{ background: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd; height: 600px; overflow-y: auto; font-size: {tam_fonte}px !important; line-height: 1.7; font-family: serif; color: #1e3a8a !important; }}
        .chat-bubble {{ padding: 12px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }}
        </style>
    """, unsafe_allow_html=True)

    # --- MENU: BÍBLIA ---
    if menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        livros_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        
        if not livros_db.empty:
            col_nav, col_txt = st.columns([0.3, 0.7])
            with col_nav:
                l_sel = st.selectbox("Escolha o Livro", livros_db['livro'])
                caps_db = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap ASC", {"l":l_sel})
                c_sel = st.selectbox("Capítulo", caps_db['cap'])
                versos_db = consultar_db("SELECT ver FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver ASC", {"l":l_sel, "c":c_sel})
                v_sel = st.selectbox("Versículo (Opcional)", ["Ver Capítulo Todo"] + list(versos_db['ver']))
            
            with col_txt:
                query_v = "SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c"
                params_v = {"l":l_sel, "c":c_sel}
                if v_sel != "Ver Capítulo Todo":
                    query_v += " AND ver=:v"
                    params_v["v"] = v_sel
                
                versos = consultar_db(query_v + " ORDER BY ver ASC", params_v)
                texto_html = "".join([f"<p><b>{v['ver']}</b> {v['texto']}</p>" for _, v in versos.iterrows()])
                st.markdown(f'<div class="caixa-leitura">{texto_html}</div>', unsafe_allow_html=True)

    # --- MENU: BATE-PAPO ---
    elif menu == "🎥 Bate-papo":
        st.title("💬 Comunidade em Tempo Real")
        
        # 1. Seleção de para quem enviar
        membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n":u['nome']})
        contato = st.selectbox("Conversar com:", ["Todos"] + list(membros['nome']))
        
        # 2. Exibição das Mensagens
        chat_placeholder = st.container(height=400)
        msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
        with chat_placeholder:
            for _, row in msgs.iterrows():
                is_me = row['de_user'] == u['nome']
                align, color = ("flex-end", "#dcf8c6") if is_me else ("flex-start", "#ffffff")
                st.markdown(f'<div style="display: flex; flex-direction: column; align-items: {align};"><div class="chat-bubble" style="background-color: {color};"><b>{row["de_user"]}</b><br>{row["texto"]}</div></div>', unsafe_allow_html=True)
                if row['anexo_data']:
                    st.download_button(label=f"📁 {row['anexo_nome']}", data=base64.b64decode(row['anexo_data']), file_name=row['anexo_nome'], key=f"chat_{row['id']}")

        # 3. Caixa de Mensagem e Ferramentas (Sempre Visível)
        st.divider()
        with st.form("form_chat", clear_on_submit=True):
            txt_msg = st.text_input("Escreva sua mensagem aqui...")
            col1, col2 = st.columns([0.7, 0.3])
            arq = col1.file_uploader("Anexar Arquivo", type=['pdf','jpg','png','docx'])
            video_call = col2.markdown(f"[🎥 Iniciar Chamada de Vídeo](https://jit.si_{u['nome']})")
            
            if st.form_submit_button("Enviar Mensagem 🚀"):
                b64, nome = "", ""
                if arq:
                    nome = arq.name
                    b64 = base64.b64encode(arq.read()).decode()
                executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_nome, anexo_data, data) VALUES (:d,:p,:t,:an,:ad,:dt)", 
                              {"d":u['nome'], "p":contato, "t":txt_msg, "an":nome, "ad":b64, "dt":datetime.now().strftime("%H:%M")})
                st.rerun()

    # --- MENU: MURAL ---
    elif menu == "📢 Mural":
        st.title("📢 Mural de Avisos")
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div style="background:white; padding:20px; border-radius:15px; border-left:8px solid #1e3a8a; margin-bottom:15px;"><h4>{av["titulo"]}</h4><p style="font-size:20px;">{av["conteudo"]}</p></div>', unsafe_allow_html=True)

    # --- MENU: FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Balanço")
        df = consultar_db("SELECT * FROM financeiro")
        st.dataframe(df, use_container_width=True)
