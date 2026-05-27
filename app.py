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

# Criação das tabelas estruturais locais
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

# Dicionário de mapeamento internacional exigido pela API estável
LIVROS_TRADUCAO = {
    "Gênesis": "genesis", "Êxodo": "exodus", "Levítico": "leviticus", "Números": "numbers", "Deuteronômio": "deuteronomy",
    "Josué": "joshua", "Juízes": "judges", "Rute": "ruth", "1 Samuel": "1 samuel", "2 Samuel": "2 samuel",
    "1 Reis": "1 kings", "2 Reis": "2 kings", "1 Crônicas": "1 cronicles", "2 Crônicas": "2 chronicles", "Esdras": "ezra",
    "Neemias": "nehemiah", "Ester": "esther", "Jó": "job", "Salmos": "psalms", "Provérbios": "proverbs",
    "Eclesiastes": "ecclesiastes", "Cânticos": "song of solomon", "Isaías": "isaiah", "Jeremias": "jeremiah", "Lamentações": "lamentations",
    "Ezequiel": "ezekiel", "Daniel": "daniel", "Oseias": "hosea", "Joel": "joel", "Amós": "amos", "Obadias": "obadiah",
    "Jonas": "jonah", "Miqueias": "micah", "Naum": "nahum", "Habacuque": "habakkuk", "Sofonias": "zephaniah",
    "Ageu": "haggai", "Zacarias": "zechariah", "Malaquias": "malachi", "Mateus": "matthew", "Marcos": "mark",
    "Lucas": "lucas", "João": "john", "Atos": "acts", "Romanos": "romans", "1 Coríntios": "1 corinthians",
    "2 Coríntios": "2 corinthians", "Gálatas": "galatians", "Efésios": "ephesians", "Filipenses": "philippians", "Colossenses": "colossians",
    "1 Tessalonicenses": "1 letters", "2 Tessalonicenses": "2 letters", "1 Timóteo": "1 timothy", "2 Timóteo": "2 timothy",
    "Tito": "titus", "Filemom": "philemon", "Hebreus": "hebrews", "Tiago": "james", "1 Pedro": "1 peter",
    "2 Pedro": "2 peter", "1 João": "1 john", "2 João": "2 john", "3 João": "3 john", "Judas": "judas", "Apocalipse": "revelation"
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
        st.subheader("📖 Bíblia Sagrada Completa (Carregamento por Demanda)")
        modo = st.radio("Escolha o modo:", ["Leitura por Capítulo", "Pesquisar por Palavra-Chave"], horizontal=True)
        
        if modo == "Leitura por Capítulo":
            c1, c2 = st.columns(2)
            l_nome = c1.selectbox("Selecione o Livro:", list(LIVROS_TRADUCAO.keys()))
            c_num = c2.number_input("Selecione o Capítulo:", min_value=1, max_value=150, value=1, step=1)
            
            if st.button("📖 Carregar Apenas o Capítulo Escolhido", use_container_width=True):
                with st.spinner("Buscando capítulo na nuvem..."):
                    try:
                        # Carrega UNICAMENTE o livro e o capítulo selecionados na tela para não estourar a memória
                        url = f"https://bible-api.com{LIVROS_TRADUCAO[l_nome]}+{c_num}"
                        res = requests.get(url, timeout=7)
                        if res.status_code == 200:
                            html = f"<div class='leitura-box'><h4>📜 {l_nome} — Capítulo {c_num}</h4><br>"
                            for v in res.json()["verses"]: html += f"<p><b style='color:#FFA500;'>{v['verse']}.</b> {v['text']}</p>"
                            st.markdown(html + "</div>", unsafe_allow_html=True)
                        else: st.error("Capítulo não localizado para este livro.")
                    except: st.error("O servidor da Bíblia demorou a responder. Tente clicar novamente.")
        else:
            termo = st.text_input("Digite a palavra ou frase para buscar (Ex: jesus, amor):").strip()
            if termo:
                with st.spinner("Pesquisando ocorrências..."):
                    try:
                        # Busca apenas as correspondências exatas da palavra digitada
