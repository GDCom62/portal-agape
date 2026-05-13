import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import requests
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONFIGURAÇÕES DE AMBIENTE ---
URL_CHAT_RAILWAY = "https://railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS (CORRIGIDO PARA STREAMLIT CLOUD) ---
@st.cache_resource
def inicializar_conexoes():
    # Caminho /tmp resolve o erro de permissão de escrita (OperationalError)
    engine = create_engine(
        "sqlite:////tmp/agape_v60.db", 
        connect_args={"check_same_thread": False, "timeout": 10}
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

# Inicialização segura das tabelas
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS membros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    telefone TEXT,
    cargo TEXT,
    data_cadastro TEXT
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    descricao TEXT,
    valor REAL,
    data TEXT
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
    letra TEXT
);
""")

def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    admin_senha_pura = "agape2026"
    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
    if existe.empty:
        hash_admin = generate_password_hash(admin_senha_pura, method="scrypt")
        executar_query("INSERT INTO usuarios (usuario, senha) VALUES (:user, :senha)", 
                       {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. ESTILIZAÇÃO PROFISSIONAL (Elementos Flutuantes e Cantos Arredondados) ---
st.markdown("""
    <style>
    .stMetric, div[data-testid="stMetricValue"], div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 16px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .stMetric:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    .stButton>button {
        border-radius: 12px !important;
        padding: 10px 24px;
        font-weight: 600;
    }
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {
        border-radius: 12px !important;
    }
    .card-flutuante {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #4A90E2;
    }
    .versiculo-box {
        background: linear-gradient(135deg, #6B73FF 0%, #000DFF 100%);
        color: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 6px 20px rgba(0,13,255,0.15);
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. AUTENTICAÇÃO ---
def autenticar_usuario(usuario, senha):
    df = consultar_db("SELECT senha FROM usuarios WHERE usuario = :user", {"user": usuario})
    if not df.empty:
        hash_gravado = df.iloc[0]['senha']
        return check_password_hash(hash_gravado, senha)
    return False

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None

st.sidebar.title("🔐 Portal Ágape")

if not st.session_state.autenticado:
    with st.sidebar.form(key="form_login"):
        campo_usuario = st.text_input("E-mail/Usuário")
        campo_senha = st.text_input("Senha", type="password")
        botao_entrar = st.form_submit_button("Entrar")
        if botao_entrar:
            if autenticar_usuario(campo_usuario, campo_senha):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = campo_usuario
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha incorretos.")
    st.stop()
else:
    st.sidebar.write(f"Conectado como: **{st.session_state.usuario_atual}**")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.rerun()

# --- 6. MÓDULOS ---

def obter_versiculo_do_dia():
    try:
        r = requests.get("bible-api.com", timeout=3)
        if r.status_code == 200:
            dados = r.json()
            return dados['text'], dados['reference']
    except Exception:
        pass
    return "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "João 3:16"

def modulo_home():
    st.title("⛪ Painel Geral")
    
    texto_v, ref_v = obter_versiculo_do_dia()
    st.markdown(f"""
    <div class="versiculo-box">
        <h3>📖 Palavra do Dia</h3>
        <p style="font-size: 1.2rem; font-style: italic;">"{texto_v.strip()}"</p>
        <p style="text-align: right; font-weight: bold; margin-bottom: 0;">— {ref_v}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Processamento de Métricas
    tot_membros = len(consultar_db("SELECT id FROM membros"))
    fin_dados = consultar_db("SELECT tipo, valor FROM financeiro")
    
    entradas = fin_dados[fin_dados['tipo'] == 'Entrada']['valor'].sum() if not fin_dados.empty else 0.0
    saidas = fin_dados[fin_dados['tipo'] == 'Saída']['valor'].sum() if not fin_dados.empty else 0.0
    saldo = entradas - saidas
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Membros", f"{tot_membros} Cadastrados")
    col2.metric("Saldo Financeiro", f"R$ {saldo:,.2f}")
    col3.metric("Conexão Redis", "Estável" if r_db else "Offline")

    # Gráficos Financeiros Dinâmicos
    if not fin_dados.empty:
        st.subheader("📊 Resumo Financeiro Visual")
        df_agrupado = fin_dados.groupby('tipo')['valor'].sum().reset_index()
        st.bar_chart(data=df_agrupado, x='tipo', y='valor', use_container_width=True)

    # Quadro de Avisos
    st.subheader("📢 Mural de Avisos")
    df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC LIMIT 3")
    if not df_avisos.empty:
        for _, aviso in df_avisos.iterrows():
            st.markdown(f"""
            <div class="card-flutuante">
                <h4>📌 {aviso['titulo']}</h4>
                <p style="color: #666; font-size: 0.85rem;">Postado em: {aviso['data']}</p>
                <p>{aviso['conteudo']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nenhum aviso importante publicado no momento.")

def modulo_membros():
    st.title("👥 Gestão de Membros")
    aba1, aba2 = st.tabs(["Cadastrar Membro", "Visualizar Todos"])
    with aba1:
        with st.form("cadastro_membro"):
            nome = st.text_input("Nome Completo")
            tel = st.text_input("Telefone de Contato")
            cargo = st.selectbox("Cargo/Função", ["Membro", "Diácono", "Presbítero", "Pastor", "Líder de Ministério"])
            salvar = st.form_submit_button("Adicionar Membro")
            if salvar and nome:
                data_hoje = datetime.date.today().strftime("%d/%m/%Y")
                executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro) VALUES (:nome, :tel, :cargo, :data)",
                               {"nome": nome, "tel": tel, "cargo": cargo, "data": data_hoje})
                st.success("Membro registrado com sucesso!")
                st.rerun()
    with aba2:
        df_membros = consultar_db("SELECT id as ID, nome as Nome, telefone as Telefone, cargo as Cargo, data_cadastro as 'Data Cadastro' FROM membros")
        st.dataframe(df_membros, use_container_width=True)

def modulo_financeiro():
    st.title("💰 Controle Financeiro")
    aba1, aba2 = st.tabs(["Lançar Movimentação", "Fluxo de Caixa"])
    with aba1:
        with st.form("form_financeiro"):
            tipo = st.radio("Tipo de Lançamento", ["Entrada (Dízimo/Oferta)", "Saída (Despesa)"])
            desc = st.text_input("Descrição / Origem / Destino")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            lancar = st.form_submit_button("Confirmar Lançamento")
            if lancar and desc and valor > 0:
                tipo_limpo = "Entrada" if "Entrada" in tipo else "Saída"
                data_hoje = datetime.date.today().strftime("%d/%m/%Y")
                executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:tipo, :desc, :valor, :data)",
                               {"tipo": tipo_limpo, "desc": desc, "valor": valor, "data": data_hoje})
                st.success("Lançamento computado!")
                st.rerun()
    with aba2:
        df_fin = consultar_db("SELECT id as ID, tipo as Tipo, descricao as Descrição, valor as 'Valor (R$)', data as Data FROM financeiro ORDER BY id DESC")
        st.dataframe(df_fin, use_container_width=True)

