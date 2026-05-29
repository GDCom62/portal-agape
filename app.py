import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import urllib.request
import json

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- CONEXÃO BANCO DE DADOS LOCAL ---
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

# Inicialização limpa e direta das tabelas
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    senha_hash = generate_password_hash("agape2026", method="pbkdf2:sha256")
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": senha_hash})

# --- DICIONÁRIO DE 66 LIVROS PARA A API ---
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
def buscar_versiculos(livro_en, capitulo):
    url = f"https://bible-api.com{livro_en}+{capitulo}?translation=almeida"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except:
        return None

# --- ESTILIZAÇÃO VISUAL ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 15px; border-radius: 8px; color: #212529 !important; margin-bottom: 8px; border-left: 5px solid #FFA500; }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE LOGIN ---
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
    st.sidebar.success("Conectado com Sucesso!")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    # Navegação simplificada e linear
    menu = ["Início", "Bíblia Completa", "Membros", "Financeiro"]
    escolha = st.selectbox("Selecione a Seção:", menu)
    st.divider()

    if escolha == "Início":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span>— João 3:16</span></div>', unsafe_allow_html=True)

    if escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Completa")
        col_l, col_c = st.columns(2)
        with col_l:
            livro_sel = st.selectbox("Selecione o Livro:", list(LIVROS_BIBLE.keys()))
        
        max_caps = LIVROS_BIBLE[livro_sel]["caps"]
        with col_c:
            cap_sel = st.selectbox("Selecione o Capítulo:", list(range(1, max_caps + 1)))
        
        st.write(f"### {livro_sel} - Capítulo {cap_sel}")
        st.divider()
        
        livro_en = LIVROS_BIBLE[livro_sel]["en"]
        dados = buscar_versiculos(livro_en, cap_sel)
        
        if dados and "verses" in dados:
            for verso in dados["verses"]:
                st.markdown(f'<div class="leitura-box"><b>{verso["verse"]}.</b> {verso["text"]}</div>', unsafe_allow_html=True)
        else:
            st.error("Servidor de busca ocupado. Por favor, mude de capítulo ou tente novamente.")

    if escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        with st.form("form_membro"):
            nome = st.text_input("Nome do Membro")
            funcao = st.text_input("Cargo / Função")
            if st.form_submit_button("Salvar Registro"):
                if nome:
                    executar_query("INSERT INTO membros (nome, cargo, data_cadastro) VALUES (:n, :c, :d)", {"n": nome, "c": funcao, "d": str(datetime.date.today())})
                    st.success("Membro adicionado!")
                    st.rerun()
        
        df_membros = consultar_db("SELECT nome as Nome, cargo as Cargo, data_cadastro as [Data Cadastro] FROM membros")
        st.dataframe(df_membros, use_container_width=True, hide_index=True)

    if escolha == "Financeiro":
        st.subheader("💰 Caixa da Igreja")
        with st.form("form_fin"):
            tipo = st.selectbox("Tipo de Movimentação", ["Entrada", "Saída"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Lançar"):
                if desc and valor > 0:
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:t, :desc, :v, :d)", {"t": tipo, "desc": desc, "v": valor, "d": str(datetime.date.today())})
                    st.success("Lançamento efetuado!")
                    st.rerun()

        df_fin = consultar_db("SELECT tipo as Tipo, descricao as Descrição, valor as Valor, data as Data FROM financeiro")
        st.dataframe(df_fin, use_container_width=True, hide_index=True)
else:
    st.info("Por favor, preencha os dados de login na barra lateral para acessar o Portal.")
