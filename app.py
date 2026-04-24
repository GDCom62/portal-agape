import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL (Fundo Sólido) ---
st.set_page_config(page_title="Portal Ágape", layout="wide")

# Força o fundo a ser branco sólido para evitar o efeito transparente
st.markdown("""
    <style>
    .main { background-color: #ffffff !important; }
    div[data-testid="stForm"] { background-color: #f9f9f9 !important; border-radius: 10px; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_final.db", pool_pre_ping=True)

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

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    
    tab_log, tab_cad = st.tabs(["🔐 Login", "📝 Cadastro"])
    
    with tab_log:
        with st.form("login_safe"):
            e = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty:
                    u_data = res.iloc[0].to_dict()
                    if u_data['ativo'] == 0:
                        st.error("Conta bloqueada.")
                    elif check_password_hash(u_data['senha'], s):
                        st.session_state.logado = True
                        st.session_state.user = u_data
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("E-mail não encontrado.")

    with tab_cad:
        with st.form("cad_safe"):
            n = st.text_input("Nome Completo")
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if n and em and se:
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                   {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastrado! Seu código: {c}")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.title(f"🙏 {u['nome']}")
    
    menu_op = ["Mural", "Bíblia", "Ofertas"]
    if u['is_admin'] == 1:
        menu_op.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", menu_op)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if escolha == "⚙️ Admin":
        st.title("⚙️ Administração")
        t_pix, t_bib, t_mem = st.tabs(["Config PIX", "Importar Bíblia", "Gerir Membros"])
        
        with t_bib:
            st.subheader("Importar Bíblia (JSON)")
            f = st.file_uploader("Selecione acf.json", type=['json'])
            if f and st.button("🚀 Iniciar Importação"):
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
                st.success("Concluído!")

        with t_mem:
            df_m = consultar_db("SELECT nome, email, codigo, ativo FROM membros")
            st.dataframe(df_m, use_container_width=True)

    elif escolha == "Bíblia":
        st.title("📖 Bíblia")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l_sel = st.selectbox("Livro", livros['livro'].tolist())
            caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l_sel})
            c_sel = st.selectbox("Capítulo", caps['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l_sel, "c": c_sel})
            for _, v in versos.iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.info("Bíblia não importada.")

    elif escolha == "Mural":
        st.title("📢 Avisos")
        df_av = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if df_av.empty: st.info("Sem avisos.")
        else:
            for _, r in df_av.iterrows():
                st.info(f"**{r['titulo']}**\n\n{r['conteudo']}")
