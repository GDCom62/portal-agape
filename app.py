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

# Estrutura do banco de dados local
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

if consultar_db("SELECT id FROM texto_biblico LIMIT 1").empty:
    executar_query("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES ('João', 3, 16, 'Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.');")
    executar_query("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES ('Salmos', 23, 1, 'O Senhor é o meu pastor, nada me faltará.');")

# Dicionário oficial com limite exato de capítulos por livro
LIVROS_BIBLE = {
    "Gênesis": {"api": "genesis", "caps": 50}, "Êxodo": {"api": "exodus", "caps": 40}, 
    "Levítico": {"api": "leviticus", "caps": 27}, "Números": {"api": "numbers", "caps": 36}, 
    "Deuteronômio": {"api": "deuteronomy", "caps": 34}, "Josué": {"api": "joshua", "caps": 24}, 
    "Juízes": {"api": "judges", "caps": 21}, "Rute": {"api": "ruth", "caps": 4},
    "1 Samuel": {"api": "1 samuel", "caps": 31}, "2 Samuel": {"api": "2 samuel", "caps": 24}, 
    "1 Reis": {"api": "1 kings", "caps": 22}, "2 Reis": {"api": "2 kings", "caps": 25}, 
    "1 Crônicas": {"api": "1 chronicles", "caps": 29}, "2 Crônicas": {"api": "2 chronicles", "caps": 36}, 
    "Esdras": {"api": "ezra", "caps": 10}, "Neemias": {"api": "nehemiah", "caps": 13}, 
    "Ester": {"api": "esther", "caps": 10}, "Jó": {"api": "job", "caps": 42}, 
    "Salmos": {"api": "psalms", "caps": 150}, "Provérbios": {"api": "proverbs", "caps": 31},
    "Eclesiastes": {"api": "ecclesiastes", "caps": 12}, "Cânticos": {"api": "song of solomon", "caps": 8}, 
    "Isaías": {"api": "isaiah", "caps": 66}, "Jeremias": {"api": "jeremiah", "caps": 52}, 
    "Lamentações": {"api": "lamentations", "caps": 5}, "Ezequiel": {"api": "ezekiel", "caps": 48}, 
    "Daniel": {"api": "daniel", "caps": 12}, "Oseias": {"api": "hosea", "caps": 14}, 
    "Joel": {"api": "joel", "caps": 3}, "Amós": {"api": "amos", "caps": 9}, 
    "Obadias": {"api": "obadiah", "caps": 1}, "Jonas": {"api": "jonah", "caps": 4}, 
    "Miqueias": {"api": "micah", "caps": 7}, "Naum": {"api": "nahum", "caps": 3}, 
    "Habacuque": {"api": "habakkuk", "caps": 3}, "Sofonias": {"api": "zephaniah", "caps": 3},
    "Ageu": {"api": "haggai", "caps": 2}, "Zacarias": {"api": "zechariah", "caps": 14}, 
    "Malaquias": {"api": "malachi", "caps": 4}, "Mateus": {"api": "matthew", "caps": 28}, 
    "Marcos": {"api": "mark", "caps": 16}, "Lucas": {"api": "lucas", "caps": 24}, 
    "João": {"api": "john", "caps": 21}, "Atos": {"api": "acts", "caps": 28}, 
    "Romanos": {"api": "romans", "caps": 16}, "1 Coríntios": {"api": "1 corinthians", "caps": 16},
    "2 Coríntios": {"api": "2 corinthians", "caps": 13}, "Gálatas": {"api": "galatians", "caps": 6}, 
    "Efésios": {"api": "ephesians", "caps": 6}, "Filipenses": {"api": "philippians", "caps": 4}, 
    "Colossenses": {"api": "colossians", "caps": 4}, "1 Tessalonicenses": {"api": "1 tessalonians", "caps": 5}, 
    "2 Tessalonicenses": {"api": "2 tessalonians", "caps": 3}, "1 Timóteo": {"api": "1 timothy", "caps": 6}, 
    "2 Timóteo": {"api": "2 timothy", "caps": 4}, "Tito": {"api": "titus", "caps": 3}, 
    "Filemom": {"api": "philemon", "caps": 1}, "Hebreus": {"api": "hebrews", "caps": 13}, 
    "Tiago": {"api": "james", "caps": 5}, "1 Pedro": {"api": "1 peter", "caps": 5}, 
    "2 Pedro": {"api": "2 peter", "caps": 3}, "1 João": {"api": "1 john", "caps": 5}, 
    "2 João": {"api": "2 john", "caps": 1}, "3 João": {"api": "3 john", "caps": 1}, 
    "Judas": {"api": "judas", "caps": 1}, "Apocalipse": {"api": "revelation", "caps": 22}
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
        df_v_dia = consultar_db("SELECT texto FROM texto_biblico WHERE livro = 'João' AND capitulo = 3 AND versiculo = 16")
        txt_box = df_v_dia.loc[0, "texto"] if not df_v_dia.empty else "Porque Deus amou o mundo de tal maneira..."
        st.markdown(f'<div class="versiculo-box"><h4>"{txt_box}"</h4><span style="color:#fff;">— João 3:16</span></div>', unsafe_allow_html=True)
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual_nome = meses[datetime.date.today().month - 1]
        st.write(f"🎉 **Aniversariantes do Mês de {mes_atual_nome}:**")
        df_aniv = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :m", {"m": mes_atual_nome})
