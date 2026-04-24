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
    # Garante que a tabela tenha todas as colunas necessárias
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('''CREATE TABLE IF NOT EXISTS biblia 
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    
    # Verifica se Admin existe
    admin_check = consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'")
    if admin_check.empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- 4. TELA DE ACESSO (LOGIN) ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])
    
    with t_log:
        with st.form("login_form"):
            u = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": u})
                if not res.empty:
                    # Coleta dados com segurança para evitar travamento iloc
                    usuario_db = res.to_dict('records')[0]
                    if usuario_db['ativo'] == 0:
                        st.error("Sua conta está desativada.")
                    elif check_password_hash(usuario_db['senha'], s):
                        st.session_state.logado = True
                        st.session_state.user_nome = usuario_db['nome']
                        st.session_state.user_email = usuario_db['email']
                        st.session_state.is_admin = bool(usuario_db['is_admin'])
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")

    with t_cad:
        with st.form("cad_form"):
            n = st.text_input("Nome")
            e = st.text_input("E-mail")
            s1 = st.text_input("Senha", type="password")
            if st.form_submit_button("Criar Conta"):
                if n and e and s1:
                    check = consultar_db("SELECT id FROM membros WHERE email=:e", {"e": e})
                    if check.empty:
                        cod = "AG-" + "".join(random.choices(string.digits, k=5))
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": n, "e": e, "c": cod, "p": generate_password_hash(s1)})
                        st.success(f"Cadastrado! Seu código: {cod}")
                    else:
                        st.error("E-mail já cadastrado.")

# --- 5. ÁREA LOGADA (PÓS-LOGIN) ---
else:
    st.sidebar.title(f"🙏 {st.session_state.user_nome}")
    
    menu_opcoes = ["Mural", "Bíblia", "Ofertas"]
    if st.session_state.is_admin:
        menu_opcoes.append("Admin")
    
    menu = st.sidebar.radio("Navegação", menu_opcoes)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if menu == "Mural":
        st.header("📢 Mural de Avisos")
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if avisos.empty:
            st.info("Nenhum aviso disponível.")
        else:
            for _, r in avisos.iterrows():
                st.info(f"**{r['titulo']}**\n\n{r['conteudo']}")

    elif menu == "Admin":
        st.title("⚙️ Painel do Administrador")
        tab1, tab2, tab3 = st.tabs(["Avisos/PIX", "📥 Bíblia", "Membros"])
        
        with tab2:
            st.subheader("Importar arquivo acf.json")
            file = st.file_uploader("Selecione o arquivo", type=['json'])
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
                    st.success("✅ Importação concluída!")
                except Exception as ex:
                    st.error(f"Erro: {ex}")

        with tab3:
            df_m = consultar_db("SELECT id, nome, email, codigo, ativo FROM membros")
            st.dataframe(df_m, use_container_width=True)

    elif menu == "Bíblia":
        st.header("📖 Bíblia Sagrada")
        # Carrega livros disponíveis
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Escolha o Livro", livros['livro'].tolist())
            capitulos = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l})
            c = st.selectbox("Capítulo", capitulos['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l, "c": c})
            for _, v in versos.iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.info("Bíblia ainda não disponível no sistema.")

    elif menu == "Ofertas":
        st.header("💰 Dízimos e Ofertas")
        conf = consultar_db("SELECT * FROM config_geral LIMIT 1")
        if not conf.empty:
            st.success(f"PIX: {conf.iloc[0]['chave_pix']}")
            if conf.iloc[0]['url_qrcode']:
                st.image(conf.iloc[0]['url_qrcode'], width=250)
        else:
            st.warning("Configurações de PIX não encontradas.")
