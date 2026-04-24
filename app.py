import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL (DEVE SER A PRIMEIRA LINHA) ---
st.set_page_config(page_title="Portal Ágape", layout="wide")

# --- 2. BANCO DE DADOS (NOVO ARQUIVO PARA NÃO TRAVAR) ---
# O pool_pre_ping garante que a conexão não "congele"
engine = create_engine("sqlite:///agape_oficial.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

# Inicialização segura das tabelas
def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('''CREATE TABLE IF NOT EXISTS biblia 
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    
    # Criar Admin inicial apenas se não existir
    try:
        check_admin = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
        if check_admin.empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except:
        pass

init_db()

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. INTERFACE DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_login, t_cadastro = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])

    with t_login:
        with st.form("form_acesso"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email})
                if not res.empty:
                    # Pega a primeira linha como um dicionário
                    usuario = res.to_dict('records')[0]
                    if usuario['ativo'] == 0:
                        st.error("Conta desativada.")
                    elif check_password_hash(usuario['senha'], senha):
                        st.session_state.logado = True
                        st.session_state.user = usuario
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")

    with t_cadastro:
        with st.form("form_cad"):
            n = st.text_input("Nome")
            e = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Criar Conta"):
                if n and e and s:
                    cod = "AG-" + "".join(random.choices(string.digits, k=5))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                   {"n": n, "e": e, "c": cod, "p": generate_password_hash(s)})
                    st.success(f"Cadastrado! Código: {cod}")

# --- 5. ÁREA DO MEMBRO (LOGADO) ---
else:
    u = st.session_state.user
    st.sidebar.title(f"🙏 Olá, {u['nome']}")
    
    opcoes = ["Mural", "Bíblia", "Ofertas"]
    if u['is_admin'] == 1:
        opcoes.append("⚙️ Admin")
    
    menu = st.sidebar.radio("Navegação", opcoes)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.session_state.user = None
        st.rerun()

    if menu == "Mural":
        st.header("📢 Avisos")
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if df_a.empty:
            st.info("Nenhum aviso no momento.")
        else:
            for _, r in df_a.iterrows():
                st.info(f"**{r['titulo']}**\n\n{r['conteudo']}")

    elif menu == "Bíblia":
        st.header("📖 Sala de Estudos")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l})
            c = st.selectbox("Capítulo", caps['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l, "c": c})
            for _, v in versos.iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.warning("Bíblia ainda não importada.")

    elif menu == "⚙️ Admin":
        st.title("Administração")
        t_pix, t_biblia = st.tabs(["PIX/Avisos", "Importar Bíblia"])
        
        with t_biblia:
            f = st.file_uploader("Subir acf.json", type=['json'])
            if f and st.button("🚀 Iniciar Importação"):
                dados = json.load(f)
                p = st.progress(0)
                for i in range(0, len(dados), 500):
                    bloco = dados[i:i+500]
                    with engine.begin() as conn:
                        for v in bloco:
                            conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)"),
                                         {"l":v['book'], "c":v['chapter'], "v":v['number'], "t":v['text']})
                    p.progress(min((i+500)/len(dados), 1.0))
                st.success("Bíblia Importada!")

    elif menu == "Ofertas":
        st.header("💰 Dízimos e Ofertas")
        conf = consultar_db("SELECT * FROM config_geral LIMIT 1")
        if not conf.empty:
            st.success(f"Chave PIX: {conf.iloc[0]['chave_pix']}")
