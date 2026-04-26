import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, base64

# --- 1. CONFIGURAÇÃO E LOGO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (v15) ---
engine = create_engine("sqlite:///agape_v15.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS playlist (id INTEGER PRIMARY KEY, nome TEXT, url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. INTERFACE DE LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image(URL_LOGO, use_container_width=True)
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
                    st.error("Email ou senha incorretos.")
        with tab_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastro realizado! Seu código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    try: st.sidebar.image(URL_LOGO, use_container_width=True)
    except: st.sidebar.title("⛪ Portal Ágape")
    
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "🎶 Playlist", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Administrador") if u['is_admin'] == 1 else False
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Admin")
        t1, t2, t3, t4 = st.tabs(["📢 Avisos", "📖 Bíblia", "📺 Live URL", "💰 Financeiro"])
        
        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                if st.form_submit_button("Postar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Aviso postado!")

        with t2:
            st.info("Para a Bíblia funcionar, você precisa importar o arquivo JSON ou cadastrar versículos manualmente via banco.")
            st.write("Em breve: Importador de JSON automático.")

        with t3:
            url_live = st.text_input("URL Incorporada do YouTube (Ex: https://youtube.com)")
            if st.button("Salvar URL da Live"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v": url_live})
                st.success("URL da Live salva!")

        with t4:
            with st.form("f_fin"):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor", 0.0), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Lançado!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural de Avisos")
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, a in avisos.iterrows():
                st.info(f"**{a['titulo']}** ({a['data']})\n\n{a['conteudo']}")

        elif menu == "💰 Financeiro":
            st.title("💰 Transparência Financeira")
            dados = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
            if not dados.empty:
                st.table(dados)
            else: st.write("Nenhum registro financeiro encontrado.")

        elif menu == "📺 Ao Vivo":
            st.title("📺 Culto Online")
            live_res = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
            if not live_res.empty:
                url = live_res.iloc[0]['valor']
                st.video(url)
            else: st.warning("Nenhuma live configurada pelo administrador.")

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia")
            st.write("Selecione o livro e capítulo.")
            # Aqui você faria a busca no banco se a tabela 'biblia' estivesse populada
