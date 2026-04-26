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
    
    /* Cartões Flutuantes */
    .card-flutuante {
        background-color: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 12px;
        border-left: 8px solid #1e3a8a;
    }
    .versiculo-card {
        background-color: white; padding: 15px 20px; border-radius: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 10px;
        border: 1px solid #eef2ff;
        transition: transform 0.2s;
    }
    .versiculo-card:hover { transform: translateY(-3px); }
    
    /* Notificação Vermelha */
    .notif-bola {
        color: white; background-color: #ef4444; padding: 2px 8px;
        border-radius: 50%; font-size: 0.8em; margin-left: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///portal_agape_final_v27.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS recados (id INTEGER PRIMARY KEY, de_nome TEXT, para_nome TEXT, mensagem TEXT, data TEXT, lido INTEGER DEFAULT 0)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def logo_central(largura):
    if os.path.exists(URL_LOGO):
        with open(URL_LOGO, "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_central, _ = st.columns([1, 1.5, 1])
    with col_central:
        logo_central(200)
        tab_l, tab_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with tab_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with tab_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar", use_container_width=True):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Sucesso! Seu código é {c}. Faça login agora.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    
    # Notificação de Recados
    res_n = consultar_db("SELECT COUNT(*) as total FROM recados WHERE para_nome = :eu AND lido = 0", {"eu": u['nome']})
    n_lidos = res_n.iloc[0]['total']
    label_chat = f"🎥 Bate-papo {'🔴' if n_lidos > 0 else ''}"

    with st.sidebar:
        logo_central(120)
        st.markdown(f"<p style='text-align: center;'>🙏 Olá, <b>{u['nome']}</b></p>", unsafe_allow_html=True)
        menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", label_chat, "💰 Financeiro"])
        admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.sidebar.button("Sair", use_container_width=True): 
            st.session_state.logado = False
            st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3 = st.tabs(["📢 Mural", "📖 Bíblia", "💰 Financeiro"])
        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                if st.form_submit_button("Postar Aviso"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")
        with t2:
            arq = st.file_uploader("Subir arquivo acf.json", type=['json'])
            if arq and st.button("🚀 Importar"):
                dados = json.load(arq)
                for liv in dados:
                    for ic, cap in enumerate(liv.get('chapters', [])):
                        for iv, txt in enumerate(cap):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l":liv['name'], "c":ic+1, "v":iv+1, "t":txt})
                st.success("Bíblia Importada!")
        with t3:
            with st.form("f_fin", clear_on_submit=True):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Registrar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Lançado!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            bib = consultar_db("SELECT livro, capitulo, versiculo, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not bib.empty:
                st.markdown(f'<div class="card-flutuante"><h4>✨ Palavra do Dia</h4><b>{bib.iloc[0]["livro"]} {bib.iloc[0]["capitulo"]}:{bib.iloc[0]["versiculo"]}</b><br><i>"{bib.iloc[0]["texto"]}"</i></div>', unsafe_allow_html=True)
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-flutuante"><b>📌 {a["titulo"]}</b><br><small>{a["data"]}</small><br>{a["conteudo"]}</div>', unsafe_allow_html=True)

        elif menu == label_chat:
            st.title("🎥 Bate-papo & Vídeo Chamada")
            executar_query("UPDATE recados SET lido = 1 WHERE para_nome = :eu", {"eu": u['nome']})
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :eu", {"eu": u['nome']})
            contato = st.selectbox("Escolha um membro para conversar:", ["Selecione..."] + list(membros['nome']))
            
            if contato != "Selecione...":
                t_msg, t_vid = st.tabs(["💬 Mensagem", "📽️ Vídeo"])
                with t_msg:
                    with st.form("f_msg", clear_on_submit=True):
                        txt = st.text_area(f"Recado para {contato}:")
                        if st.form_submit_button("Enviar"):
                            executar_query("INSERT INTO recados (de_nome, para_nome, mensagem, data) VALUES (:d,:p,:m,:dt)", {"d":u['nome'], "p":contato, "m":txt, "dt":datetime.now().strftime("%H:%M")})
                            st.success("Enviado!")
                with t_vid:
                    n_sala = sorted([u['nome'], contato])
                    sala_id = f"Agape_{n_sala[0]}_{n_sala[1]}".replace(" ", "")
                    st.markdown(f'<iframe src="https://jit.si{sala_id}" allow="camera; microphone; fullscreen; display-capture; autoplay" style="height:600px; width:100%; border-radius:20px; border:0;"></iframe>', unsafe_allow_html=True)

            st.divider()
            st.subheader("📩 Recados Recebidos")
            recados = consultar_db("SELECT * FROM recados WHERE para_nome = :eu ORDER BY id DESC", {"eu": u['nome']})
            for _, r in recados.iterrows():
                st.warning(f"**De: {r['de_nome']}** ({r['data']}): {r['mensagem']}")

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l_s = st.selectbox("Livro", livros['livro'])
                c_s = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_s})['capitulo'])
                for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_s, "c":c_s}).iterrows():
                    st.markdown(f'<div class="versiculo-card"><span style="color:#1e3a8a;font-weight:bold;">{v["versiculo"]}</span> {v["texto"]}</div>', unsafe_allow_html=True)

        elif menu == "💰 Financeiro":
            st.title("💰 Transparência Financeira")
            df = consultar_db("SELECT descricao as Descrição, valor as Valor, tipo as Tipo, data as Data FROM financeiro")
            st.table(df)
