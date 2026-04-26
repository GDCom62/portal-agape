import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import json

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (VERSÃO V12) ---
engine = create_engine("sqlite:///agape_v12.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS playlist (id INTEGER PRIMARY KEY, nome TEXT, url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY, data TEXT, codigo_membro TEXT, valor REAL)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad, t_rec = st.tabs(["🔐 Entrar", "📝 Cadastro", "🔑 Esqueci Senha"])
    
    with t_log:
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Dados incorretos.")

    with t_cad:
        with st.form("cad"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                c = "AG-" + "".join(random.choices(string.digits, k=4))
                executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                st.success(f"Código gerado: {c}")

    with t_rec:
        with st.form("rec"):
            re_e, re_c, re_s = st.text_input("E-mail"), st.text_input("Código AG-XXXX"), st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Redefinir"):
                check = consultar_db("SELECT id FROM membros WHERE email=:e AND codigo=:c", {"e":re_e, "c":re_c})
                if not check.empty:
                    executar_query("UPDATE membros SET senha=:s WHERE email=:e", {"s": generate_password_hash(re_s), "e": re_e})
                    st.success("Senha alterada!")
                else: st.error("Dados não conferem.")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.title(f"🙏 {u['nome']}")
    menu = st.sidebar.radio("Navegação", ["🎶 Louvores", "📖 Bíblia", "📊 Transparência", "⚙️ Admin"])
    if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

    # --- LOUVORES ---
    if menu == "🎶 Louvores":
        st.title("🎶 Playlist Ágape")
        musicas = consultar_db("SELECT * FROM playlist")
        if musicas.empty:
            st.info("Nenhum louvor na playlist.")
        else:
            for _, m in musicas.iterrows():
                with st.container(border=True):
                    st.subheader(f"🎵 {m['nome']}")
                    st.audio(m['url'])

    # --- BÍBLIA ---
    elif menu == "📖 Bíblia":
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap}).iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")
        else: st.warning("Importe a Bíblia no Admin.")

    # --- TRANSPARÊNCIA ---
    elif menu == "📊 Transparência":
        df = consultar_db("SELECT data, codigo_membro, valor FROM financas ORDER BY id DESC")
        st.metric("Saldo Total", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

    # --- ADMIN ---
    elif menu == "⚙️ Admin" and u['is_admin']:
        st.title("Painel Admin")
        tab1, tab2, tab3 = st.tabs(["🎶 Adicionar Louvor", "💰 Lançar", "📖 Bíblia"])
        
        with tab1:
            with st.form("add_music"):
                n_m = st.text_input("Nome do Louvor")
                u_m = st.text_input("Link Direto do MP3 (URL)")
                if st.form_submit_button("Salvar na Playlist"):
                    executar_query("INSERT INTO playlist (nome, url) VALUES (:n, :u)", {"n": n_m, "u": u_m})
                    st.success("Adicionado!")

        with tab2:
            membros = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0")
            with st.form("add_fin"):
                sel = st.selectbox("Membro", membros['nome'].tolist()) if not membros.empty else ""
                val = st.number_input("Valor", 0.0)
                if st.form_submit_button("Lançar"):
                    cod = membros[membros['nome'] == sel]['codigo'].values[0]
                    executar_query("INSERT INTO financas (data, codigo_membro, valor) VALUES (:d, :c, :v)", {"d": datetime.now().strftime("%d/%m/%Y"), "c": cod, "v": val})
                    st.success("Lançado!")
                    
        with tab3:
            f = st.file_uploader("acf.json", type=['json'])
            if f and st.button("Importar Bíblia"):
                dados = json.load(f)
                for liv in dados:
                    for ic, cl in enumerate(liv.get('chapters', [])):
                        for iv, tv in enumerate(cl):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l": str(liv.get('name')), "c": ic+1, "v": iv+1, "t": str(tv)})
                st.success("Bíblia Carregada!")
