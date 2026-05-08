import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, re, unicodedata

# --- CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        .stApp { background-color: #f0f2f5; }
        .card-post { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-bottom: 16px; border: 1px solid #dddfe2; color: black; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .stButton>button { border-radius: 6px !important; }
        </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
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
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, data TEXT)')
    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def importar_biblia_acf():
    if not os.path.exists("acf.json"):
        st.error("Arquivo acf.json não encontrado na pasta raiz!")
        return
    try:
        with open("acf.json", "r", encoding="utf-8") as f:
            biblia_data = json.load(f)
            executar_query("DELETE FROM biblia")
            for livro_dict in biblia_data:
                nome_livro = livro_dict['name']
                for i, capitulo in enumerate(livro_dict['chapters']):
                    num_cap = i + 1
                    for j, texto_verso in enumerate(capitulo):
                        num_ver = j + 1
                        executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l, :c, :v, :t)",
                                       {"l": nome_livro, "c": num_cap, "v": num_ver, "t": texto_verso})
        st.success("Bíblia ACF importada!")
    except Exception as e: st.error(f"Erro: {e}")

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    _, col_c, _ = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<h1 style='color: #1877f2; text-align: center;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais inválidas.")

else:
    u = st.session_state.user
    aplicar_estilo_facebook()

    with st.sidebar:
        st.subheader(f"👤 {u['nome']}")
        menu = st.radio("Menu", ["🏠 Feed", "📖 Bíblia", "👥 Comunhão", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if adm and st.button("📥 Importar acf.json"): importar_biblia_acf()
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    if menu == "🏠 Feed":
        st.title("Feed de Notícias")
        col_f, col_p = st.columns([2, 1])
        with col_f:
            if adm:
                with st.container():
                    st.markdown('<div class="card-post">', unsafe_allow_html=True)
                    with st.form("post", clear_on_submit=True):
                        txt = st.text_area("No que você está pensando?")
                        if st.form_submit_button("Publicar"):
                            executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c, :d)", {"c":txt, "d":datetime.now().strftime("%d/%m %H:%M")})
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows():
                st.markdown(f"<div class='card-post'><b>Igreja Ágape</b><br><small>{p['data']}</small><p>{p['conteudo']}</p></div>", unsafe_allow_html=True)

        with col_p:
            res_b = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_b.empty:
                b = res_b.iloc[0]
                st.markdown(f"<div class='palavra-destaque'><i>'{b['texto']}'</i><br><br><b>{b['livro']} {b['cap']}:{b['ver']}</b></div>", unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        res_l = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not res_l.empty:
            l_sel = st.selectbox("Livro", res_l['livro'].tolist())
            res_c = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap", {"l":l_sel})
            c_sel = st.selectbox("Capítulo", res_c['cap'].tolist())
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver", {"l":l_sel, "c":c_sel})
            for _, v in versos.iterrows(): st.write(f"**{v['ver']}** {v['texto']}")
            st.markdown('</div>', unsafe_allow_html=True)
        else: st.warning("Bíblia vazia. Use o botão Importar no Modo Admin.")

    elif menu == "👥 Comunhão":
        st.title("👥 Comunhão")
        m_list = consultar_db("SELECT nome FROM membros")['nome'].tolist()
        dest = st.selectbox("Conversar com:", [m for m in m_list if m != u['nome']])
        st.link_button(f"🎥 Vídeo Chamada com {dest}", f"https://jit.si{u['id']}_{dest}")
        
        st.divider()
        msgs = consultar_db("SELECT * FROM mensagens WHERE (de_user=:u AND para_user=:d) OR (de_user=:d AND para_user=:u)", {"u":u['nome'], "d":dest})
        for _, m in msgs.iterrows(): st.info(f"**{m['de_user']}**: {m['texto']}")
        with st.form("chat", clear_on_submit=True):
            mtxt = st.text_input("Mensagem")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO mensagens (de_user, para_user, texto, data) VALUES (:u, :d, :t, :dt)", {"u":u['nome'], "d":dest, "t":mtxt, "dt":datetime.now().isoformat()})
                st.rerun()

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        if adm:
            with st.expander("Novo Lançamento"):
                with st.form("f"):
                    desc, val = st.text_input("Descrição"), st.number_input("Valor", 0.0)
                    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                    if st.form_submit_button("Salvar"):
                        executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d, :v, :t, :dt)", {"d":desc, "v":val, "t":tipo, "dt":datetime.now().strftime("%d/%m/%Y")})
                        st.rerun()
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            res_e = df[df['tipo']=='Entrada']['valor'].sum()
            res_s = df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo", f"R$ {res_e - res_s:,.2f}", delta=f"E: {res_e} | S: {res_s}")
