import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
import json
import urllib.request

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- CONEXÃO BANCO DE DADOS ---
@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v70.db", connect_args={"check_same_thread": False, "timeout": 30})

engine = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn: 
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: 
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except: 
            return pd.DataFrame()

# Inicialização das tabelas essenciais
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, data_cadastro TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    senha_hash = generate_password_hash("agape2026", method="pbkdf2:sha256")
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": senha_hash})

# --- RECONSTRUTOR INTEGRADO DE ALTA PERFORMANCE (BIBLIA.JSON AUTOMÁTICO) ---
@st.cache_data(show_spinner=False)
def carregar_e_validar_biblia():
    nome_arquivo = "biblia.json"
    url_fonte = "https://githubusercontent.com"
    
    # Se o arquivo não existir ou estiver corrompido, reconstrói automaticamente
    reconstruir = True
    if os.path.exists(nome_arquivo):
        try:
            with open(nome_arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if dados and len(dados.keys()) > 2:
                    reconstruir = False
                    return dados
        except:
            reconstruir = True

    if reconstruir:
        try:
            req = urllib.request.Request(url_fonte, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as response:
                originais = json.loads(response.read().decode('utf-8'))
            
            biblia_limpa = {}
            for livro in originais:
                nome_l = livro["name"]
                biblia_limpa[nome_l] = {}
                for idx_c, capitulo in enumerate(livro["chapters"], start=1):
                    biblia_limpa[nome_l][str(idx_c)] = {}
                    for idx_v, texto_v in enumerate(capitulo, start=1):
                        biblia_limpa[nome_l][str(idx_c)][str(idx_v)] = texto_v
            
            with open(nome_arquivo, "w", encoding="utf-8") as f:
                json.dump(biblia_limpa, f, ensure_ascii=False, indent=4)
            return biblia_limpa
        except:
            # Contingência estática imediata caso o GitHub falhe
            return {
                "Gênesis": {"1": {"1": "No princípio criou Deus os céus e a terra.", "2": "E a terra era sem forma e vazia."}},
                "Salmos": {"23": {"1": "O Senhor é o meu pastor, nada me faltará."}},
                "João": {"3": {"16": "Porque Deus amou o mundo de tal maneira..."}}
            }

# --- ESTILIZAÇÃO VISUAL ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 15px; border-radius: 8px; color: #212529 !important; margin-bottom: 8px; border-left: 5px solid #FFA500; }
    </style>
""", unsafe_allow_html=True)

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

st.sidebar.title("🔐 Login Portal")
if not st.session_state.autenticado:
    u = st.sidebar.text_input("Usuário").strip()
    p = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar", use_container_width=True):
        df = consultar_db("SELECT senha FROM usuarios WHERE usuario = :u", {"u": u})
        if not df.empty and check_password_hash(str(df.loc[0, 'senha']), p):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("Dados incorretos.")

if st.session_state.autenticado:
    st.sidebar.success("Conectado!")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    menu = ["Início", "Bíblia", "Membros", "Financeiro"]
    escolha = st.selectbox("Selecione a Seção:", menu)
    st.divider()

    if escolha == "Início":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span>— João 3:16</span></div>', unsafe_allow_html=True)

    elif escolha == "Bíblia":
        st.subheader("📖 Leitura da Bíblia Sagrada")
        
        with st.spinner("Indexando livros e capítulos..."):
            bible_data = carregar_e_validar_biblia()
            
        lista_livros = list(bible_data.keys())
        col_l, col_c = st.columns(2)
        with col_l:
            livro_sel = st.selectbox("Livro:", lista_livros)
            
        lista_caps = list(bible_data[livro_sel].keys())
        with col_c:
            cap_sel = st.selectbox("Capítulo:", lista_caps)
            
        st.write(f"### {livro_sel} - Capítulo {cap_sel}")
        st.divider()
        
        versos = bible_data[livro_sel][cap_sel]
        for num, texto in versos.items():
            st.markdown(f'<div class="leitura-box"><b>{num}.</b> {texto}</div>', unsafe_allow_html=True)

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        with st.form("form_membro"):
            nome = st.text_input("Nome")
            cargo = st.text_input("Função")
            if st.form_submit_button("Cadastrar"):
                if nome:
                    executar_query("INSERT INTO membros (nome, cargo, data_cadastro) VALUES (:n, :c, :d)", {"n": nome, "c": cargo, "d": str(datetime.date.today())})
                    st.success("Cadastrado com sucesso!")
                    st.rerun()
        
        df_m = consultar_db("SELECT nome as Nome, cargo as Cargo, data_cadastro as [Data Cadastro] FROM membros")
        st.dataframe(df_m, use_container_width=True, hide_index=True)

    elif escolha == "Financeiro":
        st.subheader("💰 Livro Caixa")
        with st.form("form_fin"):
            tipo = st.selectbox("Movimento", ["Entrada", "Saída"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
            if st.form_submit_button("Lançar"):
                if desc and valor > 0:
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:t, :desc, :v, :d)", {"t": tipo, "desc": desc, "v": valor, "d": str(datetime.date.today())})
                    st.success("Lançado!")
                    st.rerun()

        df_f = consultar_db("SELECT tipo as Tipo, descricao as Descrição, valor as Valor, data as Data FROM financeiro")
        st.dataframe(df_f, use_container_width=True, hide_index=True)
else:
    st.info("Digite suas credenciais na barra lateral para liberar o acesso.")
