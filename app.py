import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, os, base64, re

# --- 1. CONFIGURAÇÕES E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e3a8a !important; text-align: center; }
    .card-flutuante {
        background-color: white; padding: 20px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 8px solid #1e3a8a;
    }
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (v45) ---
engine = create_engine("sqlite:///agape_v45.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS recados (id INTEGER PRIMARY KEY, de_nome TEXT, para_nome TEXT, mensagem TEXT, data TEXT)')
    
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
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        logo_central(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad", clear_on_submit=True):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Minha Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Conta criada! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        logo_central(100)
        st.markdown(f"<p style='text-align: center;'>🙏 Olá, <b>{u['nome']}</b></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo & Vídeo", "💰 Financeiro"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3 = st.tabs(["📢 Mural", "📖 Bíblia", "💰 Financeiro"])
        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                foto = st.file_uploader("Foto", type=['png','jpg','jpeg'])
                if st.form_submit_button("Publicar Aviso"):
                    img_b64 = base64.b64encode(foto.read()).decode() if foto else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_data) VALUES (:t, :c, :d, :i)", 
                                  {"t":tit, "c":cont, "d":datetime.now().strftime("%d/%m/%Y"), "i":img_b64})
                    st.success("Postado!")
        with t2:
            arq = st.file_uploader("Subir acf.json", type=['json'])
            if arq and st.button("🚀 Importar"):
                dados = json.load(arq)
                for liv in dados:
                    for ic, cap in enumerate(liv.get('chapters', [])):
                        for iv, txt in enumerate(cap):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l":liv['name'], "c":ic+1, "v":iv+1, "t":txt})
                st.success("Bíblia Carregada!")
        with t3:
            with st.form("f_fin", clear_on_submit=True):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Lançado!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            bib = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not bib.empty:
                st.markdown(f'<div class="card-flutuante"><h4>✨ Palavra do Dia</h4><b>{bib.iloc[0]["livro"]} {bib.iloc[0]["capitulo"]}:{bib.iloc[0]["versiculo"]}</b><br><i>"{bib.iloc[0]["texto"]}"</i></div>', unsafe_allow_html=True)
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-flutuante"><h3>{a["titulo"]}</h3><small>{a["data"]}</small><br>{a["conteudo"]}</div>', unsafe_allow_html=True)
                if a['img_data']: st.image(f"data:image/png;base64,{a['img_data']}", use_container_width=True)

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            col_filtros, col_texto = st.columns([1, 2])
            livros_df = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros_df.empty:
                with col_filtros:
                    l_sel = st.selectbox("Livro", livros_df['livro'])
                    caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_sel})
                    c_sel = st.selectbox("Capítulo", caps['capitulo'])
                with col_texto:
                    vers = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_sel, "c":c_sel})
                    for _, v in vers.iterrows():
                        st.markdown(f'<div class="card-flutuante"><b>{v["versiculo"]}.</b> {v["texto"]}</div>', unsafe_allow_html=True)
            else: st.info("Bíblia vazia. Importe no Admin.")

        elif menu == "🎥 Bate-papo & Vídeo":
            st.title("🎥 Comunicação")
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :eu", {"eu": u['nome']})
            contato = st.selectbox("Com quem falar?", ["Selecione..."] + list(membros['nome']))
            if contato != "Selecione...":
                t1, t2 = st.tabs(["💬 Chat Escrito", "📽️ Vídeo"])
                with t1:
                    with st.form("f_chat", clear_on_submit=True):
                        msg = st.text_area(f"Escreva para {contato}:")
                        if st.form_submit_button("Enviar"):
                            executar_query("INSERT INTO recados (de_nome, para_nome, mensagem, data) VALUES (:d,:p,:m,:dt)", {"d":u['nome'], "p":contato, "m":msg, "dt":datetime.now().strftime("%H:%M")})
                    rec = consultar_db("SELECT * FROM recados WHERE (para_nome=:eu AND de_nome=:ct) OR (para_nome=:ct AND de_nome=:eu) ORDER BY id DESC", {"eu":u['nome'], "ct":contato})
                    for _, r in rec.iterrows(): st.info(f"**{r['de_nome']}**: {r['mensagem']}")
                with t2:
                    n1 = re.sub(r'\W+', '', u['nome']).lower()[:10]
                    n2 = re.sub(r'\W+', '', contato).lower()[:10]
                    sala_id = f"Agape_{min(n1, n2)}_{max(n1, n2)}"
                    st.link_button("🟢 ABRIR VÍDEO EM TELA CHEIA", f"https://jit.si{sala_id}")
                    st.markdown(f'<iframe src="https://jit.si{sala_id}" allow="camera; microphone; fullscreen" style="height:500px; width:100%; border:0; border-radius:20px;"></iframe>', unsafe_allow_html=True)

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            st.dataframe(consultar_db("SELECT descricao, valor, tipo, data FROM financeiro"), width='stretch')
