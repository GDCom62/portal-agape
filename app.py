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
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #ddd; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .comentario-box { padding: 10px; border-left: 4px solid #1E3A8A; background-color: #f1f3f9; margin-top: 5px; border-radius: 5px; }
    .codigo-box { background-color: #e3f2fd; padding: 15px; border-radius: 10px; border: 1px dashed #1e88e5; text-align: center; font-size: 20px; font-weight: bold; color: #1e3a8a; }
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
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, biblia_id INTEGER, nome_membro TEXT, comentario TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_nome' not in st.session_state: st.session_state.user_nome = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 4. TELA INICIAL ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])
    
    with t_log:
        with st.form("login"):
            u, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": u})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user_nome": res.iloc[0]['nome'], "is_admin": bool(res.iloc[0]['is_admin'])})
                    st.rerun()
                else: st.error("Dados inválidos.")

    with t_cad:
        with st.form("cad"):
            n, e, s1 = st.text_input("Nome Completo"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                cod = "AG-" + "".join(random.choices(string.digits, k=5))
                executar_query("INSERT INTO membros (nome, email, codigo, senha) VALUES (:n, :e, :c, :p)",
                               {"n": n, "e": e, "c": cod, "p": generate_password_hash(s1)})
                st.markdown(f"<div class='codigo-box'>CADASTRO REALIZADO!<br>Seu código é: {cod}</div>", unsafe_allow_html=True)

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 {st.session_state.user_nome}")
    menu = st.sidebar.radio("Navegação", ["🏠 Mural", "📖 Sala de Estudos", "🙏 Orações", "💰 Ofertas", "⚙️ Administração"])
    
    if menu == "📖 Sala de Estudos":
        st.title("📖 Sala de Estudos Interativa")
        livros_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        
        if not livros_db.empty:
            col1, col2 = st.columns(2)
            livro_sel = col1.selectbox("Escolha o Livro", livros_db['livro'].tolist())
            caps_db = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": livro_sel})
            cap_sel = col2.selectbox("Capítulo", caps_db['capitulo'].tolist())
            
            versiculos = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l": livro_sel, "c": cap_sel})
            
            for _, v in versiculos.iterrows():
                with st.expander(f"Versículo {v['versiculo']}"):
                    st.info(v['texto'])
                    if v['explicacao']:
                        st.subheader("💡 Explicação do Pastor/Líder")
                        st.write(v['explicacao'])
                    
                    st.divider()
                    st.subheader("💬 Comentários dos Membros")
                    coments = consultar_db("SELECT * FROM comentarios WHERE biblia_id=:id", {"id": int(v['id'])})
                    for _, c in coments.iterrows():
                        st.markdown(f"<div class='comentario-box'><b>{c['nome_membro']}</b> ({c['data']}):<br>{c['comentario']}</div>", unsafe_allow_html=True)
                    
                    with st.form(f"coment_{v['id']}", clear_on_submit=True):
                        txt_coment = st.text_area("Adicione sua dúvida ou comentário")
                        if st.form_submit_button("Enviar Comentário"):
                            executar_query("INSERT INTO comentarios (biblia_id, nome_membro, comentario, data) VALUES (:bid, :nome, :txt, :dt)",
                                           {"bid": int(v['id']), "nome": st.session_state.user_nome, "txt": txt_coment, "dt": datetime.now().strftime("%d/%m %H:%M")})
                            st.rerun()
        else:
            st.warning("Nenhum conteúdo bíblico importado ainda.")

    elif menu == "⚙️ Administração" and st.session_state.is_admin:
        st.title("⚙️ Painel Administrativo")
        t1, t2 = st.tabs(["📥 Importar Bíblia (JSON)", "👥 Membros"])
        
        with t1:
            st.subheader("Importação Massiva de Versículos")
            st.write("O arquivo JSON deve conter uma lista de objetos com: livro, capitulo, versiculo, texto.")
            file = st.file_uploader("Subir JSON da Bíblia", type=['json'])
            if file and st.button("Processar Importação"):
                dados = json.load(file)
                for item in dados:
                    executar_query("INSERT INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)",
                                   {"l": item['livro'], "c": item['capitulo'], "v": item['versiculo'], "t": item['texto']})
                st.success("Importação concluída com sucesso!")

        with t2:
            st.dataframe(consultar_db("SELECT id, nome, email, codigo FROM membros"))

    elif menu == "💰 Ofertas":
        st.title("💰 Dízimos e Ofertas")
        res = consultar_db("SELECT * FROM config_geral LIMIT 1")
        if not res.empty:
            st.success(f"Chave PIX: `{res.iloc[0]['chave_pix']}`")
            if res.iloc[0]['url_qrcode']: st.image(res.iloc[0]['url_qrcode'], width=300)

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
