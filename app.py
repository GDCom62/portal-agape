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
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; background-color: #1E3A8A; color: white; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #ddd; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
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
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM001', :pw, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_nome' not in st.session_state: st.session_state.user_nome = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 4. TELA INICIAL (LOGIN / CADASTRO / AVISOS) ---
if not st.session_state.logado:
    st.title("⛪ Bem-vindo ao Portal Ágape")
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        tab_login, tab_cadastro = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])
        
        with tab_login:
            with st.form("login_agape"):
                email_l = st.text_input("E-mail")
                senha_l = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email_l})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], senha_l):
                        st.session_state.update({
                            "logado": True, 
                            "user_nome": res.iloc[0]['nome'], 
                            "is_admin": bool(res.iloc[0]['is_admin'])
                        })
                        st.rerun()
                    else: st.error("E-mail ou senha incorretos.")
        
        with tab_cadastro:
            st.info("Crie sua conta para participar da comunidade.")
            with st.form("cadastro_membro"):
                novo_nome = st.text_input("Nome Completo")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Crie uma Senha", type="password")
                confirma_senha = st.text_input("Confirme a Senha", type="password")
                
                if st.form_submit_button("Finalizar Cadastro"):
                    if not novo_nome or not novo_email or not nova_senha:
                        st.warning("Preencha todos os campos.")
                    elif nova_senha != confirma_senha:
                        st.error("As senhas não coincidem.")
                    else:
                        # Verificar se e-mail existe
                        existe = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": novo_email})
                        if not existe.empty:
                            st.error("Este e-mail já está cadastrado.")
                        else:
                            # Gerar código aleatório (ex: AG-482)
                            cod = "AG-" + ''.join(random.choices(string.digits, k=3))
                            hash_pw = generate_password_hash(nova_senha)
                            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)",
                                           {"n": novo_nome, "e": novo_email, "c": cod, "p": hash_pw})
                            st.success(f"Cadastro realizado! Seu código é {cod}. Agora você já pode entrar.")

    with col2:
        st.subheader("📢 Avisos da Comunidade")
        df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC LIMIT 5")
        if df_avisos.empty:
            st.info("Nenhum aviso no momento.")
        else:
            for _, row in df_avisos.iterrows():
                st.markdown(f"""<div class='aviso-card'><b>{row['titulo']}</b><br><small>{row['data']}</small></div>""", unsafe_allow_html=True)

# --- 5. ÁREA LOGADA (PAINEL DO MEMBRO) ---
else:
    st.sidebar.title(f"🙏 Olá, {st.session_state.user_nome}")
    menus = ["🏠 Mural de Avisos", "📖 Estudos Bíblicos", "🙏 Pedidos de Oração", "💰 Dízimos/Ofertas"]
    if st.session_state.is_admin: menus.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação", menus)
    if st.sidebar.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- Lógica das páginas continua a mesma do código anterior ---
    if escolha == "🏠 Mural de Avisos":
        st.title("📢 Mural da Igreja")
        df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, row in df_avisos.iterrows():
            st.markdown(f"""<div class='aviso-card'><h3>{row['titulo']}</h3><p>{row['conteudo']}</p><small>Postado em: {row['data']}</small></div>""", unsafe_allow_html=True)

    elif escolha == "📖 Estudos Bíblicos":
        st.title("📖 Estudos e Explicações")
        livros = ["Gênesis", "Salmos", "Provérbios", "Mateus", "João", "Romanos", "Apocalipse"]
        col_l, col_c = st.columns(2)
        l_sel = col_l.selectbox("Livro", livros)
        c_sel = col_c.number_input("Capítulo", min_value=1, step=1)
        if st.button("Ler Estudo"):
            res = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l_sel, "c": c_sel})
            if not res.empty:
                st.info(f"📜 {res.iloc[0]['texto']}")
                st.subheader("💡 Explicação Teológica")
                st.write(res.iloc[0]['explicacao'])
            else: st.warning("Ainda não temos um estudo cadastrado para este capítulo.")

    elif escolha == "🙏 Pedidos de Oração":
        st.title("🙏 Mural de Oração")
        with st.form("form_oracao"):
            msg_pedido = st.text_area("Escreva seu pedido ou agradecimento")
            if st.form_submit_button("Enviar Pedido"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data, status) VALUES (:n, :p, :d, 'Pendente')",
                               {"n": st.session_state.user_nome, "p": msg_pedido, "d": datetime.now().strftime("%d/%m/%Y")})
                st.success("Seu pedido foi registrado!")
        st.divider()
        df_oracoes = consultar_db("SELECT * FROM oracoes ORDER BY id DESC")
        for _, row in df_oracoes.iterrows():
            cor = "orange" if row['status'] == 'Pendente' else "green"
            st.markdown(f"""<div class='aviso-card'><b>{row['nome_membro']}</b> - <span style='color:{cor};'>{row['status']}</span><br><p>{row['pedido']}</p></div>""", unsafe_allow_html=True)

    elif escolha == "💰 Dízimos/Ofertas":
        st.title("💰 Contribuições")
        res = consultar_db("SELECT * FROM config_geral LIMIT 1")
        if not res.empty:
            st.success(f"Chave PIX: {res.iloc[0]['chave_pix']}")
            if res.iloc[0]['url_qrcode']: st.image(res.iloc[0]['url_qrcode'], width=300)
        else: st.warning("Dados não cadastrados pela administração.")

    elif escolha == "⚙️ Administração":
        st.title("⚙️ Painel Gestor")
        # (Lógica de administração conforme o código anterior: postar aviso, restaurar JSON, etc.)
        aba1, aba2 = st.tabs(["📢 Novo Aviso", "📂 Restaurar Dados Legados"])
        with aba1:
            with st.form("aviso_adm"):
                t = st.text_input("Título")
                c = st.text_area("Conteúdo")
                if st.form_submit_button("Publicar Aviso"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                   {"t": t, "c": c, "d": datetime.now().strftime("%d/%m/%Y")})
                    st.success("Aviso Publicado!")
        with aba2:
            st.subheader("📥 Importar Dados Ágape (JSON)")
            up = st.file_uploader("Selecione o arquivo backup_agape.json", type=['json'])
            if up and st.button("Executar Restauro"):
                try:
                    dados = json.loads(up.read().decode("utf-8"))
                    for m in dados.get('membros', []):
                        pw = generate_password_hash('Agape2026')
                        executar_query("INSERT OR IGNORE INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)",
                                       {"n": m['nome'], "e": m['email'], "c": m['codigo'], "p": pw})
                    st.success("Dados restaurados!")
                except Exception as e: st.error(f"Erro: {e}")
