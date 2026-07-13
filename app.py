import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import requests

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# Instancia o cliente da IA utilizando a nova biblioteca google-genai
from google import genai
from google.genai import types

@st.cache_resource
def info_ia():
    try:
        # Busca automaticamente a variável de ambiente GEMINI_API_KEY
        return genai.Client()
    except Exception:
        return None

client_gemini = info_ia()

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
        except Exception: 
            return pd.DataFrame()

# CRIAÇÃO DAS TABELAS (Garante execução inicial limpa)
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id TEXT);")
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

# --- 3. MAPEAMENTO DE LIVROS DA BÍBLIA (Português -> Abreviações para API Estável) ---
MAPA_LIVROS = {
    "Gênesis": "gn", "Êxodo": "ex", "Levítico": "lv", "Números": "num", "Deuteronômio": "dt",
    "Josué": "js", "Juízes": "jz", "Rute": "rt", "1 Samuel": "1sm", "2 Samuel": "2sm",
    "1 Reis": "1rs", "2 Reis": "2rs", "1 Crônicas": "1cr", "2 Crônicas": "2cr", "Esdras": "ez",
    "Neemias": "ne", "Ester": "et", "Jó": "jo", "Salmos": "sl", "Provérbios": "pv",
    "Eclesiastes": "ec", "Cânticos": "ct", "Isaías": "is", "Jeremias": "jr", "Lamentações": "lm",
    "Ezequiel": "ezq", "Daniel": "dn", "Oseias": "os", "Joel": "jl", "Amós": "am",
    "Obadias": "ob", "Jonas": "jn", "Miqueias": "mq", "Naum": "na", "Habacuque": "hc",
    "Sofonias": "sf", "Ageu": "ag", "Zacarias": "zc", "Malaquias": "ml",
    "Mateus": "mt", "Marcos": "mc", "Lucas": "lc", "João": "joao", "Atos": "at",
    "Romanos": "rm", "1 Coríntios": "1co", "2 Coríntios": "2co", "Gálatas": "gl", "Efésios": "ef",
    "Filipenses": "fp", "Colossenses": "cl", "1 Tessalonicenses": "1ts", "2 Tessalonicenses": "2ts", "1 Timóteo": "1tm",
    "2 Timóteo": "2tm", "Tito": "tt", "Filemom": "fm", "Hebreus": "hb", "Tiago": "tg",
    "1 Pedro": "1pe", "2 Pedro": "2pe", "1 João": "1jo", "2 João": "2jo", "3 João": "3jo",
    "Judas": "jd", "Apocalipse": "ap"
}
LIVROS_BIBLE = list(MAPA_LIVROS.keys())

# --- 4. FUNÇÃO ULTRA ESTÁVEL EM PORTUGUÊS (Almeida Recebida) ---
@st.cache_data(ttl=86400)
def buscar_capitulo_api(livro_pt, capitulo):
    abrev = MAPA_LIVROS.get(livro_pt, "gn")
    # Requisição direta a um repositório estável de arquivos JSON bíblicos em português
    url = f"https://githubusercontent.com{abrev}.json"
    try:
        resposta = requests.get(url, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            # O JSON é estruturado como uma lista de capítulos (índice começa em 0)
            if 0 < capitulo <= len(dados):
                versiculos_do_cap = dados[capitulo - 1]
                lista_formatada = []
                for index, texto in enumerate(versiculos_do_cap):
                    lista_formatada.append({"verse": index + 1, "text": texto})
                return lista_formatada
        return []
    except Exception:
        return []

# --- 5. INICIALIZAÇÃO DE MEMÓRIA DE SESSÃO ---
if "roteiro_culto" not in st.session_state:
    st.session_state.roteiro_culto = []

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

    menu = [
        "Início & Versículos", "Bíblia Completa & IA", "Comunhão Online (Jitsi)", 
        "Rádio Web & Transmissão", "Membros", "Cadastro de Visitantes", 
        "Escala de Cultos", "Escala de Visitas", "Financeiro & Dízimos Protegidos", 
        "Patrimônio da Igreja", "Avisos", "Louvores"
    ]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span style="color:#fff;">— João 3:16 (ACF)</span></div>', unsafe_allow_html=True)
        
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual_nome = meses[datetime.date.today().month - 1]
        
        st.write(f"🎉 **Aniversariantes do Mês de {mes_atual_nome}:**")
        df_aniv = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :m", {"m": mes_atual_nome})
        if not df_aniv.empty:
            for idx, row in df_aniv.iterrows(): 
                st.info(f"🎂 **{row['nome']}** ({row['cargo']})")
        else: 
            st.caption("Nenhum aniversário registrado para este mês.")
            
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa & IA":
        st.subheader("📖 Bíblia Sagrada Completa em Português (Almeida)")
        
        c1, c2 = st.columns(2)
        with c1:
            livro_sel = st.selectbox("Selecione o Livro:", LIVROS_BIBLE)
        with c2:
            capitulo_sel = st.number_input("Digite o Capítulo:", min_value=1, max_value=150, value=1, step=1)
            
