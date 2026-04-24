import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string
import io

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; background-color: #1E3A8A; color: white; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .comentario-box { padding: 10px; border-left: 4px solid #1E3A8A; background-color: #f1f3f9; margin-top: 5px; border-radius: 5px; font-size: 14px; }
    .codigo-box { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border: 1px dashed #1e88e5; text-align: center; font-size: 20px; font-weight: bold; color: #1e3a8a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (SQLAlchemy) ---
engine = create_engine("sqlite:///agape_portal.db", pool_size=10, max_overflow=20)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, biblia_id INTEGER, nome_membro TEXT, comentario TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN E ESTADO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA INICIAL (LOGOFF) ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])
    
    with t_log:
        with st.form("login_form"):
            u = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": u})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user_nome": res.iloc[0]['nome'], "is_admin": bool(res.iloc[0]['is_admin'])})
                    st.rerun()
                else: st.error("Dados inválidos.")
    with t_cad:
        with st.form("cad_form"):
            n, e, s1 = st.text_input("Nome Completo"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                cod = "AG-" + "".join(random.choices(string.digits, k=5))
                executar_query("INSERT INTO membros (nome, email, codigo, senha) VALUES (:n, :e, :c, :p)",
                               {"n": n, "e": e, "c": cod, "p": generate_password_hash(s1)})
                st.markdown(f"<div class='codigo-box'>CADASTRO REALIZADO!<br>Código: {cod}</div>", unsafe_allow_html=True)

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["🏠 Mural", "📖 Sala de Estudos", "💰 Ofertas", "⚙️ Administração"])
    
    if menu == "🏠 Mural":
        st.title("📢 Mural de Avisos")
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            st.markdown(f"<div class='aviso-card'><h3>{r['titulo']}</h3><p>{r['conteudo']}</p></div>", unsafe_allow_html=True)

    elif menu == "📖 Sala de Estudos":
        st.title("📖 Sala de Estudos Bíblicos")
        livros_db = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        
        if not livros_db.empty:
            col1, col2 = st.columns(2)
            liv_sel = col1.selectbox("Escolha o Livro", livros_db['livro'].tolist())
            caps_db = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l ORDER BY capitulo", {"l": liv_sel})
            cap_sel = col2.selectbox("Capítulo", caps_db['capitulo'].tolist())
            
            versiculos = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": liv_sel, "c": cap_sel})
            
            for _, v in versiculos.iterrows():
                with st.expander(f"Versículo {v['versiculo']}"):
                    st.info(v['texto'])
                    comts = consultar_db("SELECT * FROM comentarios WHERE biblia_id=:id", {"id": int(v['id'])})
                    for _, c in comts.iterrows():
                        st.markdown(f"<div class='comentario-box'><b>{c['nome_membro']}</b>: {c['comentario']}</div>", unsafe_allow_html=True)
                    
                    with st.form(f"cm_{v['id']}", clear_on_submit=True):
                        txt_c = st.text_area("Adicione um comentário/dúvida")
                        if st.form_submit_button("Enviar"):
                            executar_query("INSERT INTO comentarios (biblia_id, nome_membro, comentario, data) VALUES (:bid, :nome, :txt, :dt)",
                                           {"bid": int(v['id']), "nome": st.session_state.user_nome, "txt": txt_c, "dt": datetime.now().strftime("%d/%m %H:%M")})
                            st.rerun()
        else: st.warning("Bíblia ainda não importada.")

    elif menu == "⚙️ Administração" and st.session_state.is_admin:
        st.title("⚙️ Painel do Administrador")
        t1, t2, t3 = st.tabs(["📥 Importar Bíblia", "👥 Membros", "🗑️ Limpar Banco"])
        
        with t1:
            st.subheader("Importação Segura por Blocos")
            file = st.file_uploader("Subir arquivo 'acf.json'", type=['json'])
            if file and st.button("Iniciar Importação"):
                try:
                    dados = json.load(file)
                    total = len(dados)
                    progresso = st.progress(0)
                    texto_status = st.empty()
                    
                    for i in range(0, total, 500):
                        bloco = dados[i:i+500]
                        with engine.begin() as conn:
                            for v in bloco:
                                conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"),
                                             {"l": v['book'], "c": v['chapter'], "v": v['number'], "t": v['text']})
                        perc = min((i + 500) / total, 1.0)
                        progresso.progress(perc)
                        texto_status.text(f"Processando {i+len(bloco)} de {total}...")
                    st.success("✅ Importação concluída!")
                except Exception as e: st.error(f"Erro: {e}")

        with t2:
            st.dataframe(consultar_db("SELECT id, nome, email, codigo FROM membros"))

        with t3:
            st.warning("Cuidado! Isso apagará todos os versículos importados.")
            if st.button("🔴 APAGAR TODOS OS VERSÍCULOS"):
                executar_query("DELETE FROM biblia")
                st.rerun()

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
