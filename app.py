import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json

# --- 1. CONFIGURAÇÃO E LOGO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_final.db", pool_pre_ping=True)

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
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, mensagem TEXT, data TEXT)')
    
    # Criar Admin Padrão caso não exista
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image(URL_LOGO, width=180) 
        except: st.title("⛪ Portal Ágape")
        
        tab_l, tab_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with tab_l:
            with st.form("login"):
                e = st.text_input("E-mail")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("E-mail ou senha incorretos.")
        with tab_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastro realizado! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.image(URL_LOGO, width=120)
    st.sidebar.write(f"🙏 **{u['nome']}**")
    
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("🚪 Sair"): 
        st.session_state.logado = False
        st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3, t4, t5 = st.tabs(["📢 Avisos", "📖 Bíblia", "📺 Live", "💰 Financeiro", "📜 Palavra do Dia"])

        with t1:
            with st.form("f_aviso"):
                tit, cont = st.text_input("Título"), st.text_area("Mensagem")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")

        with t3:
            vid_id = st.text_input("ID do Vídeo YouTube (Ex: jNQXAC9IVRw)")
            if st.button("Salvar Live"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_id', :v)", {"v": vid_id})
                st.success("Live salva!")

        with t4:
            with st.form("f_fin"):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Lançado!")

        with t5:
            with st.form("f_pal"):
                v, m = st.text_input("Versículo"), st.text_area("Mensagem")
                if st.form_submit_button("Atualizar"):
                    executar_query("DELETE FROM palavra_dia")
                    executar_query("INSERT INTO palavra_dia (versiculo, mensagem, data) VALUES (:v,:m,:d)", {"v":v,"m":m,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Atualizada!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            palavra = consultar_db("SELECT * FROM palavra_dia LIMIT 1")
            if not palavra.empty:
                st.info(f"📖 **Palavra do Dia: {palavra.iloc[0]['versiculo']}**\n\n{palavra.iloc[0]['mensagem']}")
            
            st.divider()
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, a in avisos.iterrows():
                with st.expander(f"📌 {a['titulo']} - {a['data']}"):
                    st.write(a['conteudo'])

        elif menu == "📺 Ao Vivo":
            res = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_id'")
            if not res.empty:
                v_id = res.iloc[0]['valor']
                st.markdown(f'<iframe width="100%" height="500" src="https://youtube.com{v_id}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
            else: st.warning("Sem live.")

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            df = consultar_db("SELECT descricao, valor, tipo, data FROM financeiro")
            st.dataframe(df, width='stretch')

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia")
            st.info("Admin, faça o upload do JSON na aba Bíblia do Painel Admin.")
