import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import datetime
import random

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONEXÃO BANCO DE DADOS ---
@st.cache_resource
def inicializar_conexoes():
    engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})
    return engine

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

# --- 3. INTEGRAÇÃO REAL COM A BÍBLIA DIGITAL ---
def buscar_versiculo_api():
    sugestoes = [
        {"slug": "jo", "cap": 3}, {"slug": "sl", "cap": 23},
        {"slug": "fp", "cap": 4}, {"slug": "is", "cap": 41},
        {"slug": "rm", "cap": 8}, {"slug": "mt", "cap": 6}
    ]
    escolha = random.choice(sugestoes)
    try:
        url = f"https://abibliadigital.com.br{escolha['slug']}/{escolha['cap']}"
        resposta = requests.get(url, timeout=4)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "verses" in dados and len(dados["verses"]) > 0:
                v_sorteado = random.choice(dados["verses"])
                return v_sorteado.get("text", ""), f"{dados['book']['name']} {dados['chapter']}:{v_sorteado.get('number', 1)}"
    except Exception:
        pass
    return ("Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "João 3:16")

# Dicionário de mapeamento para busca de livros na API
LIVROS_BIBLIA = {
    "Gênesis": "gn", "Êxodo": "ex", "Levítico": "lv", "Números": "nu", "Deuteronômio": "dt", "Josué": "js",
    "Juízes": "jz", "Rute": "rt", "1 Samuel": "1sm", "2 Samuel": "2sm", "1 Reis": "1rs", "2 Reis": "2rs",
    "1 Crônicas": "1cr", "2 Crônicas": "2cr", "Esdras": "ez", "Neemias": "ne", "Ester": "et", "Jó": "jo",
    "Salmos": "sl", "Provérbios": "pv", "Eclesiastes": "ec", "Cânticos": "ct", "Isaías": "is", "Jeremias": "jr",
    "Lamentações": "lm", "Ezequiel": "ezk", "Daniel": "dn", "Oseias": "ho", "Joel": "jl", "Amós": "am",
    "Obadias": "ob", "Jonas": "jn", "Miqueias": "mi", "Naum": "na", "Habacuque": "hb", "Sofonias": "ze",
    "Ageu": "hg", "Zacarias": "zc", "Malaquias": "ml", "Mateus": "mt", "Marcos": "mc", "Lucas": "lc",
    "João": "jo", "Atos": "act", "Romanos": "rm", "1 Coríntios": "1co", "2 Coríntios": "2co", "Gálatas": "gl",
    "Efésios": "ep", "Filipenses": "fp", "Colossenses": "cl", "1 Tessalonicenses": "1th", "2 Tessalonicenses": "2th",
    "1 Timóteo": "1tm", "2 Timóteo": "2tm", "Tito": "tt", "Filemom": "phm", "Hebreus": "hb", "Tiago": "ja",
    "1 Pedro": "1pe", "2 Pedro": "2pe", "1 João": "1jo", "2 João": "2jo", "3 João": "3jo", "Judas": "jd",
    "Apocalipse": "re"
}

# Criar tabelas necessárias de forma segura
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, miembro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, letra TEXT, arquivo_audio BLOB);")

# Sincronizar dados do Admin padrão
def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    hash_admin = generate_password_hash("agape2026", method="scrypt")
    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
    if existe.empty:
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. LAYOUT DESIGN CUSTOMIZADO ---
st.markdown("""
    <style>
    .stAppViewContainer {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
    }
    .versiculo-box {
        background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important;
        color: #FFD700 !important;
        padding: 25px !important;
        border-radius: 15px !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
        margin-bottom: 20px !important;
        border: 2px solid #FFD700 !important;
        text-align: center !important;
    }
    .texto-sagrado-grande {
        font-size: 20px !important;
        font-family: 'Georgia', serif !important;
        line-height: 1.5 !important;
    }
    .numero-versiculo {
        color: #ffffff !important;
        font-weight: bold !important;
        display: block;
        margin-top: 8px;
    }
    .leitura-box {
        background-color: #ffffff !important;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #e0a800;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        color: #212529 !important;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. GESTÃO DE ACESSO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_atual = "Membro"

st.sidebar.title("🔐 Acesso ao Portal")

if not st.session_state.autenticado:
    tab_log, tab_new = st.sidebar.tabs(["Entrar", "Novo Acesso"])
    
    with tab_log:
        campo_usuario = st.text_input("E-mail/Usuário", value="admin@agape.com", key="u_login").strip()
        campo_senha = st.text_input("Senha", type="password", value="agape2026", key="p_login")
        if st.button("Autenticar", use_container_width=True):
            df_u = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :user", {"user": campo_usuario})
            if not df_u.empty and check_password_hash(str(df_u.loc[0, 'senha']), campo_senha):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = campo_usuario
                st.session_state.nivel_atual = df_u.loc[0, 'nivel']
                st.rerun()
            else:
                st.error("Dados incorretos.")
                
    with tab_new:
        reg_user = st.text_input("E-mail corporativo", key="u_reg").strip()
        reg_pass = st.text_input("Senha de acesso", type="password", key="p_reg")
        if st.button("Cadastrar conta", use_container_width=True):
            if reg_user and len(reg_pass) >= 4:
                check = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reg_user})
                if check.empty:
                    h_pass = generate_password_hash(reg_pass, method="scrypt")
                    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Membro')", {"u": reg_user, "s": h_pass})
                    st.success("Conta criada! Acesse pela aba 'Entrar'.")
                else:
                    st.error("Usuário já existe.")
            else:
                st.warning("Preencha os campos (mínimo 4 dígitos).")

# --- 6. PAINEL DO PORTAL (LOGADO) ---
if st.session_state.autenticado:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_atual}")
    if st.sidebar.button("🚪 Desconectar Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.rerun()

    # MENU COM A NOVA ABA INCLUÍDA
    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="navigation_box_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        texto_v, ref_v = buscar_versiculo_api()
        st.markdown(f"""
            <div class="versiculo-box">
                <div class="texto-sagrado-grande">
                    "{texto_v}"
                    <span class="numero-versiculo">— {ref_v}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        df_m_total = consultar_db("SELECT id FROM membros")
        st.metric("Total de Membros Cadastrados", f"{len(df_m_total)} Irmãos")

    # --- NOVA SEÇÃO: BÍBLIA COMPLETA ---
    elif escolha == "Bíblia Completa":
        st.subheader("📖 Leitura da Bíblia Sagrada")
        
        c1, c2, c3 = st.columns([2, 1, 1])
        livro_nome = c1.selectbox("Selecione o Livro:", list(LIVROS_BIBLIA.keys()))
        capitulo_num = c2.number_input("Capítulo:", min_value=1, max_value=150, value=1, step=1)
        versao = c3.selectbox("Versão:", ["NVI", "ACF"])
        
        if st.button("📖 Ler Capítulo", use_container_width=True):
            slug = LIVROS_BIBLIA[livro_nome]
            v_slug = versao.lower()
            try:
                url_cap = f"https://abibliadigital.com.br{v_slug}/{slug}/{capitulo_num}"
                res = requests.get(url_cap, timeout=5)
                if res.status_code == 200:
                    dados_cap = res.json()
                    st.success(f"Exibindo: {dados_cap['book']['name']} — Capítulo {dados_cap['chapter']}")
                    
                    # Concatena e renderiza todo o texto bíblico organizado
