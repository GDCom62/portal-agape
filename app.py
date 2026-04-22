import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #ddd; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .btn-perigo > div > button { background-color: #ff4b4b !important; color: white !important; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_portal.db", pool_size=10, max_overflow=20)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM001', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_nome' not in st.session_state: st.session_state.user_nome = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 4. TELA INICIAL ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        t_log, t_cad, t_rec = st.tabs(["🔐 Entrar", "📝 Cadastro", "🔑 Senha"])
        
        with t_log:
            with st.form("login_agape"):
                email_l = st.text_input("E-mail")
                senha_l = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email_l})
                    if not res.empty:
                        user = res.iloc[0]
                        if user['ativo'] == 0: st.error("Conta desativada.")
                        elif check_password_hash(user['senha'], senha_l):
                            st.session_state.update({"logado": True, "user_nome": user['nome'], "is_admin": bool(user['is_admin'])})
                            st.rerun()
                        else: st.error("Senha incorreta.")
                    else: st.error("Não cadastrado.")
        
        with t_cad:
            with st.form("cad_membro"):
                n_n, n_e, n_s = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    if n_n and n_e and n_s:
                        cod = "AG-" + ''.join(random.choices(string.digits, k=4))
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": n_n, "e": n_e, "c": cod, "p": generate_password_hash(n_s)})
                        st.success(f"Sucesso! Seu código: {cod}")
        
        with t_rec:
            with st.form("rec_senha"):
                re_e, re_c, re_s = st.text_input("E-mail"), st.text_input("Código"), st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Resetar"):
                    user = consultar_db("SELECT * FROM membros WHERE email=:e AND codigo=:c", {"e": re_e, "c": re_c})
                    if not user.empty:
                        executar_query("UPDATE membros SET senha=:p WHERE email=:e", {"p": generate_password_hash(re_s), "e": re_e})
                        st.success("Senha atualizada!")

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 Olá, {st.session_state.user_nome}")
    menu = ["🏠 Mural", "📖 Bíblia & Estudos", "🙏 Orações", "💰 Ofertas"]
    if st.session_state.is_admin: menu.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação", menu)
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- PÁGINA ADMIN ---
    if escolha == "⚙️ Administração":
        st.title("⚙️ Gestão Administrativa")
        tab_m, tab_b = st.tabs(["👥 Gerenciar Membros", "📖 Editar Bíblia/Estudos"])
        
        with tab_m:
            df_m = consultar_db("SELECT id, nome, email, codigo, ativo FROM membros WHERE is_admin=0")
            for _, m in df_m.iterrows():
                with st.expander(f"👤 {m['nome']} ({m['email']})"):
                    c1, c2, c3 = st.columns(3)
                    btn_txt = "Bloquear" if m['ativo'] == 1 else "Ativar"
                    if c1.button(btn_txt, key=f"bl_{m['id']}"):
                        executar_query("UPDATE membros SET ativo=:s WHERE id=:id", {"s": 0 if m['ativo']==1 else 1, "id": int(m['id'])})
                        st.rerun()
                    confirmar = c2.checkbox("Confirmar exclusão", key=f"ch_{m['id']}")
                    st.markdown('<div class="btn-perigo">', unsafe_allow_html=True)
                    if c3.button("EXCLUIR", key=f"ex_{m['id']}", disabled=not confirmar):
                        executar_query("DELETE FROM membros WHERE id=:id", {"id": int(m['id'])})
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        with tab_b:
            st.subheader("📝 Cadastrar ou Editar Estudo Bíblico")
            with st.form("form_biblia"):
                liv = st.text_input("Livro (ex: João)")
                cap = st.number_input("Capítulo", min_value=1)
                ver = st.number_input("Versículo", min_value=1)
                txt = st.text_area("Texto Bíblico")
                exp = st.text_area("Explicação Teológica")
                if st.form_submit_button("Salvar Estudo"):
                    # Verifica se já existe para atualizar ou inserir
                    existe = consultar_db("SELECT id FROM biblia WHERE livro=:l AND capitulo=:c AND versiculo=:v", {"l": liv, "c": cap, "v": ver})
                    if not existe.empty:
                        executar_query("UPDATE biblia SET texto=:t, explicacao=:e WHERE id=:id", {"t": txt, "e": exp, "id": int(existe.iloc[0]['id'])})
                    else:
                        executar_query("INSERT INTO biblia (livro, capitulo, versiculo, texto, explicacao) VALUES (:l, :c, :v, :t, :e)",
                                       {"l": liv, "c": cap, "v": ver, "t": txt, "e": exp})
                    st.success("Estudo salvo!")

    elif escolha == "📖 Bíblia & Estudos":
        st.title("📖 Explicações Bíblicas")
        df_b = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not df_b.empty:
            l_sel = st.selectbox("Livro", df_b['livro'].tolist())
            c_sel = st.number_input("Capítulo", min_value=1)
            if st.button("Buscar Estudo"):
                res = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l_sel, "c": c_sel})
                if not res.empty:
                    for _, r in res.iterrows():
                        st.info(f"**Versículo {r['versiculo']}**: {r['texto']}")
                        st.write(f"💡 {r['explicacao']}")
                else: st.warning("Sem estudos para este capítulo.")
        else: st.info("O administrador ainda não cadastrou estudos.")

    elif escolha == "🏠 Mural":
        st.title("📢 Avisos")
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            st.markdown(f"<div class='aviso-card'><h3>{r['titulo']}</h3><p>{r['conteudo']}</p></div>", unsafe_allow_html=True)
