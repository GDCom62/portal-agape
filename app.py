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
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def exibir_logo(largura=150):
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)
    else: st.markdown(f'<h1 style="text-align:center; color:#1e3a8a;">⛪ ÁGAPE</h1>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        exibir_logo(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Erro no login.")
        with t_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Criado! Cód: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        exibir_logo(80)
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        tam_fonte = st.select_slider("Fonte", options=range(18, 40, 2), value=22)
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # CSS DE ALTO CONTRASTE
    st.markdown(f"""<style>
        .stApp {{ background-color: #f0f2f6; }}
        .caixa-leitura {{ background: white; padding: 25px; border-radius: 10px; border: 2px solid #1e3a8a; color: black !important; font-size: {tam_fonte}px !important; }}
        .card-mural {{ background: white; padding: 20px; border-radius: 15px; border-left: 10px solid #1e3a8a; margin-bottom: 15px; color: black !important; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .chat-bubble {{ padding: 12px; border-radius: 15px; margin-bottom: 8px; color: black !important; border: 1px solid #ddd; font-weight: 500; }}
    </style>""", unsafe_allow_html=True)

    if admin_mode:
        st.title("⚙️ Administração")
        t1, t2 = st.tabs(["📢 Mural", "💰 Financeiro"])
        with t1:
            with st.form("add_mural"):
                tit, cont = st.text_input("Título"), st.text_area("Mensagem")
                if st.form_submit_button("Postar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit, "c":cont, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()
            st.subheader("🗑️ Apagar Itens")
            for _, row in consultar_db("SELECT * FROM avisos").iterrows():
                if st.button(f"Excluir: {row['titulo']}", key=f"del_{row['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":row['id']}); st.rerun()
        with t2:
            with st.form("add_fin"):
                d, v = st.text_input("Descrição"), st.number_input("Valor")
                t = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d, "v":v, "t":t, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.rerun()
            for _, row in consultar_db("SELECT * FROM financeiro").iterrows():
                if st.button(f"🗑️ Apagar {row['descricao']} (R${row['valor']})", key=f"dfin_{row['id']}"):
                    executar_query("DELETE FROM financeiro WHERE id=:id", {"id":row['id']}); st.rerun()

    elif menu == "📢 Mural":
        st.title("📢 Mural Ágape")
        # Palavra do Dia Automática
        if 'palavra' not in st.session_state:
            p = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p.empty: st.session_state.palavra = f'"{p.iloc[0]["texto"]}" ({p.iloc[0]["livro"]} {p.iloc[0]["cap"]}:{p.iloc[0]["ver"]})'
        if 'palavra' in st.session_state: st.info(f"📖 **Palavra do Dia:** {st.session_state.palavra}")
        
        for _, av in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            st.markdown(f'<div class="card-mural"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p></div>', unsafe_allow_html=True)

    elif menu == "🎥 Bate-papo":
        st.title("💬 Bate-papo")
        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            dest = st.radio("Para:", ["Todos"] + list(consultar_db("SELECT nome FROM membros WHERE nome!=:n", {"n":u['nome']})['nome']))
            st.divider()
            # VÍDEO LINK DIRETO PARA EVITAR ERRO
            url_v = f"https://jit.si_{datetime.now().day}"
            st.link_button("🎥 ENTRAR NO VÍDEO", url_v, use_container_width=True)
            st.caption(f"Link: {url_v}")
        with c2:
            chat = st.container(height=400)
            with chat:
                for _, r in consultar_db("SELECT * FROM mensagens ORDER BY id ASC").iterrows():
                    me = r['de_user'] == u['nome']
                    align, cor = ("flex-end", "#dcf8c6") if me else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div class="chat-bubble" style="background:{cor};"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
            with st.form("chat_f", clear_on_submit=True):
                txt = st.text_input("Mensagem")
                arq = st.file_uploader("Arquivo", type=['pdf','png','jpg'])
                if st.form_submit_button("Enviar"):
                    b64 = base64.b64encode(arq.read()).decode() if arq else ""
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_data, anexo_nome) VALUES (:d,:p,:t,:ad,:an)", {"d":u['nome'], "p":dest, "t":txt, "ad":b64, "an":arq.name if arq else ""})
                    st.rerun()

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo", f"R$ {e-s:,.2f}", delta=e-s)
            st.dataframe(df, use_container_width=True)

    elif menu == "📖 Bíblia":
        # ... Mantido igual com livros e capítulos
        l_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not l_db.empty:
            col1, col2 = st.columns([0.3, 0.7])
            l_s = col1.selectbox("Livro", l_db['livro'])
            c_s = col1.selectbox("Cap", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_s})['cap'])
            txt_c = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_s, "c":c_s})
            txt_h = "".join([f"<p><b>{v['ver']}</b> {v['texto']}</p>" for _, v in txt_c.iterrows()])
            col2.markdown(f'<div class="caixa-leitura">{txt_h}</div>', unsafe_allow_html=True)
