import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import json
import requests
import datetime
import random

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONFIGURAÇÕES DE AMBIENTE ---
URL_CHAT_RAILWAY = "https://railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS PERSISTENTE & REDIS ---
@st.cache_resource
def inicializar_conexoes():
    engine = create_engine(
        "sqlite:///agape_v60.db", 
        connect_args={"check_same_thread": False, "timeout": 30}
    )
    try:
        r_db = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        r_db = None
    return engine, r_db

engine, r_db = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# --- FUNÇÃO CORRIGIDA: API A BÍBLIA DIGITAL ---
def buscar_versiculo_api():
    sugestoes = [
        {"slug": "jo", "cap": 3},
        {"slug": "sl", "cap": 23},
        {"slug": "fp", "cap": 4},
        {"slug": "is", "cap": 41},
        {"slug": "rm", "cap": 8},
        {"slug": "mt", "cap": 6}
    ]
    escolha = random.choice(sugestoes)
    version = "nvi"
    
    try:
        url = f"https://abibliadigital.com.br{version}/{escolha['slug']}/{escolha['cap']}"
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "verses" in dados and len(dados["verses"]) > 0:
                v_sorteado = random.choice(dados["verses"])
                texto = v_sorteado.get("text", "")
                numero = v_sorteado.get("number", 1)
                referencia = f"{dados['book']['name']} {dados['chapter']}:{numero}"
                return texto, referencia
    except Exception:
        pass
        
    return ("Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "João 3:16")

# Inicialização segura das tabelas nativas do sistema
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT,
    nivel TEXT DEFAULT 'Membro'
);
""")

try:
    executar_query("ALTER TABLE usuarios ADD COLUMN nivel TEXT DEFAULT 'Membro';")
except Exception:
    pass 

executar_query("""
CREATE TABLE IF NOT EXISTS membros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    telefone TEXT,
    cargo TEXT,
    data_cadastro TEXT,
    mes_aniversario TEXT,
    observacoes TEXT
);
""")

try:
    executar_query("ALTER TABLE membros ADD COLUMN observacoes TEXT DEFAULT '';")
except Exception:
    pass

executar_query("""
CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    descricao TEXT,
    valor REAL,
    data TEXT,
    mes_ano TEXT,
    membro_id INTEGER
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    conteudo TEXT,
    data TEXT
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS louvores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    artista TEXT,
    letra TEXT,
    arquivo_audio BLOB
);
""")

# Sincronização do Administrador Nativo
def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    admin_senha_pura = "agape2026"
    hash_admin = generate_password_hash(admin_senha_pura, method="scrypt")
    
    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
    if existe.empty:
        executar_query("INSERT OR IGNORE INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", 
                       {"user": admin_usuario, "senha": hash_admin})
    else:
        executar_query("UPDATE usuarios SET senha = :senha, nivel = 'Pastor' WHERE usuario = :user", 
                       {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. ESTILIZAÇÃO CUSTOMIZADA (AMARELO OURO) ---
st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
    }
    .stMetric, div[data-testid="stMetricValue"], div[data-testid="metric-container"], .card-flutuante, .cartao-membro {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 16px !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.1) !important;
        border: 1px solid #e0a800 !important;
        color: #212529 !important;
    }
    .versiculo-box {
        background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important;
        color: #FFD700 !important;
        padding: 30px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        margin-bottom: 25px !important;
        border: 2px solid #FFD700 !important;
        text-align: center !important;
    }
    .texto-sagrado-grande {
        font-size: 22px !important;
        font-family: 'Georgia', serif !important;
        line-height: 1.6 !important;
        margin-bottom: 15px !important;
        color: #FFD700 !important;
        text-align: center;
    }
    .numero-versiculo {
        color: #ffffff !important;
        font-weight: bold !important;
        display: block;
        margin-top: 10px;
        font-size: 16px;
    }
    .pix-card {
        background-color: #ffffff !important;
        padding: 30px;
        border-radius: 20px;
        border: 2px dashed #008080;
        text-align: center;
        box-shadow: 0 6px 16px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. GESTÃO DE ACESSO COM PERSISTÊNCIA DIRETA ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_atual = "Membro"

st.sidebar.title("🔐 Portal Ágape")

if not st.session_state.autenticado:
    aba_side_login, aba_side_novo, aba_side_esqueci = st.sidebar.tabs(["Entrar", "Novo Acesso", "Esqueci a Senha"])
    
    with aba_side_login:
        campo_usuario = st.text_input("E-mail/Usuário", value="admin@agape.com", key="login_user_input").strip()
        campo_senha = st.text_input("Senha", type="password", value="agape2026", key="login_pass_input")
        
        if st.button("Entrar no Sistema", use_container_width=True, key="btn_login_direct"):
            df_u = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :user", {"user": campo_usuario})
            if not df_u.empty and check_password_hash(str(df_u.loc[0, 'senha']), campo_senha):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = campo_usuario
                st.session_state.nivel_atual = df_u.loc[0, 'nivel']
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
                    
    with aba_side_novo:
        reg_user = st.text_input("E-mail para Acesso", key="reg_user_input").strip()
        reg_pass = st.text_input("Defina uma Senha", type="password", key="reg_pass_input")
        if st.button("Solicitar Acesso", use_container_width=True, key="btn_reg_direct"):
            if reg_user and reg_pass:
                if len(reg_pass) < 4:
                    st.error("A senha precisa ter no mínimo 4 caracteres.")
                else:
                    check_existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reg_user})
                    if check_existe.empty:
                        hash_nova_senha = generate_password_hash(reg_pass, method="scrypt")
                        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Membro')",
                                       {"u": reg_user, "s": hash_nova_senha})
                        st.success("Acesso criado! Vá para a aba 'Entrar'.")
                    else:
                        st.error("Este e-mail já está cadastrado.")
            else:
                st.warning("Preencha todos os campos.")

    with aba_side_esqueci:
        reset_user = st.text_input("E-mail Cadastrado", key="reset_user_input").strip()
        nova_senha_pura = st.text_input("Nova Senha Desejada", type="password", key="reset_pass_input")
        if st.button("Atualizar Senha", use_container_width=True, key="btn_reset_direct"):
            if reset_user and nova_senha_pura:
                check_user = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reset_user})
                if not check_user.empty:
                    if len(nova_senha_pura) < 4:
                        st.error("A nova senha precisa ter no mínimo 4 caracteres.")
                    else:
                        hash_reset = generate_password_hash(nova_senha_pura, method="scrypt")
                        executar_query("UPDATE usuarios SET senha = :s WHERE usuario = :u", {"s": hash_reset, "u": reset_user})
                        st.success("Senha updated! Faça login na aba 'Entrar'.")
                else:
                    st.error("E-mail não encontrado.")
            else:
                st.warning("Preencha todos os campos.")

# --- 6. PAINEL PRINCIPAL (APÓS AUTENTICAÇÃO) ---
if st.session_state.autenticado:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_atual}")
    st.sidebar.info(f"Nível: {st.session_state.nivel_atual}")
    
