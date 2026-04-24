import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL (Sem temas complexos para não travar) ---
st.set_page_config(page_title="Portal Ágape", layout="centered")

# --- 2. BANCO DE DADOS (USANDO NOVO NOME PARA FORÇAR RESET) ---
engine = create_engine("sqlite:///portal_agape_v3.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('''CREATE TABLE IF NOT EXISTS biblia 
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    
    # Criar Admin inicial
    try:
        check = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
        if check.empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    
    tab_log, tab_cad = st.tabs(["Login", "Cadastro"])
    
    with tab_log:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email})
            if not res.empty:
                u_data = res.iloc[0].to_dict()
                if check_password_hash(u_data['senha'], senha):
                    st.session_state.logado = True
                    st.session_state.user = u_data
                    st.rerun()
                else: st.error("Senha incorreta.")
            else: st.error("Usuário não encontrado.")

    with tab_cad:
        nome_c = st.text_input("Nome Completo")
        email_c = st.text_input("E-mail para cadastro")
        senha_c = st.text_input("Senha para cadastro", type="password")
        if st.button("Cadastrar Novo Membro"):
            if nome_c and email_c and senha_c:
                cod = "AG-" + "".join(random.choices(string.digits, k=4))
                executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                               {"n": nome_c, "e": email_c, "c": cod, "p": generate_password_hash(senha_c)})
                st.success(f"Cadastrado! Código: {cod}")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.title(f"Olá, {u['nome']}")
    
    menu = ["Bíblia", "Mural"]
    if u['is_admin'] == 1:
        menu.append("Admin")
    
    escolha = st.sidebar.radio("Navegação", menu)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if escolha == "Admin":
        st.header("⚙️ Importar Bíblia")
        f = st.file_uploader("Selecione acf.json", type=['json'])
        if f and st.button("Iniciar Importação"):
            dados = json.load(f)
            prog = st.progress(0)
            total = len(dados)
            for i in range(0, total, 500):
                bloco = dados[i:i+500]
                with engine.begin() as conn:
                    for v in bloco:
                        conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)"),
                                     {"l":v['book'], "c":v['chapter'], "v":v['number'], "t":v['text']})
                prog.progress(min((i+500)/total, 1.0))
            st.success("Bíblia Importada com Sucesso!")

    elif escolha == "Bíblia":
        st.header("📖 Bíblia Sagrada")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l})
            c = st.selectbox("Capítulo", caps['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l, "c": c})
            for _, v in versos.iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.info("Bíblia não importada ainda.")

    elif escolha == "Mural":
        st.header("📢 Mural de Avisos")
        st.write("Bem-vindo ao portal da comunidade.")
