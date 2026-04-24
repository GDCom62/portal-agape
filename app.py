import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Card da Palavra do Dia - Destaque */
    .palavra-dia-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white !important;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 30px;
        text-align: center;
    }
    .palavra-dia-card h2 { color: white !important; }

    /* Cards do Mural */
    .mural-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border-top: 5px solid #1e3a8a;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Imagens nos avisos */
    .aviso-img {
        width: 100%;
        max-height: 400px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v6.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('''CREATE TABLE IF NOT EXISTS biblia 
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('''CREATE TABLE IF NOT EXISTS avisos 
        (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)''')
    executar_query('''CREATE TABLE IF NOT EXISTS palavra_dia 
        (id INTEGER PRIMARY KEY, versiculo TEXT, referencia TEXT, devocional TEXT)''')
    
    try:
        if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. LOGIN / CADASTRO ---
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.markdown("<h1 style='text-align: center;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
        t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_log:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data}); st.rerun()
                    st.error("Dados incorretos.")
        with t_cad:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                   {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Código: {c}")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    escolha = st.sidebar.radio("Menu", ["📢 Mural Ágape", "📖 Bíblia Sagrada"] + (["⚙️ Admin"] if u['is_admin'] == 1 else []))
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- MURAL COM PALAVRA DO DIA ---
    if escolha == "📢 Mural Ágape":
        # Palavra do Dia (Destaque)
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f"""
                <div class="palavra-dia-card">
                    <h2 style='margin-bottom:0;'>📖 Palavra do Dia</h2>
                    <p style='font-size: 1.4em; font-style: italic; margin-top:10px;'>"{p['versiculo']}"</p>
                    <strong style='font-size: 1.1em;'>— {p['referencia']}</strong>
                    <div style='margin-top:20px; padding-top:15px; border-top: 1px solid rgba(255,255,255,0.2);'>
                        {p['devocional']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<h1>📢 Mural da Comunidade</h1>", unsafe_allow_html=True)
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img_html = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ''
            st.markdown(f"""
                <div class="mural-card">
                    {img_html}
                    <h3 style="margin-top:0;">{r['titulo']}</h3>
                    <p style="color: #475569;">{r['conteudo']}</p>
                    <small style="color: #94a3b8;">📅 {r['data']}</small>
                </div>
            """, unsafe_allow_html=True)

    # --- BÍBLIA ---
    elif escolha == "📖 Bíblia Sagrada":
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros_df.empty:
            c1, c2 = st.columns(2)
            l_sel = c1.selectbox("Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l_sel})
            c_sel = c2.selectbox("Capítulo", caps_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l_sel, "c": c_sel})
            st.markdown(f"### {l_sel} - Capítulo {c_sel}")
            for _, v in versos.iterrows():
                st.markdown(f"<div style='background:white; padding:10px; border-radius:8px; margin-bottom:5px;'><b style='color:#3b82f6;'>{v['versiculo']}</b> {v['texto']}</div>", unsafe_allow_html=True)

    # --- ADMINISTRAÇÃO ---
    elif escolha == "⚙️ Admin":
        st.markdown("<h1>⚙️ Administração</h1>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["✨ Palavra do Dia", "📢 Novo Aviso", "👥 Membros"])
        
        with t1:
            st.subheader("Definir Palavra Diária")
            with st.form("form_pd"):
                v_pd = st.text_area("Versículo")
                r_pd = st.text_input("Referência (Ex: João 3:16)")
                d_pd = st.text_area("Mensagem Devocional/Reflexão")
                if st.form_submit_button("Atualizar Palavra do Dia"):
                    executar_query("INSERT INTO palavra_dia (versiculo, referencia, devocional) VALUES (:v, :r, :d)",
                                   {"v": v_pd, "r": r_pd, "d": d_pd})
                    st.success("Palavra do dia atualizada!")

        with t2:
            st.subheader("Novo Aviso com Imagem")
            with st.form("form_av"):
                tit = st.text_input("Título")
                cont = st.text_area("Mensagem")
                img = st.text_input("Link da Imagem (URL)")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_url) VALUES (:t, :c, :d, :i)",
                                   {"t": tit, "c": cont, "d": datetime.now().strftime("%d/%m/%Y"), "i": img})
                    st.success("Postado!")
