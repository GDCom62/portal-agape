import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# URL DO SEU CHAT NO RAILWAY (Certifique-se que este link está correto)
URL_CHAT_RAILWAY = "https://chat-agape-production.up.railway.app/"

def aplicar_estilo():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 12px; text-align: center; }
        .btn-chat { background: #1877f2; color: white !important; padding: 15px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; }
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
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, mes_ref TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, titulo TEXT, dia_semana TEXT, hora TEXT)')
    
    # CARREGAMENTO AUTOMÁTICO DA BÍBLIA (Correção UTF-8-SIG)
    if consultar_db("SELECT id FROM biblia LIMIT 1").empty and os.path.exists("acf.json"):
        try:
            with open("acf.json", "r", encoding="utf-8-sig") as f:
                dados_biblia = json.load(f)
                for livro in dados_biblia:
                    for i, cap in enumerate(livro['chapters']):
                        for j, txt in enumerate(cap):
                            executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", 
                                           {"l":livro['name'], "c":i+1, "v":j+1, "t":txt})
            st.toast("📖 Bíblia carregada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao carregar Bíblia: {e}")

    # Admin Padrão
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- 3. CONTROLE DE ACESSO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

if not st.session_state.logado:
    aplicar_estilo()
    if st.session_state.tela == "login":
        st.markdown("<h1 style='color:#1877f2; text-align:center;'>Portal Ágape</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais inválidas.")
        st.button("Não tem conta? Cadastre-se", on_click=lambda: st.session_state.update({"tela": "cadastro"}))
    else:
        with st.form("cad"):
            st.subheader("Criar Conta")
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:e,:s,0)", 
                               {"n":n,"e":em,"s":generate_password_hash(se)})
                st.success("Cadastrado! Faça o login."); st.session_state.tela = "login"; st.rerun()
        st.button("Voltar ao Login", on_click=lambda: st.session_state.update({"tela": "login"}))

else:
    u = st.session_state.user
    aplicar_estilo()
    with st.sidebar:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
                st.markdown(f'<p align="center"><img src="data:image/png;base64,{img_data}" width="120"></p>', unsafe_allow_html=True)
        st.write(f"👤 **{u['nome']}**")
        menu = st.radio("Menu", ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- NAVEGAÇÃO ---
    if adm:
        st.title("⚙️ Administração")
        tab1, tab2 = st.tabs(["Postagens", "Financeiro"])
        with tab1:
            with st.form("admin_mural"):
                txt = st.text_area("Novo Aviso")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c,:d)", {"c":txt,"d":datetime.now().strftime("%d/%m")}); st.rerun()
        with tab2:
            with st.form("admin_fin"):
                desc, val = st.text_input("Descrição"), st.number_input("Valor")
                tipo = st.selectbox("Tipo", ["Ativo (Entrada)", "Passivo (Saída)"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, mes_ref) VALUES (:d,:v,:t,:dt,:m)",
                                   {"d":desc,"v":val,"t":tipo,"dt":datetime.now().strftime("%d/%m/%Y"),"m":datetime.now().strftime("%m/%Y")}); st.rerun()

    elif menu == "🏠 Mural":
        st.title("Mural Ágape")
        c1, c2 = st.columns([0.7, 0.3])
        with c1:
            for _, p in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-post">{p["conteudo"]}<br><small>{p["data"]}</small></div>', unsafe_allow_html=True)
        with c2:
            st.markdown("### ✨ Palavra do Dia")
            p_dia = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_dia.empty:
                st.markdown(f'<div class="palavra-destaque">"{p_dia.iloc[0]["texto"]}"<br><br><b>{p_dia.iloc[0]["livro"]} {p_dia.iloc[0]["cap"]}:{p_dia.iloc[0]["ver"]}</b></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("Bíblia Sagrada")
        df_livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if df_livros.empty: st.warning("Bíblia não carregada.")
        else:
            l = st.selectbox("Livro", df_livros['livro'])
            c = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l})['cap'])
            for _, v in consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l,"c":c}).iterrows():
                st.write(f"**{v['ver']}** {v['texto']}")

    elif menu == "💰 Financeiro":
        st.title("Gestão Financeira")
        meses = consultar_db("SELECT DISTINCT mes_ref FROM financeiro")
        if not meses.empty:
            m_sel = st.selectbox("Mês Referência", meses['mes_ref'])
            df = consultar_db("SELECT * FROM financeiro WHERE mes_ref=:m", {"m":m_sel})
            st.table(df[['descricao', 'valor', 'tipo', 'data']])
            ativos = df[df['tipo'] == 'Ativo (Entrada)']['valor'].sum()
            passivos = df[df['tipo'] == 'Passivo (Saída)']['valor'].sum()
            st.metric("Saldo do Mês", f"R$ {ativos - passivos:.2f}", f"- R$ {passivos}")
        else: st.info("Sem dados financeiros.")

    elif menu == "💬 Chat Online":
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}"
        st.markdown(f"""
            <div style="text-align:center; padding:50px; background:white; border-radius:20px; border:1px solid #ddd;">
                <h2>Chat Comunitário</h2>
                <p>Ambiente seguro para conversa e vídeo.</p>
                <a href="{link}" target="_blank" class="btn-chat">ABRIR CHAT AGORA</a>
            </div>
        """, unsafe_allow_html=True)

    elif menu == "🤝 Ofertas":
        st.title("Dízimos e Ofertas")
        st.markdown('<div class="card-post" style="text-align:center;"><h3>PIX: financeiro@agape.com</h3></div>', unsafe_allow_html=True)
