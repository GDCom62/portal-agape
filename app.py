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

def executar_query(sql, params=None):
    with engine.begin() as conn: 
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: 
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except: 
            return pd.DataFrame()

# Criação inicial das tabelas do sistema
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
executar_query("CREATE TABLE IF NOT EXISTS escalas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ministerio TEXT, voluntario TEXT, periodo TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS escalas_visitas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, irmao_visitado TEXT, endereço TEXT, responsavel TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS visitantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, data_visita TEXT, observacoes TEXT, precisa_visita TEXT DEFAULT 'Não');")
executar_query("CREATE TABLE IF NOT EXISTS patrimonio (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, quantidade INTEGER, valor REAL, estado TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, objetivo TEXT, valor_alvo REAL, arrecadado REAL DEFAULT 0.0);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

# --- 3. DICIONÁRIO BÍBLICO NATIVO DE BACKUP ---
BIBLIA_ESTAVEL = {
    "Gênesis": {
        1: {
            1: "No princípio criou Deus os céus e a terra.", 
            2: "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo.", 
            3: "E disse Deus: Haja luz; e houve luz.", 
            4: "E viu Deus que era boa a luz; e fez Deus separação entre a luz e as trevas.", 
            5: "E Deus chamou à luz Dia; e às trevas chamou Noite."
        }
    },
    "Números": {
        4: {
            1: "Falou mais o Senhor a Moisés e a Arão, dizendo:", 
            2: "Toma a soma dos filhos de Coate, dentre os filhos de Levi...", 
            3: "Da idade de trinta anos para cima até aos cinquenta anos...", 
            4: "Este será o serviço dos filhos de Coate na tenda da congregação."
        }
    },
    "Salmos": {
        23: {
            1: "O Senhor é o meu pastor, nada me faltará.", 
            2: "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.", 
            3: "Refrigera a minha alma; guia-me pelas veredas da justiça.", 
            4: "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum.", 
            5: "Preparas uma mesa perante mim na presença dos meus inimigos.", 
            6: "Certamente que a bondade e a misericórdia me seguirão."
        }
    },
    "João": {
        3: {
            16: "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", 
            17: "Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo.", 
            18: "Quem crê nele não é condizido à condenação."
        }
    }
}

LIVROS_API = {
    "Gênesis": "GN", "Êxodo": "EX", "Levítico": "LV", "Números": "NU", "Deuteronômio": "DE",
    "Josué": "JS", "Juízes": "JZ", "Rute": "RT", "1 Samuel": "1S", "2 Samuel": "2S",
    "1 Reis": "1R", "2 Reis": "2R", "1 Crônicas": "1C", "2 Crônicas": "2C", "Esdras": "ED",
    "Neemias": "NE", "Ester": "ET", "Jó": "JO", "Salmos": "SL", "Provérbios": "PV",
    "Eclesiastes": "EC", "Cantares": "CT", "Isaías": "IS", "Jeremias": "JR", "Lamentações": "LM",
    "Ezequiel": "EZ", "Daniel": "DN", "Oséias": "OS", "Joel": "JL", "Amós": "AM",
    "Obadias": "OB", "Jonas": "JN", "Miqueias": "MQ", "Naum": "NA", "Habacuque": "HC",
    "Sofonias": "SF", "Ageu": "AG", "Zacarias": "ZC", "Malaquias": "ML", "Mateus": "MT",
    "Marcos": "MC", "Lucas": "LC", "João": "JO", "Atos": "AT", "Romanos": "RM",
    "1 Coríntios": "1C", "2 Coríntios": "2C", "Gálatas": "GL", "Efésios": "EF", "Filipenses": "FL",
    "Colossenses": "CL", "1 Tessalonicenses": "1T", "2 Tessalonicenses": "2T", "1 Timóteo": "1T", "2 Timóteo": "2T",
    "Tito": "TT", "Filemom": "FL", "Hebreus": "HB", "Tiago": "TG", "1 Pedro": "1P",
    "2 Pedro": "2P", "1 João": "1J", "2 João": "2J", "3 João": "3J", "Judas": "JD",
    "Apocalipse": "AP"
}

@st.cache_data(ttl=3600)
def buscar_capitulo_api(livro_abrev, capitulo):
    url = f"https://bible-api.com{livro_abrev}+{capitulo}?translation=almeida"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

def renderizar_modulo_biblia(livro, cap):
    abrev = LIVROS_API[livro]
    dados_cap = buscar_capitulo_api(abrev, cap)
    if dados_cap and "verses" in dados_cap:
        for verso in dados_cap["verses"]:
            st.markdown(f'<div class="leitura-box"><b>{verso["verse"]}.</b> {verso["text"]}</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Modo Offline Ativado: Exibindo textos locais estáveis.")
        if livro in BIBLIA_ESTAVEL and cap in BIBLIA_ESTAVEL[livro]:
            versiculos = BIBLIA_ESTAVEL[livro][cap]
            for num_ver, texto_ver in versiculos.items():
                st.markdown(f'<div class="leitura-box"><b>{num_ver}.</b> {texto_ver}</div>', unsafe_allow_html=True)
        else:
            st.info("Texto indisponível offline para este capítulo. Verifique sua conexão.")

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
if not st.session_state.autenticado:
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
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
