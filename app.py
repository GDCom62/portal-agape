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

# --- 3. CONEXÕES COM BANCO DE DADOS ---
@st.cache_resource
def inicializar_conexoes():
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

# Inicialização de Tabelas
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT,
    nivel TEXT DEFAULT 'Membro'
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS membros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    telefone TEXT,
    cargo TEXT,
    data_cadastro TEXT,
    mes_aniversario TEXT
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    descricao TEXT,
    valor REAL,
    data TEXT,
    mes_ano TEXT
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
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", 
                       {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. ESTILIZAÇÃO CUSTOMIZADA (FUNDO AMARELO OURO PROFISSIONAL) ---
st.markdown("""
    <style>
    /* Fundo Geral do App em Amarelo Ouro com gradiente suave para leitura confortável */
    .stApp {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
    }
    /* Estilização dos blocos e containers brancos para alto contraste */
    .stMetric, div[data-testid="stMetricValue"], div[data-testid="metric-container"], .card-flutuante {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 16px !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.1) !important;
        border: 1px solid #e0a800 !important;
        color: #212529 !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .stMetric:hover, .card-flutuante:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.15) !important;
    }
    /* Botões robustos e arredondados */
    .stButton>button {
        border-radius: 12px !important;
        background-color: #212529 !important;
        color: #ffffff !important;
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover {
        background-color: #495057 !important;
        color: #FFD700 !important;
    }
    /* Ajustes de inputs */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {
        border-radius: 12px !important;
        background-color: #ffffff !important;
    }
    /* Caixa da Palavra do Dia */
    .versiculo-box {
        background: linear-gradient(135deg, #212529 0%, #000000 100%);
        color: #FFD700;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. DICIONÁRIO DE TRADUÇÃO PARA API DA BÍBLIA ---
TRADUCAO_LIVROS = {
    "genese": "genesis", "genesis": "genesis", "exodo": "exodus", "levitico": "leviticus",
    "numeros": "numbers", "deuteronomio": "deuteronomy", "josue": "joshua", "juizes": "judges",
    "rute": "ruth", "samuel": "samuel", "reis": "kings", "cronicas": "chronicles",
    "esdras": "ezra", "neemias": "nehemiah", "ester": "esther", "jo": "job",
    "salmos": "psalms", "proverbios": "proverbs", "eclesiastes": "ecclesiastes", "cantares": "song of solomon",
    "isaias": "isaiah", "jeremias": "jeremiah", "lamentacoes": "lamentations", "ezequiel": "ezekiel",
    "daniel": "daniel", "oseias": "hosea", "joel": "joel", "amos": "amos",
    "obadias": "obadiah", "jonas": "jonas", "miqueias": "micah", "naum": "nahum",
    "habacuque": "habakkuk", "sofonias": "zephaniah", "ageu": "haggai", "zacarias": "zechariah",
    "malaquias": "malachi", "mateus": "matthew", "marcos": "mark", "lucas": "lucas",
    "joao": "john", "atos": "acts", "romanos": "romans", "corintios": "corinthians",
    "galatas": "galatians", "efesios": "ephesians", "filipenses": "philippians", "colossenses": "colossians",
    "tessalonicenses": "thessalonians", "timoteo": "timothy", "tito": "titus", "filemon": "philemon",
    "hebreus": "hebrews", "tiago": "james", "pedro": "peter", "joao": "john",
    "judas": "jude", "apocalipse": "revelation"
}

def normalizar_livro(nome_livro):
    nome_limpo = nome_livro.lower().strip().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ç", "c")
    for chave, valor in TRADUCAO_LIVROS.items():
        if chave in nome_limpo:
            return valor
    return nome_limpo

# --- 6. AUTENTICAÇÃO E PERMISSÕES ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_atual = "Membro"

st.sidebar.title("🔐 Portal Ágape")

if not st.session_state.autenticado:
    with st.sidebar.form(key="form_login"):
        campo_usuario = st.text_input("E-mail/Usuário", value="admin@agape.com")
        campo_senha = st.text_input("Senha", type="password", value="agape2026")
        botao_entrar = st.form_submit_button("Entrar")
        if botao_entrar:
            df_u = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :user", {"user": campo_usuario})
            if not df_u.empty and check_password_hash(df_u.iloc[0]['senha'], campo_senha):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = campo_usuario
                st.session_state.nivel_atual = df_u.iloc[0]['nivel']
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha incorretos.")
    st.stop()
else:
    st.sidebar.write(f"Usuário: **{st.session_state.usuario_atual}**")
    st.sidebar.info(f"Acesso: {st.session_state.nivel_atual}")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.session_state.nivel_atual = "Membro"
        st.rerun()

def e_administrador():
    return st.session_state.nivel_atual in ["Pastor", "Admin"]

# --- 7. MÓDULOS DE GERENCIAMENTO ---

def obter_versiculo_do_dia():
    try:
        r = requests.get("bible-api.com", timeout=3)
        if r.status_code == 200:
            dados = r.json()
            return dados['text'], "João 3:16"
    except Exception:
        pass
    return "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "João 3:16"

def modulo_home():
    st.title("⛪ Painel Geral")
    
    texto_v, ref_v = obter_versiculo_do_dia()
    st.markdown(f"""
    <div class="versiculo-box">
        <h3>📖 Palavra de Agora</h3>
        <p style="font-size: 1.25rem; font-style: italic;">"{texto_v.strip()}"</p>
        <p style="text-align: right; font-weight: bold; margin-bottom: 0; color: #FFD700;">— {ref_v}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Métricas Gerais
    tot_membros = len(consultar_db("SELECT id FROM membros"))
    fin_dados = consultar_db("SELECT tipo, valor FROM financeiro")
    entradas = fin_dados[fin_dados['tipo'] == 'Entrada']['valor'].sum() if not fin_dados.empty else 0.0
    saidas = fin_dados[fin_dados['tipo'] == 'Saída']['valor'].sum() if not fin_dados.empty else 0.0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Membros Registrados", f"{tot_membros}")
    col2.metric("Caixa Atual", f"R$ {entradas - saidas:,.2f}")
    col3.metric("Sessão Redis", "Ativa" if r_db else "Local")

    # Aniversariantes do Mês
    st.subheader("🎂 Aniversariantes do Mês Atual")
    mes_atual_nome = datetime.date.today().strftime("%B")
    df_niver = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :mes", {"mes": mes_atual_nome})
    if not df_niver.empty:
        for _, niver in df_niver.iterrows():
            st.markdown(f"🎁 **{niver['nome']}** ({niver['cargo']})")
    else:
        st.info("Nenhum aniversariante registrado para este mês.")

    # Mural de Avisos
    st.subheader("📢 Últimos Comunicados Fixados")
    df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC LIMIT 2")
    if not df_avisos.empty:
        for _, aviso in df_avisos.iterrows():
            st.markdown(f"""
            <div class="card-flutuante">
                <h4>📌 {aviso['titulo']}</h4>
                <p style="color: #666; font-size: 0.8rem;">Data de publicação: {aviso['data']}</p>
                <p>{aviso['conteudo']}</p>
            </div>
            """, unsafe_allow_html=True)

def modulo_membros():
    st.title("👥 Gestão Integrada de Membros")
    aba1, aba2 = st.tabs(["Lista de Membros", "Registrar Novo"])
    
    with aba1:
        df_membros = consultar_db("SELECT id, nome as Nome, telefone as Telefone, cargo as Cargo, mes_aniversario as Aniversário FROM membros")
        st.dataframe(df_membros, use_container_width=True)
        if not df_membros.empty:
            st.download_button("📥 Baixar Cadastro (CSV)", df_membros.to_csv(index=False).encode('utf-8'), "membros.csv")
            
    with aba2:
        if e_administrador():
            with st.form("form_membro"):
                nome = st.text_input("Nome Completo")
                tel = st.text_input("Telefone")
                cargo = st.selectbox("Função Ministerial", ["Membro", "Diácono", "Presbítero", "Pastor", "Líder"])
                mes_niver = st.selectbox("Mês de Aniversário", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
                if st.form_submit_button("Salvar Membro") and nome:
                    hoje = datetime.date.today().strftime("%d/%m/%Y")
                    executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario) VALUES (:n, :t, :c, :d, :m)",
                                   {"n": nome, "t": tel, "c": cargo, "d": hoje, "m": mes_niver})
                    st.success("Cadastro efetuado!")
                    st.rerun()
        else:
            st.warning("Apenas administradores podem cadastrar.")

def modulo_financeiro():
    st.title("💰 Movimentações Financeiras")
    
    # Filtro por Mês/Ano
    df_filtros = consultar_db("SELECT DISTINCT mes_ano FROM financeiro")
    lista_meses = ["Todos"] + df_filtros['mes_ano'].tolist() if not df_filtros.empty else ["Todos"]
    mes_sel = st.selectbox("Filtrar por Mês", lista_meses)
    
    if mes_sel == "Todos":
        df_fin = consultar_db("SELECT id, tipo as Tipo, descricao as Descrição, valor as Valor, data as Data FROM financeiro ORDER BY id DESC")
    else:
        df_fin = consultar_db("SELECT id, tipo as Tipo, descricao as Descrição, valor as Valor, data as Data FROM financeiro WHERE mes_ano = :m ORDER BY id DESC", {"m": mes_sel})
        
    st.dataframe(df_fin, use_container_width=True)
    
    if e_administrador():
        with st.expander("💸 Lançar Nova Entrada/Saída"):
            with st.form("form_fin"):
                tipo = st.radio("Tipo", ["Entrada", "Saída"])
                desc = st.text_input("Histórico / Descrição")
                val = st.number_input("Valor (R$)", min_value=0.0)
                if st.form_submit_button("Gravar Transação") and desc and val > 0:
                    hoje = datetime.date.today()
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano) VALUES (:t, :desc, :v, :d, :ma)",
                                   {"t": tipo, "desc": desc, "v": val, "d": hoje.strftime("%d/%m/%Y"), "ma": hoje.strftime("%m/%Y")})
                    st.success("Lançamento adicionado!")
                    st.rerun()

