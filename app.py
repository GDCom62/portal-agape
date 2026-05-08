import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, re, unicodedata

# --- 1. CONFIGURAÇÕES E ESTILO FACEBOOK ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        .card-post { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-bottom: 16px; border: 1px solid #dddfe2; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .stButton>button { border-radius: 6px !important; }
        .sidebar-user { text-align: center; padding: 10px; border-bottom: 1px solid #dddfe2; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, data TEXT)')
    # Popula Bíblia caso vazia para não dar erro
    if consultar_db("SELECT * FROM biblia LIMIT 1").empty:
        executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES ('Gênesis', 1, 1, 'No princípio criou Deus o céu e a terra.')")

init_db()

def limpar_link(texto):
    texto = unicodedata.normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', texto)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    _, col_c, _ = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<h1 style='color: #1877f2; text-align: center;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Erro de login.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    aplicar_estilo_facebook()

    with st.sidebar:
        st.markdown(f"<div class='sidebar-user'><h3>🙏 {u['nome']}</h3></div>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["🏠 Feed", "📖 Bíblia", "👥 Comunhão", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- FEED (MURAL) ---
    if menu == "🏠 Feed":
        col_f, col_p = st.columns([2, 1])
        with col_f:
            if adm:
                with st.form("post"):
                    txt = st.text_area("No que está pensando?")
                    if st.form_submit_button("Publicar"):
                        executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c, :d)", {"c":txt, "d":datetime.now().strftime("%d/%m %H:%M")})
                        st.rerun()
            
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows():
                st.markdown(f"<div class='card-post'><b>Igreja Ágape</b> • {p['data']}<p>{p['conteudo']}</p></div>", unsafe_allow_html=True)

        with col_p:
            res_b = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_b.empty:
                b = res_b.iloc[0]
                st.markdown(f"<div class='palavra-destaque'><i>'{b['texto']}'</i><br><br><b>{b['livro']} {b['cap']}:{b['ver']}</b></div>", unsafe_allow_html=True)

    # --- BÍBLIA ---
    elif menu == "📖 Bíblia":
        st.title("📖 Leitura Bíblica")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")['livro'].tolist()
        if livros:
            l_sel = st.selectbox("Livro", livros)
            capitulos = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_sel})['cap'].tolist()
            c_sel = st.selectbox("Capítulo", capitulos)
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver", {"l":l_sel, "c":c_sel})
            for _, v in versos.iterrows():
                st.write(f"**{v['ver']}** {v['texto']}")

    # --- COMUNHÃO (BATE-PAPO E VÍDEO) ---
    elif menu == "👥 Comunhão":
        st.title("👥 Comunhão")
        c1, c2 = st.columns([1, 2])
        with c1:
            membros = consultar_db("SELECT nome FROM membros")['nome'].tolist()
            dest = st.selectbox("Conversar com:", [m for m in membros if m != u['nome']])
            st.link_button("🎥 Iniciar Vídeo Chamada", f"https://jit.si{limpar_link(u['nome'])}")
        
        with c2:
            st.subheader(f"Chat com {dest}")
            msgs = consultar_db("SELECT * FROM mensagens WHERE (de_user=:u AND para_user=:d) OR (de_user=:d AND para_user=:u)", {"u":u['nome'], "d":dest})
            for _, m in msgs.iterrows():
                st.info(f"**{m['de_user']}**: {m['texto']}")
            with st.form("send", clear_on_submit=True):
                m_txt = st.text_input("Mensagem")
                if st.form_submit_button("Enviar"):
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, data) VALUES (:u, :d, :t, :dt)", 
                                   {"u":u['nome'], "d":dest, "t":m_txt, "dt":datetime.now().isoformat()})
                    st.rerun()

    # --- FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Tesouraria")
        if adm:
            with st.expander("Lançar Movimentação"):
                with st.form("fin"):
                    desc = st.text_input("Descrição")
                    val = st.number_input("Valor", min_value=0.0)
                    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                    if st.form_submit_button("Salvar"):
                        executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d, :v, :t, :dt)",
                                       {"d":desc, "v":val, "t":tipo, "dt":datetime.now().strftime("%d/%m/%Y")})
                        st.rerun()
        
        df_fin = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        if not df_fin.empty:
            st.table(df_fin)
            total = df_fin[df_fin['tipo']=='Entrada']['valor'].sum() - df_fin[df_fin['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo em Caixa", f"R$ {total:,.2f}")
        else:
            st.write("Nenhuma movimentação encontrada.")
