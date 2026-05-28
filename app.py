import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import datetime

st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})

engine = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn: conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: return pd.read_sql_query(text(sql), conn, params=params or {})
        except: return pd.DataFrame()

# Estrutura do Banco de Dados Local
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
executar_query("CREATE TABLE IF NOT EXISTS texto_biblico (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

# Índice Completo de Todos os 66 Livros da Bíblia com a quantidade exata de capítulos
INFO_LIVROS = {
    "Gênesis": {"id": "gn", "caps": 50}, "Êxodo": {"id": "ex", "caps": 40}, "Levítico": {"id": "lv", "caps": 27},
    "Números": {"id": "nu", "caps": 36}, "Deuteronômio": {"id": "dt", "caps": 34}, "Josué": {"id": "js", "caps": 24},
    "Juízes": {"id": "jz", "caps": 21}, "Rute": {"id": "rt", "caps": 4}, "1 Samuel": {"id": "1sm", "caps": 31},
    "2 Samuel": {"id": "2sm", "caps": 24}, "1 Reis": {"id": "1rs", "caps": 22}, "2 Reis": {"id": "2rs", "caps": 25},
    "1 Crônicas": {"id": "1cr", "caps": 29}, "2 Crônicas": {"id": "2cr", "caps": 36}, "Esdras": {"id": "ez", "caps": 10},
    "Neemias": {"id": "ne", "caps": 13}, "Ester": {"id": "et", "caps": 10}, "Jó": {"id": "job", "caps": 42},
    "Salmos": {"id": "ps", "caps": 150}, "Provérbios": {"id": "pr", "caps": 31}, "Eclesiastes": {"id": "ec", "caps": 12},
    "Cânticos": {"id": "sg", "caps": 8}, "Isaías": {"id": "is", "caps": 66}, "Jeremias": {"id": "jr", "caps": 52},
    "Lamentações": {"id": "la", "caps": 5}, "Ezequiel": {"id": "ez", "caps": 48}, "Daniel": {"id": "dn", "caps": 12},
    "Oseias": {"id": "ho", "caps": 14}, "Joel": {"id": "jl", "caps": 3}, "Amós": {"id": "am", "caps": 9},
    "Obadias": {"id": "ob", "caps": 1}, "Jonas": {"id": "jon", "caps": 4}, "Miqueias": {"id": "mi", "caps": 7},
    "Naum": {"id": "na", "caps": 3}, "Habacuque": {"id": "hb", "caps": 3}, "Sofonias": {"id": "ze", "caps": 3},
    "Ageu": {"id": "hg", "caps": 2}, "Zacarias": {"id": "zc", "caps": 14}, "Malaquias": {"id": "ml", "caps": 4},
    "Mateus": {"id": "mt", "caps": 28}, "Marcos": {"id": "mk", "caps": 16}, "Lucas": {"id": "lk", "caps": 24},
    "João": {"id": "jn", "caps": 21}, "Atos": {"id": "ac", "caps": 28}, "Romanos": {"id": "rm", "caps": 16},
    "1 Coríntios": {"id": "1co", "caps": 16}, "2 Coríntios": {"id": "2co", "caps": 13}, "Gálatas": {"id": "gl", "caps": 6},
    "Efésios": {"id": "ep", "caps": 6}, "Filipenses": {"id": "ph", "caps": 4}, "Colossenses": {"id": "cl", "caps": 4},
    "1 Tessalonicenses": {"id": "1th", "caps": 5}, "2 Tessalonicenses": {"id": "2th", "caps": 3}, "1 Timóteo": {"id": "1ti", "caps": 6},
    "2 Timóteo": {"id": "2ti", "caps": 4}, "Tito": {"id": "ti", "caps": 3}, "Filemom": {"id": "phm", "caps": 1},
    "Hebreus": {"id": "he", "caps": 13}, "Tiago": {"id": "ja", "caps": 5}, "1 Pedro": {"id": "1pe", "caps": 5},
    "2 Pedro": {"id": "2pe", "caps": 3}, "1 João": {"id": "1jo", "caps": 5}, "2 João": {"id": "2jo", "caps": 1},
    "3 João": {"id": "3jo", "caps": 1}, "Judas": {"id": "jd", "caps": 1}, "Apocalipse": {"id": "re", "caps": 22}
}

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
            else: st.error("Dados incorretos.")
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
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span style="color:#fff;">— João 3:16 (ACF)</span></div>', unsafe_allow_html=True)
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual_nome = meses[datetime.date.today().month - 1]
        st.write(f"🎉 **Aniversariantes do Mês de {mes_atual_nome}:**")
        df_aniv = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :m", {"m": mes_atual_nome})
        if not df_aniv.empty:
            for idx, row in df_aniv.iterrows(): st.info(f"🎂 **{row['nome']}** ({row['cargo']})")
        else: st.caption("Nenhum aniversário registrado para este mês.")
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Completa (Por Demanda Dinâmica)")
        modo = st.radio("Escolha o modo:", ["Leitura por Capítulo", "Pesquisar por Palavra-Chave"], horizontal=True)
        
        if modo == "Leitura por Capítulo":
            c1, c2 = st.columns(2)
            l_nome = c1.selectbox("Selecione o Livro:", list(INFO_LIVROS.keys()))
            # Calcula dinamicamente o máximo de capítulos do livro escolhido
            max_caps = INFO_LIVROS[l_nome]["caps"]
            c_num = c2.number_input(f"Selecione o Capítulo (1 até {max_caps}):", min_value=1, max_value=max_caps, value=1, step=1)
            
