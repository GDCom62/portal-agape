import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
import urllib.request
import json

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONEXÃO BANCO DE DADOS LOCAL ---
@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})

engine = inicializar_conexoes()

def ejecutar_query(sql, params=None):
    with engine.begin() as conn: 
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: 
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except: 
            return pd.DataFrame()

# Criação das tabelas de forma encapsulada
def criar_tabelas_sistema():
    ejecutar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
    ejecutar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, miembro_id INTEGER);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS escalas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ministerio TEXT, voluntario TEXT, periodo TEXT);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS escalas_visitas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, irmao_visitado TEXT, endereço TEXT, responsavel TEXT);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS visitantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, data_visita TEXT, observacoes TEXT, precisa_visita TEXT DEFAULT 'Não');")
    ejecutar_query("CREATE TABLE IF NOT EXISTS patrimonio (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, quantidade INTEGER, valor REAL, estado TEXT);")
    ejecutar_query("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, objetivo TEXT, valor_alvo REAL, arrecadado REAL DEFAULT 0.0);")

    admin_user = "admin@agape.com"
    if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
        ejecutar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

criar_tabelas_sistema()

# --- 3. DICIONÁRIO DE MAPEAMENTO PARA O PADRÃO DA API (66 LIVROS) ---
LIVROS_BIBLE = {
    "Gênesis": {"en": "genesis", "caps": 50}, "Êxodo": {"en": "exodus", "caps": 40}, 
    "Levítico": {"en": "leviticus", "caps": 27}, "Números": {"en": "numbers", "caps": 36}, 
    "Deuteronômio": {"en": "deuteronomy", "caps": 34}, "Josué": {"en": "joshua", "caps": 24}, 
    "Juízes": {"en": "judges", "caps": 21}, "Rute": {"en": "ruth", "caps": 4}, 
    "1 Samuel": {"en": "1samuel", "caps": 31}, "2 Samuel": {"en": "2samuel", "caps": 24}, 
    "1 Reis": {"en": "1kings", "caps": 22}, "2 Reis": {"en": "2kings", "caps": 25}, 
    "1 Crônicas": {"en": "1chronicles", "caps": 29}, "2 Crônicas": {"en": "2chronicles", "caps": 36}, 
    "Esdras": {"en": "ezra", "caps": 10}, "Neemias": {"en": "nehemiah", "caps": 13}, 
    "Ester": {"en": "esther", "caps": 10}, "Jó": {"en": "job", "caps": 42}, 
    "Salmos": {"en": "psalms", "caps": 150}, "Provérbios": {"en": "proverbs", "caps": 31}, 
    "Eclesiastes": {"en": "ecclesiastes", "caps": 12}, "Cantares": {"en": "songofsolomon", "caps": 8}, 
    "Isaías": {"en": "isaiah", "caps": 66}, "Jeremias": {"en": "jeremiah", "caps": 52}, 
    "Lamentações": {"en": "lamentations", "caps": 5}, "Ezequiel": {"en": "ezekiel", "caps": 48}, 
    "Daniel": {"en": "daniel", "caps": 12}, "Oséias": {"en": "hosea", "caps": 14}, 
    "Joel": {"en": "joel", "caps": 3}, "Amós": {"en": "amos", "caps": 9}, 
    "Obadias": {"en": "obadiah", "caps": 1}, "Jonas": {"en": "jonah", "caps": 4}, 
    "Miqueias": {"en": "micah", "caps": 7}, "Naum": {"en": "nahum", "caps": 3}, 
    "Habacuque": {"en": "habakkuk", "caps": 3}, "Sofonias": {"en": "zephaniah", "caps": 3}, 
    "Ageu": {"en": "haggai", "caps": 2}, "Zacarias": {"en": "zechariah", "caps": 14}, 
    "Malaquias": {"en": "malachi", "caps": 4}, "Mateus": {"en": "matthew", "caps": 28}, 
    "Marcos": {"en": "mark", "caps": 16}, "Lucas": {"en": "lukes", "caps": 24}, 
    "João": {"en": "john", "caps": 21}, "Atos": {"en": "acts", "caps": 28}, 
    "Romanos": {"en": "romans", "caps": 16}, "1 Coríntios": {"en": "1corinthians", "caps": 16}, 
    "2 Coríntios": {"en": "2corinthians", "caps": 13}, "Gálatas": {"en": "galatians", "caps": 6}, 
    "Efésios": {"en": "ephesians", "caps": 6}, "Filipenses": {"en": "philippians", "caps": 4}, 
    "Colossenses": {"en": "colossians", "caps": 4}, "1 Tessalonicenses": {"en": "1thessalonians", "caps": 5}, 
    "2 Tessalonicenses": {"en": "2thessalonians", "caps": 3}, "1 Timóteo": {"en": "1timothy", "caps": 6}, 
    "2 Timóteo": {"en": "2timothy", "caps": 4}, "Tito": {"en": "titus", "caps": 3}, 
    "Filemom": {"en": "philemon", "caps": 1}, "Hebreus": {"en": "hebrews", "caps": 13}, 
    "Tiago": {"en": "james", "caps": 5}, "1 Pedro": {"en": "1peter", "caps": 5}, 
    "2 Pedro": {"en": "2peter", "caps": 3}, "1 João": {"en": "1john", "caps": 5}, 
    "2 João": {"en": "2john", "caps": 1}, "3 João": {"en": "3john", "caps": 1}, 
    "Judas": {"en": "jude", "caps": 1}, "Apocalipse": {"en": "revelation", "caps": 22}
}

