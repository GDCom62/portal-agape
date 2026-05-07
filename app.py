import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, re, unicodedata
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_divino(tam_fonte):
    st.markdown(f"""
        <style>
        .stApp {{ background: #fdfbf0; }}
        h1, h2, h3 {{ color: #b8860b !important; text-align: center; font-weight: bold; font-family: 'Georgia', serif; }}
        p, span, label, li, .stMarkdown, .stSelectbox label {{ color: #000000 !important; font-weight: 600 !important; }}
        .card-mural {{ background: white; padding: 20px; border-radius: 15px; border: 2px solid #ffd700; margin-bottom: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .palavra-do-dia {{ background: #fff3ad; padding: 30px; border-radius: 20px; border: 3px double #b8860b; text-align: center; margin-bottom: 30px; }}
        .caixa-leitura {{ background: white; padding: 30px; border-radius: 10px; border: 2px solid #b8860b; font-size: {tam_fonte}px !important; line-height: 1.7; color: black !important; font-family: serif; }}
        /* Estilo Balões Chat */
        .bubble {{ padding: 10px 15px; border-radius: 15px; max-width: 80%; margin-bottom: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }}
        .mine {{ background-color: #dcf8c6; border-bottom-right-radius: 2px; }}
        .others {{ background-color: white; border-bottom-left-radius: 2px; }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (SQLite Local) ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS chat_agape (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, texto TEXT, anexo_data TEXT, anexo_nome TEXT, hora TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def exibir_logo(largura=150):
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)
    else: st.markdown(f'<h1 style="text-align:center; color:#b8860b; margin:0;">⛪ ÁGAPE</h1>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_divino(22)
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        exibir_logo(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Criada! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        exibir_logo(80)
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Comunhão", "💰 Tesouraria"])
        tam_fonte = st.select_slider("Tamanho Fonte", options=range(18, 48, 2), value=24)
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    aplicar_estilo_divino(tam_fonte)

    if menu == "📢 Mural":
        st.title("📢 Mural da Fé")
        if admin_mode:
            with st.expander("➕ Novo Aviso"):
                with st.form("f_mural", clear_on_submit=True):
                    tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                    foto = st.file_uploader("Foto", type=['jpg','png','jpeg'])
                    if st.form_submit_button("Publicar"):
                        img = base64.b64encode(foto.read()).decode() if foto else ""
                        executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t,:c,:i,:d)", {"t":tit,"c":cont,"i":img,"d":datetime.now().strftime("%d/%m/%Y")})
                        st.rerun()
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-mural"><h3>{av["titulo"]}</h3><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)
            if av['img_data']: st.image(base64.b64decode(av['img_data']), width=300)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        livros_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros_db.empty:
            livro = st.selectbox("Livro", livros_db['livro'].tolist())
            caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":livro})['cap'].tolist()
            cap = st.selectbox("Capítulo", caps)
            vers = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":livro,"c":cap})
            texto_formatado = " ".join([f"<sup>{v['ver']}</sup> {v['texto']}" for _,v in vers.iterrows()])
            st.markdown(f'<div class="caixa-leitura">{texto_formatado}</div>', unsafe_allow_html=True)

    elif menu == "🎥 Comunhão":
        st_autorefresh(interval=4000, key="chat_refresh")
        st.title("💬 Comunhão & Bate-papo")
        
        c_vid, c_chat = st.columns([0.4, 0.6])
        with c_vid:
            st.subheader("📹 Vídeo Chamada")
            st.link_button("🎥 ENTRAR NA CÂMERA", "https://jit.si", use_container_width=True)
            st.divider()
            # Sorteio de Versículo
            p = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p.empty:
                st.info(f"📖 {p.iloc[0]['livro']} {p.iloc[0]['cap']}:{p.iloc[0]['ver']}\n\n\"{p.iloc[0]['texto']}\"")

        with c_chat:
            chat_box = st.container(height=400)
            with chat_box:
                msgs = consultar_db("SELECT * FROM chat_agape ORDER BY id ASC LIMIT 50")
                for _, m in msgs.iterrows():
                    is_mine = m['usuario'] == u['nome']
                    align = "flex-end" if is_mine else "flex-start"
                    classe = "mine" if is_mine else "others"
                    st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};">'
                                f'<div class="bubble {classe}">'
                                f'<small><b>{m["usuario"]}</b></small><br>{m["texto"]}'
                                f'{f"<br><small>📁 {m["anexo_nome"]}</small>" if m["anexo_data"] else ""}'
                                f'<br><small style="color:gray; font-size:10px; float:right;">{m["hora"]}</small>'
                                f'</div></div>', unsafe_allow_html=True)

            with st.form("f_chat", clear_on_submit=True):
                txt = st.text_input("Mensagem")
                arq = st.file_uploader("Anexo", type=['jpg','png','pdf'], label_visibility="collapsed")
                if st.form_submit_button("Enviar ➤"):
                    if txt or arq:
                        b64, nome = ("", "") if not arq else (base64.b64encode(arq.read()).decode(), arq.name)
                        executar_query("INSERT INTO chat_agape (usuario, texto, anexo_data, anexo_nome, hora) VALUES (:u,:t,:d,:n,:h)",
                                       {"u":u['nome'], "t":txt, "d":b64, "n":nome, "h":datetime.now().strftime("%H:%M")})
                        st.rerun()

    elif menu == "💰 Tesouraria":
        st.title("💰 Tesouraria")
        if admin_mode:
            with st.form("f_fin"):
                d, v = st.text_input("Descrição"), st.number_input("Valor", min_value=0.0)
                t = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
        
        fin = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        st.table(fin)
