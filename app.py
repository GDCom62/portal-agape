import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json, redis

# --- 1. CONFIGURAÇÕES E ESTILO (DESIGN REFORÇADO) ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

URL_CHAT_RAILWAY = "https://chat-agape-production.up.railway.app/"
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    st.error("Erro de conexão Redis.")

def aplicar_estilo():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        p, span, label, .stMarkdown { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; min-width: 250px; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; color: black; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
        .palavra-destaque p { color: white !important; font-size: 22px !important; font-style: italic; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params=None):
    if params is None: params = {}
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params=None):
    if params is None: params = {}
    with engine.connect() as conn:
        try: return pd.read_sql_query(text(sql), conn, params=params)
        except: return pd.DataFrame()

def init_db():
    # Criar tabelas
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, titulo TEXT, dia_semana TEXT, hora TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, mes_ref TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')

    # 1. CARREGAMENTO AUTOMÁTICO DA BÍBLIA (Ajustado)
    if consultar_db("SELECT id FROM biblia LIMIT 1").empty:
        if os.path.exists("acf.json"):
            try:
                with open("acf.json", "r", encoding="utf-8-sig") as f:
                    dados = json.load(f)
                    for livro in dados:
                        for i, cap in enumerate(livro['chapters']):
                            for j, txt in enumerate(cap):
                                executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", 
                                               {"l":livro['name'], "c":i+1, "v":j+1, "t":txt})
                st.toast("📖 Bíblia inicializada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler acf.json: {e}")

    # 2. ADMIN PADRÃO
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGICA DE NAVEGAÇÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

aplicar_estilo() # Aplicado globalmente para não desconfigurar

if not st.session_state.logado:
    if st.session_state.tela == "login":
        st.markdown("<h1 style='color:#1877f2; text-align:center;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Login incorreto.")
        st.button("Criar nova conta", on_click=lambda: st.session_state.update({"tela": "cadastro"}))
    else:
        with st.form("cad_form"):
            st.subheader("Cadastro Ágape")
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:e,:s,0)", {"n":n,"e":em,"s":generate_password_hash(se)})
                st.session_state.update({"tela": "login"}); st.rerun()
        st.button("Voltar", on_click=lambda: st.session_state.update({"tela": "login"}))

else:
    u = st.session_state.user
    r_db.set(f"online:{u['nome']}", "online", ex=60)

    with st.sidebar:
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Menu", ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"])
        adm_mode = st.checkbox("⚙️ Administração") if u['is_admin'] else False
        if st.button("Sair"):
            r_db.delete(f"online:{u['nome']}")
            st.session_state.clear(); st.rerun()

    # --- TELAS ---
    if adm_mode:
        st.title("⚙️ Painel Admin")
        t1, t2 = st.tabs(["Postagens", "Financeiro"])
        with t1:
            with st.form("admin_post"):
                msg = st.text_area("Texto do Aviso")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c,:d)", {"c":msg, "d":datetime.now().strftime("%d/%m %H:%M")}); st.rerun()
        with t2:
            with st.form("admin_fin"):
                d, v = st.text_input("Descrição"), st.number_input("Valor")
                t = st.selectbox("Tipo", ["Ativo (Entrada)", "Passivo (Saída)"])
                if st.form_submit_button("Salvar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, mes_ref) VALUES (:d,:v,:t,:dt,:m)",
                                   {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%y"),"m":datetime.now().strftime("%m/%Y")}); st.rerun()

    elif menu == "🏠 Mural":
        st.title("Mural Ágape")
        col_m, col_p = st.columns([0.7, 0.3])
        with col_m:
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows(): 
                st.markdown(f'<div class="card-post"><b>Igreja Ágape</b><br><small>{p["data"]}</small><p>{p["conteudo"]}</p></div>', unsafe_allow_html=True)
        with col_p:
            st.markdown("### ✨ Palavra do Dia")
            p_dia = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_dia.empty:
                st.markdown(f'<div class="palavra-destaque"><p>"{p_dia.iloc[0]["texto"]}"</p><b>{p_dia.iloc[0]["livro"]} {p_dia.iloc[0]["cap"]}:{p_dia.iloc[0]["ver"]}</b></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("Bíblia Sagrada")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Selecione o Livro", livros['livro'])
            caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l})
            c = st.selectbox("Capítulo", caps['cap'])
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l,"c":c})
            for _, v in versos.iterrows(): st.write(f"**{v['ver']}** {v['texto']}")

    elif menu == "💰 Financeiro":
        st.title("Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            st.table(df[['descricao', 'valor', 'tipo', 'data']])
            ativos = df[df['tipo'].str.contains("Ativo")]['valor'].sum()
            passivos = df[df['tipo'].str.contains("Passivo")]['valor'].sum()
            st.metric("Saldo Atual", f"R$ {ativos - passivos:.2f}", f"Saídas: R$ {passivos}")

    elif menu == "💬 Chat Online":
        st.title("Chat Premium")
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}"
        st.markdown(f'<div style="text-align:center; padding:100px; background:white; border-radius:20px;"><a href="{link}" target="_blank" style="background:#1877f2; color:white; padding:20px 50px; text-decoration:none; border-radius:30px; font-weight:bold; font-size:20px;">ENTRAR NO CHAT</a></div>', unsafe_allow_html=True)

    # (Agenda, Ofertas e Orações podem ser adicionadas seguindo o mesmo padrão elif)
