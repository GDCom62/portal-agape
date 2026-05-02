import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io, re

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
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
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t1, t2 = st.tabs(["🔐 Entrar", "📝 Cadastro"])
    with t1:
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais incorretas.")
else:
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    st.markdown("""<style>
        .stApp { background-color: #f8fafc; }
        .card-mural { background: white; padding: 20px; border-radius: 15px; border-left: 10px solid #1e3a8a; margin-bottom: 20px; color: black; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .caixa-leitura { background: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd; font-size: 22px; color: black; }
    </style>""", unsafe_allow_html=True)

    if admin_mode:
        st.title("⚙️ Administração")
        tm, tf = st.tabs(["📢 Mural", "💰 Financeiro"])
        with tm:
            st.subheader("Postar no Mural")
            with st.form("f_mural", clear_on_submit=True):
                t_m, c_m = st.text_input("Título"), st.text_area("Conteúdo")
                f_m = st.file_uploader("Foto", type=['jpg','png','jpeg'])
                if st.form_submit_button("Publicar"):
                    img = base64.b64encode(f_m.read()).decode() if f_m else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t,:c,:i,:d)", {"t":t_m, "c":c_m, "i":img, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")
            st.subheader("🗑️ Apagar Avisos")
            av_list = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, r in av_list.iterrows():
                if st.button(f"Excluir: {r['titulo']}", key=f"del_av_{r['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":r['id']}); st.rerun()
        with tf:
            with st.form("f_fin"):
                d_f, v_f = st.text_input("Descrição"), st.number_input("Valor", min_value=0.0)
                t_f = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d_f, "v":v_f, "t":t_f, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.rerun()
            st.subheader("🗑️ Apagar Lançamentos")
            fin_list = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
            for _, r in fin_list.iterrows():
                if st.button(f"Excluir R$ {r['valor']} - {r['descricao']}", key=f"del_fin_{r['id']}"):
                    executar_query("DELETE FROM financeiro WHERE id=:id", {"id":r['id']}); st.rerun()

    elif menu == "📢 Mural":
        st.title("📢 Mural Ágape")
        # Palavra do Dia Automática
        p_dia = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
        if not p_dia.empty:
            st.info(f"📖 **Palavra do Dia:** \"{p_dia.iloc[0]['texto']}\" ({p_dia.iloc[0]['livro']} {p_dia.iloc[0]['cap']}:{p_dia.iloc[0]['ver']})")
        
        for _, av in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            st.markdown(f'<div class="card-mural"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)
            if av['img_data']: st.image(base64.b64decode(av['img_data']), width=400)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        l_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not l_db.empty:
            c1, c2 = st.columns([0.3, 0.7])
            livro_s = c1.selectbox("Livro", l_db['livro'])
            cap_s = c1.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":livro_s})['cap'])
            txts = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":livro_s, "c":cap_s})
            html = "".join([f"<p><b>{v['ver']}</b> {v['texto']}</p>" for _, v in txts.iterrows()])
            c2.markdown(f'<div class="caixa-leitura">{html}</div>', unsafe_allow_html=True)

    elif menu == "🎥 Bate-papo":
        st.title("💬 Bate-papo & Reunião")
        st.link_button("🎥 ENTRAR NA REUNIÃO DE VÍDEO (JITSI)", "https://jit.si", use_container_width=True)
        st.divider()
        chat_box = st.container(height=400)
        msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
        with chat_box:
            for _, r in msgs.iterrows():
                me = r['de_user'] == u['nome']
                align, cor = ("flex-end", "#dcf8c6") if me else ("flex-start", "#ffffff")
                st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div style="background:{cor}; padding:10px; border-radius:10px; margin-bottom:5px; max-width:80%; color:black; border:1px solid #ddd;"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
        with st.form("f_chat", clear_on_submit=True):
            txt, arq = st.text_input("Mensagem"), st.file_uploader("Anexo")
            if st.form_submit_button("Enviar"):
                b64 = base64.b64encode(arq.read()).decode() if arq else ""
                executar_query("INSERT INTO mensagens (de_user, texto, anexo_data, anexo_nome) VALUES (:d,:t,:ad,:an)", {"d":u['nome'], "t":txt, "ad":b64, "an":arq.name if arq else ""})
                st.rerun()

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo Geral", f"R$ {e-s:,.2f}", delta=e-s)
            st.dataframe(df, use_container_width=True)