@st.cache_data(ttl=3600)
def buscar_capitulo_online(livro_en, capitulo):
    url = f"https://bible-api.com{livro_en}+{capitulo}?translation=almeida"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

def abrir_aba_biblia():
    col_l, col_c = st.columns(2)
    with col_l:
        livro_nome = st.selectbox("Selecione o Livro:", list(LIVROS_BIBLE.keys()))
    
    # Obtém o total de capítulos correto para o livro selecionado
    max_caps = LIVROS_BIBLE[livro_nome]["caps"]
    with col_c:
        cap_sel = st.selectbox("Selecione o Capítulo:", list(range(1, max_caps + 1)))
    
    st.write(f"### {livro_nome} - Capítulo {cap_sel}")
    st.divider()
    
    # Envia o termo correto em inglês traduzido para a API externa
    livro_en = LIVROS_BIBLE[livro_nome]["en"]
    dados = buscar_capitulo_online(livro_en, cap_sel)
    
    if dados and "verses" in dados:
        for verso in dados["verses"]:
            st.markdown(f'<div class="leitura-box"><b>{verso["verse"]}.</b> {verso["text"]}</div>', unsafe_allow_html=True)
    else:
        st.error("Servidor de busca ocupado ou sem conexão com a internet. Tente novamente em instantes.")

# --- 4. ESTILIZAÇÃO VISUAL ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 20px; border-radius: 12px; border: 1px solid #e0a800; color: #212529 !important; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.usuario_atual, st.session_state.nivel_atual = False, None, "Membro"

st.sidebar.title("🔐 Acesso ao Portal")
if not st.session_state.autenticado:
    tab_log, tab_new = st.sidebar.tabs(["Entrar", "Novo Acesso"])
    with tab_log:
        u = st.text_input("Usuário", value="admin@agape.com", key="u_log").strip()
        p = st.text_input("Senha", type="password", value="agape2026", key="p_log")
        if st.button("Autenticar", use_container_width=True):
            df = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :u", {"u": u})
            if not df.empty and check_password_hash(str(df.loc[0, 'senha']), p):
                st.session_state.autenticado, st.session_state.usuario_atual, st.session_state.nivel_atual = True, u, df.loc[0, 'nivel']
                st.rerun()
            else: 
                st.error("Dados incorretos.")
    with tab_new:
        nu = st.text_input("E-mail corporativo", key="u_reg").strip()
        np = st.text_input("Senha de acesso", type="password", key="p_reg")
        if st.button("Cadastrar conta", use_container_width=True):
            if nu and len(np) >= 4:
                if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": nu}).empty:
                    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Membro')", {"u": nu, "s": generate_password_hash(np, method="scrypt")})
                    st.success("Conta criada!")

if st.session_state.autenticado:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_atual}")
    if st.sidebar.button("🚪 Desconectar Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Cadastro de Visitantes", "Escala de Cultos", "Escala de Visitas", "Financeiro & Dízimos", "Patrimônio da Igreja", "Avisos", "Louvores"]
