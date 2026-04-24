import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string
import io

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #ddd; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .codigo-box { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border: 1px dashed #1e88e5; text-align: center; font-size: 20px; font-weight: bold; color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_portal.db", pool_size=10, max_overflow=20)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_nome' not in st.session_state: st.session_state.user_nome = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 4. FUNÇÕES DE APOIO ---
def ocultar_nome(nome):
    partes = nome.split()
    oculto = []
    for p in partes:
        oculto.append(p[0] + "*" * (len(p)-1))
    return " ".join(oculto)

# --- 5. TELA INICIAL ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad, t_trans = st.tabs(["🔐 Entrar", "📝 Novo Cadastro", "📊 Transparência"])
    
    with t_log:
        with st.form("login_agape"):
            u, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": u})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    if res.iloc[0]['ativo'] == 1:
                        st.session_state.update({"logado": True, "user_nome": res.iloc[0]['nome'], "is_admin": bool(res.iloc[0]['is_admin'])})
                        st.rerun()
                    else: st.error("Conta bloqueada.")
                else: st.error("Dados inválidos.")

    with t_cad:
        with st.form("cad"):
            n, e, s1 = st.text_input("Nome Completo"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if n and e and s1:
                    cod = "AG-" + "".join(random.choices(string.digits, k=5))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha) VALUES (:n, :e, :c, :p)",
                                   {"n": n, "e": e, "c": cod, "p": generate_password_hash(s1)})
                    st.markdown(f"<div class='codigo-box'>CADASTRO REALIZADO!<br>Seu código individual é: {cod}</div>", unsafe_allow_html=True)
                    st.warning("⚠️ Guarde este código! Ele será usado para conferir suas ofertas e recuperar sua senha.")

    with t_trans:
        st.subheader("📋 Relação de Membros (Identificação por Código)")
        df_m = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0")
        if not df_m.empty:
            df_m['Nome'] = df_m['nome'].apply(ocultar_nome)
            st.table(df_m[['codigo', 'Nome']].rename(columns={'codigo': 'Código Individual'}))

# --- 6. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 {st.session_state.user_nome}")
    menu = ["🏠 Mural", "📖 Bíblia", "🙏 Orações", "💰 Ofertas"]
    if st.session_state.is_admin: menu.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação", menu)
    
    if escolha == "💰 Ofertas":
        st.title("💰 Dízimos e Ofertas")
        res = consultar_db("SELECT * FROM config_geral LIMIT 1")
        if not res.empty:
            st.info(f"Ao realizar o PIX, use seu código de membro na descrição para conferência.")
            st.success(f"Chave PIX: `{res.iloc[0]['chave_pix']}`")
            if res.iloc[0]['url_qrcode']: st.image(res.iloc[0]['url_qrcode'], width=300)
        
    elif escolha == "⚙️ Administração":
        st.title("⚙️ Administração")
        t1, t2, t3 = st.tabs(["👥 Membros", "💳 Configurar PIX", "💾 Backup"])
        with t1:
            membros = consultar_db("SELECT * FROM membros WHERE is_admin=0")
            for _, m in membros.iterrows():
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{m['nome']}** | Código: `{m['codigo']}`")
                if col_b.button("Excluir", key=f"ex_{m['id']}"):
                    executar_query("DELETE FROM membros WHERE id=:id", {"id": int(m['id'])})
                    st.rerun()
        with t2:
            with st.form("pix"):
                px = st.text_input("Nova Chave PIX")
                qr = st.text_input("URL QR Code")
                if st.form_submit_button("Salvar"):
                    executar_query("DELETE FROM config_geral")
                    executar_query("INSERT INTO config_geral (chave_pix, url_qrcode) VALUES (:p, :q)", {"p":px, "q":qr})
                    st.success("Salvo!")
        with t3:
            if st.button("Gerar Backup Excel"):
                df_b = consultar_db("SELECT * FROM membros")
                towrap = io.BytesIO()
                with pd.ExcelWriter(towrap, engine='xlsxwriter') as wr: df_b.to_excel(wr, index=False)
                st.download_button("📥 Baixar Excel", towrap.getvalue(), "backup_agape.xlsx")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
