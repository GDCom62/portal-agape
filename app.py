import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# Instancia o cliente da IA utilizando a nova biblioteca google-genai
from google import genai
from google.genai import types

@st.cache_resource
def info_ia():
    try:
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

# CRIAÇÃO DAS TABELAS DO SISTEMA
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

# CRIAÇÃO DA TABELA BÍBLICA LOCAL INTEGRADA
executar_query("CREATE TABLE IF NOT EXISTS biblia_sagrada (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

# SE A BÍBLIA LOCAL ESTIVER VAZIA, ALIMENTA AUTOMATICAMENTE COM OS TEXTOS PRINCIPAIS
if consultar_db("SELECT id FROM biblia_sagrada LIMIT 1").empty:
    versiculos_iniciais = [
        # Gênesis 1
        ("Gênesis", 1, 1, "No princípio criou Deus os céus e a terra."),
        ("Gênesis", 1, 2, "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus se movia sobre a face das águas."),
        ("Gênesis", 1, 3, "E disse Deus: Haja luz; e houve luz."),
        ("Gênesis", 1, 4, "E viu Deus que era boa a luz; e fez Deus separação entre a luz e as trevas."),
        ("Gênesis", 1, 5, "E Deus chamou à luz Dia; e às trevas chamou Noite. E foi a tarde e a manhã, o dia primeiro."),
        # Salmos 23
        ("Salmos", 23, 1, "O Senhor é o meu pastor, nada me faltará."),
        ("Salmos", 23, 2, "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas."),
        ("Salmos", 23, 3, "Refrigera a minha alma; guia-me pelas veredas da justiça, por amor do seu nome."),
        ("Salmos", 23, 4, "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo; a tua vara e o teu cajado me consolam."),
        ("Salmos", 23, 5, "Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda."),
        ("Salmos", 23, 6, "Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na casa do Senhor por longos dias."),
        # Salmos 91
        ("Salmos", 91, 1, "Aquele que habita no esconderijo do Altíssimo, à sombra do Onipotente descansará."),
        ("Salmos", 91, 2, "Direi do Senhor: Ele é o meu Deus, o meu refúgio, a minha fortaleza, e nele confiarei."),
        ("Salmos", 91, 3, "Porque ele te livrará do laço do passarinheiro, e da peste perniciosa."),
        # João 3
        ("João", 3, 16, "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."),
        ("João", 3, 17, "Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo por ele."),
        # Mateus 6
        ("Mateus", 6, 9, "Portanto, vós orareis assim: Pai nosso, que estás nos céus, santificado seja o teu nome;"),
        ("Mateus", 6, 10, "Venha o teu reino, seja feita a tua vontade, assim na terra como no céu;"),
        ("Mateus", 6, 11, "O pão nosso de cada dia nos dá hoje;")
    ]
    for liv, cap, ver, txt in versiculos_iniciais:
        executar_query("INSERT INTO biblia_sagrada (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)", {"l": liv, "c": cap, "v": ver, "t": txt})

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

LIVROS_BIBLE = ["Gênesis", "Êxodo", "Levítico", "Números", "Deuteronômio", "Josué", "Juízes", "Rute", "1 Samuel", "2 Samuel", "1 Reis", "2 Reis", "Salmos", "Provérbios", "Mateus", "Marcos", "Lucas", "João", "Atos", "Romanos", "Apocalipse"]

# --- 3. INICIALIZAÇÃO DE MEMÓRIA DE SESSÃO ---
if "roteiro_culto" not in st.session_state:
    st.session_state.roteiro_culto = []

st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 20px; border-radius: 12px; border: 1px solid #e0a800; color: #212529 !important; margin-bottom: 10px; font-size: 16px; line-height: 1.6; }
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