def modulo_biblia():
    st.title("📖 Consulta Bíblica Integrada")
    col1, col2, col3 = st.columns(3)
    livro = col1.text_input("Livro (Ex: john, genesis, romans)", value="john")
    capitulo = col2.number_input("Capítulo", min_value=1, value=1, step=1)
    versiculo = col3.text_input("Versículo (Opcional)", value="")
    if st.button("Buscar na Palavra"):
        alvo = f"{livro}+{capitulo}:{versiculo}" if versiculo else f"{livro}+{capitulo}"
        try:
            r = requests.get(f"bible-api.com{alvo}")
            if r.status_code == 200:
                dados = r.json()
                st.markdown(f"### 📜 {dados['reference']}")
                st.info(dados['text'])
            else:
                st.error("Trecho não encontrado. Use nomes em inglês para a busca na API pública.")
        except Exception:
            st.error("Erro ao conectar à API da Bíblia.")

def modulo_louvores():
    st.title("🎵 Hinário e Louvores")
    aba1, aba2 = st.tabs(["Pesquisar Letras", "Adicionar Novo Louvor"])
    with aba1:
        busca = st.text_input("🔍 Digite o nome do louvor ou artista")
        if busca:
            df_l = consultar_db("SELECT * FROM louvores WHERE titulo LIKE :b OR artista LIKE :b", {"b": f"%{busca}%"})
        else:
            df_l = consultar_db("SELECT * FROM louvores")
        for _, louvor in df_l.iterrows():
            with st.expander(f"🎼 {louvor['titulo']} — {louvor['artista']}"):
                st.text(louvor['letra'])
    with aba2:
        with st.form("form_louvor"):
            t = st.text_input("Título da Canção")
            a = st.text_input("Ministério / Cantor")
            letra = st.text_area("Letra Completa", height=200)
            salvar_l = st.form_submit_button("Salvar Música")
            if salvar_l and t and letra:
                executar_query("INSERT INTO louvores (titulo, artista, letra) VALUES (:t, :a, :letra)",
                               {"t": t, "a": a, "letra": letra})
                st.success("Louvor adicionado ao acervo!")
                st.rerun()

def modulo_avisos():
    st.title("📢 Administração do Mural de Avisos")
    with st.form("novo_aviso"):
        titulo = st.text_input("Título do Comunicado")
        conteudo = st.text_area("Mensagem do Aviso")
        publicar = st.form_submit_button("Publicar no Painel Geral")
        if publicar and titulo and conteudo:
            data_hoje = datetime.date.today().strftime("%d/%m/%Y %H:%M")
            executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                           {"t": titulo, "c": conteudo, "d": data_hoje})
            st.success("Aviso publicado com sucesso!")
            st.rerun()

def modulo_chat():
    st.title("💬 Chat da Comunidade")
    st.markdown(f"""
    <iframe src="{URL_CHAT_RAILWAY}" width="100%" height="600" style="border:none; border-radius:16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"></iframe>
    """, unsafe_allow_html=True)

# --- 7. ROTEAMENTO NAVEGAÇÃO ---
opcao_menu = st.sidebar.radio("Navegação", [
    "Painel Geral", 
    "Gestão de Membros", 
    "Controle Financeiro", 
    "Consulta Bíblica", 
    "Louvores/Cânticos", 
    "Gerenciar Avisos", 
    "Chat em Tempo Real"
])

if opcao_menu == "Painel Geral":
    modulo_home()
elif opcao_menu == "Gestão de Membros":
    modulo_membros()
elif opcao_menu == "Controle Financeiro":
    modulo_financeiro()
elif opcao_menu == "Consulta Bíblica":
    modulo_biblia()
elif opcao_menu == "Louvores/Cânticos":
    modulo_louvores()
elif opcao_menu == "Gerenciar Avisos":
    modulo_avisos()
elif opcao_menu == "Chat em Tempo Real":
    modulo_chat()
