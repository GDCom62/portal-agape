import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64

# --- 1. CONFIGURAÇÃO E LOGO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (v16) ---
engine = create_engine("sqlite:///agape_v16.db", pool_pre_ping=True)

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

# --- 3. LOGIN ---
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
    st.sidebar.image(URL_LOGO) if 'logo' else st.sidebar.title("⛪ Ágape")
    menu = st.sidebar.radio("Menu", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "🎶 Playlist", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3, t4 = st.tabs(["📢 Avisos", "📖 Importar Bíblia", "📺 Live", "💰 Financeiro"])

        with t1:
            with st.form("f_aviso"):
                tit, cont = st.text_input("Título"), st.text_area("Mensagem")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")

        with t2:
            st.subheader("Subir Bíblia (JSON)")
            arquivo_biblia = st.file_uploader("Selecione o arquivo acf.json", type=['json'])
            if arquivo_biblia and st.button("🚀 Iniciar Importação"):
                dados_biblia = json.load(arquivo_biblia)
                for livro in dados_biblia:
                    nome_livro = livro.get('name')
                    for i_cap, capitulo in enumerate(livro.get('chapters', [])):
                        for i_ver, texto_ver in enumerate(capitulo):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", 
                                          {"l":nome_livro, "c":i_cap+1, "v":i_ver+1, "t":texto_ver})
                st.success("Bíblia importada com sucesso!")

        with t3:
            link = st.text_input("Link da Live (YouTube Embed)")
            if st.button("Salvar Live"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v": link})
                st.success("Link atualizado!")

        with t4:
            with st.form("f_fin"):
                desc, val, tipo = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":desc,"v":val,"t":tipo,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Lançado!")

    else:
        if menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l_sel = st.selectbox("Selecione o Livro", livros['livro'])
                caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_sel})
                c_sel = st.selectbox("Capítulo", caps['capitulo'])
                versiculos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_sel, "c":c_sel})
                for _, v in versiculos.iterrows():
                    st.write(f"**{v['versiculo']}.** {v['texto']}")
            else: st.warning("Bíblia ainda não foi importada pelo administrador.")

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            df = consultar_db("SELECT descricao as Descrição, valor as Valor, tipo as Tipo, data as Data FROM financeiro ORDER BY id DESC")
            st.dataframe(df, use_container_width=True) if not df.empty else st.info("Sem registros.")

        elif menu == "📺 Ao Vivo":
            st.title("📺 Transmissão")
            url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
            st.video(url.iloc[0]['valor']) if not url.empty else st.warning("Sem live.")
            
        elif menu == "📢 Mural":
            st.title("📢 Mural")
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.chat_message("assistant").write(f"**{a['titulo']}** - {a['conteudo']}")
