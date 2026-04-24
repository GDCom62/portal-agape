import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_portal.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    # Criação das tabelas garantindo a coluna 'ativo'
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('''CREATE TABLE IF NOT EXISTS biblia 
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    
    # Criar Admin inicial se não existir
    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])
    
    with t_log:
        with st.form("login_form"):
            u = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": u})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({
                        "logado": True, 
                        "user_nome": res.iloc[0]['nome'], 
                        "user_email": res.iloc[0]['email'],
                        "is_admin": bool(res.iloc[0]['is_admin'])
                    })
                    st.rerun()
                else: st.error("E-mail ou senha incorretos.")

    with t_cad:
        with st.form("cad_form"):
            n = st.text_input("Nome")
            e = st.text_input("E-mail")
            s1 = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if n and e and s1:
                    # Verifica se e-mail já existe antes de tentar inserir
                    check = consultar_db("SELECT id FROM membros WHERE email=:e", {"e": e})
                    if check.empty:
                        cod = "AG-" + "".join(random.choices(string.digits, k=5))
                        executar_query(
                            "INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                            {"n": n, "e": e, "c": cod, "p": generate_password_hash(s1)}
                        )
                        st.success(f"Cadastrado com sucesso! Seu código: {cod}")
                    else:
                        st.error("Este e-mail já está cadastrado no sistema.")
                else: st.warning("Preencha todos os campos.")

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 {st.session_state.user_nome}")
    menu_options = ["Mural", "Bíblia", "Ofertas"]
    if st.session_state.get('is_admin') or st.session_state.get('user_email') == 'admin@agape.com':
        menu_options.append("Admin")
    
    menu = st.sidebar.radio("Navegação", menu_options)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- PÁGINA ADMIN ---
    if menu == "Admin":
        st.title("⚙️ Administração")
        t_aviso, t_biblia, t_membros = st.tabs(["Avisos/PIX", "📥 Importar Bíblia", "Membros"])
        
        with t_biblia:
            file = st.file_uploader("Upload acf.json", type=['json'])
            if file and st.button("🚀 Iniciar Importação"):
                try:
                    dados = json.load(file)
                    total = len(dados)
                    prog = st.progress(0)
                    for i in range(0, total, 500):
                        bloco = dados[i:i+500]
                        with engine.begin() as conn:
                            for v in bloco:
                                conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)"),
                                             {"l":v['book'], "c":v['chapter'], "v":v['number'], "t":v['text']})
                        prog.progress(min((i+500)/total, 1.0))
                    st.success("Bíblia importada!")
                except Exception as ex: st.error(f"Erro: {ex}")

        with t_membros:
            df_m = consultar_db("SELECT id, nome, email, codigo, ativo FROM membros")
            st.dataframe(df_m, use_container_width=True)

    # --- OUTRAS PÁGINAS (Resumidas) ---
    elif menu == "Mural":
        st.title("📢 Mural")
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            st.info(f"**{r['titulo']}**\n\n{r['conteudo']}")

    elif menu == "Bíblia":
        st.title("📖 Bíblia")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            vers = consultar_db("SELECT * FROM biblia WHERE livro=:l", {"l": l})
            st.dataframe(vers[['capitulo', 'versiculo', 'texto']], hide_index=True)
        else: st.info("Bíblia não importada.")