def modulo_biblia():
    st.title("📖 API da Bíblia Sagrada")
    col1, col2, col3 = st.columns([2, 1, 1])
    livro_pt = col1.text_input("Livro (Ex: Joao, Genesis, Lucas)", value="Joao")
    cap = col2.number_input("Capítulo", min_value=1, value=1)
    ver = col3.text_input("Versículo (Opcional)", value="")
    
    if st.button("Consultar Escrituras"):
        livro_en = normalizar_livro(livro_pt)
        alvo = f"{livro_en}+{cap}:{ver}" if ver else f"{livro_en}+{cap}"
        
        try:
            # Consome a API pública estável sem necessidade de Token/Chaves complexas
            r = requests.get(f"bible-api.com{alvo}", timeout=5)
            if r.status_code == 200:
                dados = r.json()
                st.markdown(f"### 📜 {livro_pt.title()} {cap}")
                st.info(dados['text'])
            else:
                st.error("Trecho não localizado na API. Certifique-se de escrever o nome do livro corretamente.")
        except Exception:
            st.error("Falha ao contatar servidor de dados da Bíblia.")

def modulo_louvores():
    st.title("🎵 Acervo Digital de Louvores")
    aba1, aba2 = st.tabs(["Pesquisar Hinos", "Cadastrar Novo Louvor"])
    
    with aba1:
        busca = st.text_input("🔍 Buscar por título ou artista")
        if busca:
            df_l = consultar_db("SELECT * FROM louvores WHERE titulo LIKE :b OR artista LIKE :b", {"b": f"%{busca}%"})
        else:
            df_l = consultar_db("SELECT * FROM louvores")
            
        for _, louvor in df_l.iterrows():
            with st.expander(f"🎼 {louvor['titulo']} — {louvor['artista']}"):
                st.text(louvor['letra'])
                
    with aba2:
        if e_administrador():
            with st.form("form_louvor"):
                t = st.text_input("Título")
                a = st.text_input("Ministério / Cantor")
                letra = st.text_area("Letra Completa", height=200)
                if st.form_submit_button("Salvar no Acervo") and t and letra:
                    executar_query("INSERT INTO louvores (titulo, artista, letra) VALUES (:t, :a, :l)", {"t": t, "a": a, "l": letra})
                    st.success("Louvor indexado com sucesso!")
                    st.rerun()

def modulo_avisos():
    st.title("📢 Gerenciador do Quadro de Avisos")
    if e_administrador():
        with st.form("novo_aviso"):
            t = st.text_input("Título do Comunicado")
            c = st.text_area("Mensagem")
            if st.form_submit_button("Publicar Mural") and t and c:
                data = datetime.date.today().strftime("%d/%m/%Y %H:%M")
                executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", {"t": t, "c": c, "d": data})
                st.success("Aviso fixado no Painel!")
                st.rerun()

def modulo_chat():
    st.title("💬 Chat em Tempo Real (Liderança e Pastores)")
    st.write("Módulo de comunicação operacional interna rodando em contêiner dedicado.")
    
    # Renderização via iframe com proteção contra falhas de conexão externa
    st.markdown(f"""
    <iframe src="{URL_CHAT_RAILWAY}" width="100%" height="600" style="border:3px solid #212529; border-radius:16px; background-color: #ffffff; box-shadow: 0 8px 24px rgba(0,0,0,0.2);"></iframe>
    """, unsafe_allow_html=True)

# --- 8. ROTAS DE MENU ---
opcao_menu = st.sidebar.radio("Navegação Principal", [
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
