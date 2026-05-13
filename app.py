import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import requests

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONFIGURAÇÕES DE AMBIENTE ---
URL_CHAT_RAILWAY = "railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS ---
@st.cache_resource
def inicializar_conexoes():
    engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False})
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

# Criação inicial da tabela de usuários se não existir
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT
);
""")

# --- 4. GERENCIAMENTO DE ESTADO DE LOGIN (SESSION STATE) ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "usuario_atual" not in st.session_state:
    st.session_state.usuario_atual = None

# --- 5. FUNÇÃO DE CARGA DA BÍBLIA ---
# --- 5. FUNÇÃO DE CARGA DA BÍBLIA CORRIGIDA ---
def carregar_biblia_completa():
    try:
        # URL real, pública e com o protocolo HTTPS obrigatório
        url = "githubusercontent.com"
        resposta = requests.get(url, timeout=20)
        
        if resposta.status_code == 200:
            dados_totais = resposta.json()  # Lista de livros
            linhas_db = []
            
            for livro_dados in dados_totais:
                # Captura o nome do livro (ex: "Gênesis")
                nome_livro = livro_dados.get("name", "Desconhecido")
                
                # Itera pelos capítulos e versículos do JSON
                for c_idx, capitulo in enumerate(livro_dados.get("chapters", []), start=1):
                    for v_idx, versiculo in enumerate(capitulo, start=1):
                        linhas_db.append({
                            "livro": nome_livro,
                            "capitulo": int(c_idx),
                            "versiculo": int(v_idx),
                            "texto": str(versiculo)
                        })
            
            if linhas_db:
                df_biblia = pd.DataFrame(linhas_db)
                df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
                return True
        return False
    except Exception as e:
        st.error(f"Erro técnico na carga da Bíblia: {e}")
        return False


# --- 6. FLUXO DE TELAS (LOGIN OU PORTAL) ---

if not st.session_state.logado:
    # --- TELA DE LOGIN ---
    st.markdown("<h2 style='text-align: center;'>⛪ Portal Ágape - Autenticação</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        aba_auth = st.tabs(["🔐 Entrar", "📝 Cadastrar Nova Conta"])
        
        with aba_auth[0]:
            username = st.text_input("Usuário", key="login_user")
            password = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Acessar Portal", use_container_width=True):
                res = consultar_db("SELECT senha FROM usuarios WHERE usuario = :user", {"user": username})
                if not res.empty and check_password_hash(res.iloc[0]["senha"], password):
                    st.session_state.logado = True
                    st.session_state.usuario_atual = username
                    st.success(f"Bem-vindo, {username}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
                    
        with aba_auth[1]:
            new_username = st.text_input("Escolha um Usuário", key="reg_user")
            new_password = st.text_input("Escolha uma Senha", type="password", key="reg_pass")
            
            if st.button("Criar Conta", use_container_width=True):
                if new_username and new_password:
                    # Verifica se usuário já existe
                    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": new_username})
                    if existe.empty:
                        hash_senha = generate_password_hash(new_password)
                        executar_query("INSERT INTO usuarios (usuario, senha) VALUES (:user, :senha)", 
                                       {"user": new_username, "senha": hash_senha})
                        st.success("Conta criada com sucesso! Faça login na aba ao lado.")
                    else:
                        st.error("Este nome de usuário já está em uso.")
                else:
                    st.warning("Preencha todos os campos.")

else:
    # --- PAINEL PRINCIPAL (LOGADO) ---
    # Barra Superior com informações do usuário e botão de sair
    col_tit, col_user = st.columns([8, 2])
    with col_tit:
        st.title("⛪ Portal Ágape")
    with col_user:
        st.markdown(f"👤 **{st.session_state.usuario_atual}**")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

    # Criação das Abas Principais do Portal
    aba1, aba2, aba3 = st.tabs(["📖 Bíblia Sagrada", "🎥 Vídeo Chat Premium", "⚙️ Painel do Sistema"])

    # ABA 1: BÍBLIA SAGRADA
    with aba1:
        st.header("Leitura e Busca Bíblica")
        
        # Verifica no banco SQLite se a tabela da bíblia está criada e povoada
        tabela_existe = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
        
        if tabela_existe.empty:
            st.info("A base de dados da Bíblia ainda não foi sincronizada localmente.")
            if st.button("🚀 Baixar e Sincronizar Bíblia Agora", use_container_width=True):
                with st.spinner("Conectando ao repositório e estruturando os 66 livros... Aguarde."):
                    if carregar_biblia_completa():
                        st.success("Bíblia Sagrada integrada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao baixar os dados. Verifique sua conexão.")
        else:
            # Mecanismo de pesquisa por palavra-chave ou termo
            busca = st.text_input("🔍 O que você deseja buscar na palavra? (Ex: Jesus, Fé, Amor):")
            
            if busca:
                resultados = consultar_db(
                    "SELECT livro AS 'Livro', capitulo AS 'Capítulo', versiculo AS 'Versículo', texto AS 'Texto' FROM biblia WHERE texto LIKE :busca LIMIT 100",
                    {"busca": f"%{busca}%"}
                )
                if not resultados.empty:
                    st.subheader(f"Encontrados {len(resultados)} versículos:")
                    st.dataframe(resultados, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum versículo contendo este termo foi encontrado.")
            else:
                # Exibe um livro padrão caso não haja busca para a tela não sumir ou ficar em branco
                st.markdown("---")
                st.caption("Sugestão de Leitura: Gênesis Capítulo 1")
                exemplo = consultar_db("SELECT capitulo, versiculo, texto FROM biblia WHERE livro = 'Gênesis' AND capitulo = 1 LIMIT 5")
                if not exemplo.empty:
                    for idx, row in exemplo.iterrows():
                        st.write(f"**{row['versiculo']}.** {row['texto']}")

    # ABA 2: VÍDEO CHAMADA PREMIUM
    with aba2:
        st.header("Sala de Conferência Ágape")
        st.caption("Abaixo está a sua sala de vídeo ao vivo integrada diretamente do Railway.")
        
        # Uso do iframe isolado dentro da aba para evitar que a tela repita ou dê loop com o login
        st.components.v1.iframe(URL_CHAT_RAILWAY, height=700, scrolling=True)

    # ABA 3: STATUS DO SISTEMA
    with aba3:
        st.header("Status das Instâncias e Conexões")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="Persistência Cache (Redis)", value="⚡ Conectado" if r_db else "⚠️ Desconectado")
        with col_m2:
            total_usuarios = consultar_db("SELECT COUNT(*) AS total FROM usuarios")
            st.metric(label="Usuários Cadastrados", value=int(total_usuarios.iloc[0]["total"]) if not total_usuarios.empty else 0)
