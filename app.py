import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64

# --- 1. CONFIGURAÇÃO E LOGO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (v17) ---
engine = create_engine("sqlite:///agape_v17.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image(URL_LOGO, width='stretch')
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
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("Login inválido.")
        with tab_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastrado! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    try: st.sidebar.image(URL_LOGO, width='stretch')
    except: st.sidebar.title("⛪ Ágape")
    
    menu = st.sidebar.radio("Menu", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("Sair"): 
        st.session_state.logado = False
        st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3, t4 = st.tabs(["📢 Avisos", "📖 Bíblia", "📺 Live", "💰 Financeiro"])

        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Mensagem")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")

        with t2:
            st.subheader("Importar Bíblia (JSON)")
            arq = st.file_uploader("Subir acf.json", type=['json'])
            if arq and st.button("🚀 Importar"):
                dados = json.load(arq)
                for livro in dados:
                    nm = livro.get('name')
                    for ic, cap in enumerate(livro.get('chapters', [])):
                        for iv, txt in enumerate(cap):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l":nm, "c":ic+1, "v":iv+1, "t":txt})
                st.success("Bíblia Carregada!")

        with t3:
            link_live = st.text_input("Link Incorporado do YouTube")
            if st.button("Salvar Live"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v": link_live})
                st.success("Link atualizado!")

        with t4:
            with st.form("f_fin", clear_on_submit=True):
                desc, val, tipo = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":desc,"v":val,"t":tipo,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()

    else:
        if menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros_df = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros_df.empty:
                l_sel = st.selectbox("Livro", livros_df['livro'])
                caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_sel})
                c_sel = st.selectbox("Capítulo", caps_df['capitulo'])
                vers = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_sel, "c":c_sel})
                for _, v in vers.iterrows():
                    st.write(f"**{v['versiculo']}.** {v['texto']}")
            else: st.warning("Bíblia vazia. Admin precisa importar o JSON.")

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            df = consultar_db("SELECT descricao as Descrição, valor as Valor, tipo as Tipo, data as Data FROM financeiro ORDER BY id DESC")
            if not df.empty:
                st.dataframe(df, width='stretch')
            else: st.info("Sem registros.")

        elif menu == "📺 Ao Vivo":
            st.title("📺 Transmissão")
            url_res = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
            if not url_res.empty:
                st.video(url_res.iloc[0]['valor'])
            else: st.warning("Sem live configurada.")
            
        elif menu == "📢 Mural":
            st.title("📢 Mural")
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, a in avisos.iterrows():
                with st.expander(f"{a['titulo']} - {a['data']}"):
                    st.write(a['conteudo'])
