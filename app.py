import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

URL_CHAT_RAILWAY = "https://railway.app"

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .palavra-destaque { background: #1877f2; color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .chat-container { border-radius: 15px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.2); background: white; }
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
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, mes_ref TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, titulo TEXT, dia_semana TEXT, hora TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN E SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

if not st.session_state.logado:
    aplicar_estilo_facebook()
    if st.session_state.tela == "login":
        st.markdown("<h1 style='color:#1877f2; text-align:center;'>Portal Ágape</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais incorretas.")
        st.button("Criar conta", on_click=lambda: st.session_state.update({"tela": "cadastro"}))
    else:
        st.subheader("Cadastro de Membro")
        with st.form("cad"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:e,:s,0)", {"n":n,"e":em,"s":generate_password_hash(se)})
                st.success("Sucesso! Vá para o login."); st.session_state.tela = "login"; st.rerun()
        st.button("Voltar", on_click=lambda: st.session_state.update({"tela": "login"}))

else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    with st.sidebar:
        st.write(f"👤 **{u['nome']}**")
        menu = st.radio("Menu", ["🏠 Mural", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro", "💬 Chat Online"])
        adm_mode = st.checkbox("⚙️ Administração") if u['is_admin'] else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- ADMINISTRAÇÃO ---
    if adm_mode:
        st.title("⚙️ Painel de Controle")
        tab1, tab2, tab3 = st.tabs(["Mural/Agenda", "Financeiro", "Bíblia/Sistema"])
        
        with tab1:
            with st.form("f_mural"):
                txt = st.text_area("Nova Postagem no Mural")
                if st.form_submit_button("Postar"):
                    executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c, :d)", {"c":txt, "d":datetime.now().strftime("%d/%m %H:%M")}); st.rerun()
            with st.form("f_agenda"):
                ev, dia, hr = st.text_input("Evento"), st.text_input("Dia"), st.text_input("Hora")
                if st.form_submit_button("Agendar"):
                    executar_query("INSERT INTO eventos (titulo, dia_semana, hora) VALUES (:t,:d,:h)", {"t":ev,"d":dia,"h":hr}); st.rerun()
        
        with tab2:
            with st.form("f_fin"):
                desc, val, tipo = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Ativo (Entrada)", "Passivo (Saída)"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, mes_ref) VALUES (:d,:v,:t,:dt,:m)",
                                   {"d":desc,"v":val,"t":tipo,"dt":datetime.now().strftime("%d/%m/%Y"),"m":datetime.now().strftime("%m/%Y")}); st.rerun()

        with tab3:
            if st.button("📖 Carregar acf.json"):
                if os.path.exists("acf.json"):
                    with open("acf.json", "r", encoding="utf-8") as f:
                        for livro in json.load(f):
                            for i, cap in enumerate(livro['chapters']):
                                for j, txt in enumerate(cap):
                                    executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":livro['name'], "c":i+1, "v":j+1, "t":txt})
                    st.success("Bíblia carregada!")

    # --- TELAS DE USUÁRIO ---
    elif menu == "🏠 Mural":
        st.title("Mural Ágape")
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows(): st.markdown(f'<div class="card-post">{p["conteudo"]}<br><small>{p["data"]}</small></div>', unsafe_allow_html=True)
        with col2:
            st.markdown("### 📖 Palavra do Dia")
            p_dia = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_dia.empty:
                st.markdown(f'<div class="palavra-destaque">"{p_dia.iloc[0]["texto"]}"<br><b>{p_dia.iloc[0]["livro"]} {p_dia.iloc[0]["cap"]}:{p_dia.iloc[0]["ver"]}</b></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("Bíblia Sagrada")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if livros.empty: st.warning("Bíblia não carregada pelo Admin.")
        else:
            l_sel = st.selectbox("Livro", livros['livro'])
            caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_sel})
            c_sel = st.selectbox("Capítulo", caps['cap'])
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_sel, "c":c_sel})
            for _, v in versos.iterrows(): st.write(f"**{v['ver']}** {v['texto']}")

    elif menu == "🙏 Orações":
        st.title("Pedidos de Oração")
        with st.form("f_or"):
            ped = st.text_area("Seu pedido")
            if st.form_submit_button("Enviar Pedido"):
                executar_query("INSERT INTO oracoes (nome, pedido, status, data) VALUES (:n,:p,'Pendente',:d)", {"n":u['nome'],"p":ped,"d":datetime.now().strftime("%d/%m")}); st.success("Pedido enviado!")

    elif menu == "🤝 Ofertas":
        st.title("Dízimos e Ofertas")
        st.markdown("""
            <div class="card-post" style="text-align:center;">
                <h3>Contribua via PIX</h3>
                <p>Chave: <b>financeiro@agape.com</b></p>
                <p>Ou aponte a câmera para o QR Code no mural da igreja.</p>
            </div>
        """, unsafe_allow_html=True)

    elif menu == "💰 Financeiro":
        st.title("Transparência Financeira")
        mes = st.selectbox("Mês de Referência", consultar_db("SELECT DISTINCT mes_ref FROM financeiro")['mes_ref'] if not consultar_db("SELECT DISTINCT mes_ref FROM financeiro").empty else [datetime.now().strftime("%m/%Y")])
        df = consultar_db("SELECT * FROM financeiro WHERE mes_ref=:m", {"m":mes})
        if not df.empty:
            st.table(df[['descricao', 'valor', 'tipo', 'data']])
            ativos = df[df['tipo'] == 'Ativo (Entrada)']['valor'].sum()
            passivos = df[df['tipo'] == 'Passivo (Saída)']['valor'].sum()
            st.metric("Saldo do Mês", f"R$ {ativos - passivos:.2f}", f"- R$ {passivos}" if passivos > 0 else "")
        else: st.info("Sem lançamentos para este mês.")

    elif menu == "💬 Chat Online":
        st.markdown(f'<iframe src="{URL_CHAT_RAILWAY}?user={u["nome"]}" width="100%" height="700px" style="border:none;"></iframe>', unsafe_allow_html=True)

    elif menu == "📅 Agenda":
        st.title("Agenda da Semana")
        evs = consultar_db("SELECT * FROM eventos")
        for _, e in evs.iterrows(): st.markdown(f'<div class="card-post"><b>{e["dia_semana"]} às {e["hora"]}</b><br>{e["titulo"]}</div>', unsafe_allow_html=True)
