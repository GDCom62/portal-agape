import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, os, base64

# --- 1. CONFIGURAÇÕES E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e3a8a !important; text-align: center; }
    
    /* Centralização de Imagem via CSS */
    .img-center {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 180px;
    }
    
    /* Estilo dos Cartões Flutuantes */
    .card-flutuante {
        background-color: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 12px;
        border-left: 5px solid #1e3a8a;
    }
    
    /* Estilo da Rádio */
    .radio-box {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 30px; border-radius: 40px; text-align: center; color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///portal_agape_oficial.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN CENTRALIZADO ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_central, _ = st.columns([1, 1.5, 1])
    with col_central:
        if os.path.exists(URL_LOGO):
            # Hack de centralização por Markdown
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{base64.b64encode(open(URL_LOGO, "rb").read()).decode()}" width="200"></p>', unsafe_allow_html=True)
        else:
            st.title("⛪ Portal Ágape")
        
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e = st.text_input("E-mail")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar Novo", use_container_width=True):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastro realizado! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    # Logo Centralizada na Sidebar
    if os.path.exists(URL_LOGO):
        st.sidebar.markdown(f'<p align="center"><img src="data:image/png;base64,{base64.b64encode(open(URL_LOGO, "rb").read()).decode()}" width="120"></p>', unsafe_allow_html=True)
    
    st.sidebar.markdown(f"<p style='text-align: center;'>🙏 Olá, <b>{u['nome']}</b></p>", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📻 Rádio", "🎥 Reunião & Chat", "💰 Financeiro", "📺 Live"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("🚪 Sair", use_container_width=True): 
        st.session_state.logado = False
        st.rerun()

    # --- ÁREA ADMINISTRATIVA ---
    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3, t4 = st.tabs(["📢 Avisos", "📖 Bíblia", "📻 Configs", "💰 Financeiro"])
        
        with t2:
            arq = st.file_uploader("Subir acf.json", type=['json'])
            if arq and st.button("🚀 Importar"):
                dados = json.load(arq)
                for liv in dados:
                    for ic, cap in enumerate(liv.get('chapters', [])):
                        for iv, txt in enumerate(cap):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", 
                                          {"l":liv['name'], "c":ic+1, "v":iv+1, "t":txt})
                st.success("Bíblia Carregada!")

        with t3:
            r_url = st.text_input("URL da Rádio (.mp3)")
            v_id = st.text_input("ID do YouTube")
            if st.button("Salvar Configurações"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :r)", {"r":r_url})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_id', :v)", {"v":v_id})
                st.success("Salvo!")

        with t4:
            with st.form("f_fin", clear_on_submit=True):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Registrar Lançamento"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", 
                                  {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Lançado!")

    # --- ÁREA DO MEMBRO ---
    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            # PALAVRA DO DIA AUTOMÁTICA
            bib = consultar_db("SELECT livro, capitulo, versiculo, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not bib.empty:
                st.markdown(f'<div class="card-flutuante"><h4>✨ Palavra do Dia</h4><b>{bib.iloc[0]["livro"]} {bib.iloc[0]["capitulo"]}:{bib.iloc[0]["versiculo"]}</b><br><i>"{bib.iloc[0]["texto"]}"</i></div>', unsafe_allow_html=True)
            
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, a in avisos.iterrows():
                st.info(f"**{a['titulo']}**: {a['conteudo']}")

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l = st.selectbox("Livro", livros['livro'])
                c = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'])
                for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":c}).iterrows():
                    st.markdown(f'<div class="card-flutuante"><b>{v["versiculo"]}.</b> {v["texto"]}</div>', unsafe_allow_html=True)

        elif menu == "🎥 Reunião & Chat":
            st.title("🎥 Bate-papo e Vídeo")
            st.markdown(f'<iframe src="https://jit.si" allow="camera; microphone; fullscreen; display-capture; autoplay" style="height:600px; width:100%; border-radius:20px; border:0;"></iframe>', unsafe_allow_html=True)

        elif menu == "💰 Financeiro":
            st.title("💰 Transparência Financeira")
            st.table(consultar_db("SELECT descricao as Descrição, valor as Valor, tipo as Tipo, data as Data FROM financeiro"))

        elif menu == "📻 Rádio":
            st.title("📻 Rádio Ágape")
            res = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
            if not res.empty:
                url_radio = res.iloc[0]['valor']
                st.markdown(f'<div class="radio-box"><audio controls autoplay style="width:100%"><source src="{url_radio}" type="audio/mpeg"></audio></div>', unsafe_allow_html=True)

        elif menu == "📺 Live":
            st.title("📺 Transmissão ao Vivo")
            res_live = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_id'")
            if not res_live.empty:
                st.markdown(f'<iframe width="100%" height="500" src="https://youtube.com{res_live.iloc[0]["valor"]}" frameborder="0" allowfullscreen style="border-radius:20px;"></iframe>', unsafe_allow_html=True)
