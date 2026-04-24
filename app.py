import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Portal Ágape", layout="centered")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///portal_agape_v4.db", pool_pre_ping=True)

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
    
    try:
        check = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
        if check.empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user' not in st.session_state: st.session_state.user = None

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["Login", "Cadastro"])
    
    with t_log:
        with st.form("form_login"):
            email_in = st.text_input("E-mail")
            senha_in = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email_in})
                if not res.empty:
                    u_dict = res.to_dict('records')[0]
                    if check_password_hash(u_dict['senha'], senha_in):
                        st.session_state.logado = True
                        st.session_state.user = u_dict
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("Usuário não encontrado.")

    with t_cad:
        with st.form("form_cadastro"):
            nome_c = st.text_input("Nome Completo")
            email_c = st.text_input("E-mail")
            senha_c = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if nome_c and email_c and senha_c:
                    cod = "AG-" + "".join(random.choices(string.digits, k=4))
                    try:
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": nome_c, "e": email_c, "c": cod, "p": generate_password_hash(senha_c)})
                        st.success(f"Cadastrado! Código: {cod}")
                    except: st.error("E-mail já cadastrado.")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.title(f"Olá, {u['nome']}")
    menu = ["Bíblia", "Mural"]
    if u['is_admin'] == 1: menu.append("Admin")
    escolha = st.sidebar.radio("Navegação", menu)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if escolha == "Admin":
        st.header("⚙️ Importar Bíblia")
        f = st.file_uploader("Selecione o arquivo JSON da Bíblia", type=['json'])
        if f and st.button("Iniciar Importação Inteligente"):
            dados = json.load(f)
            total = len(dados)
            prog = st.progress(0)
            st_txt = st.empty()
            
            for i in range(0, total, 500):
                bloco = dados[i:i+500]
                with engine.begin() as conn:
                    for v in bloco:
                        # Tenta encontrar as chaves corretas no seu arquivo
                        livro = v.get('book') or v.get('nome') or v.get('abbrev') or "Desconhecido"
                        cap = v.get('chapter') or v.get('capitulo') or 0
                        ver = v.get('number') or v.get('versiculo') or 0
                        txt = v.get('text') or v.get('texto') or ""
                        
                        conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)"),
                                     {"l": livro, "c": cap, "v": ver, "t": txt})
                
                prog.progress(min((i+500)/total, 1.0))
                st_txt.text(f"Importando {i+len(bloco)} de {total}...")
            st.success("Bíblia Importada!")

    elif escolha == "Bíblia":
        st.header("📖 Bíblia Sagrada")
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros_df.empty:
            l = st.selectbox("Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l})
            c = st.selectbox("Capítulo", caps_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l, "c": c})
            for _, v in versos.iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.info("Bíblia ainda não importada.")

    elif escolha == "Mural":
        st.header("📢 Mural de Avisos")
        st.write("Bem-vindo!")
