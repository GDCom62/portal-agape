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

# Garantir estrutura correta da tabela
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT
);
""")

# --- 4. GERENCIAMENTO DE ESTADO DE LOGIN ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "usuario_atual" not in st.session_state:
    st.session_state.usuario_atual = None

# --- 5. FUNÇÃO DE CARGA DA BÍBLIA ---
def carregar_biblia_completa():
    try:
        url = "githubusercontent.com"
        resposta = requests.get(url, timeout=20)
        
        if resposta.status_code == 200:
            dados_totais = resposta.json()
            linhas_db = []
            
            for livro_dados in dados_totais:
                nome_livro = livro_dados.get("name", "Desconhecido")
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

# --- 6. FLUXO DE TELAS ---
if not st.session_state.logado:
    st.markdown("<h2 style='text-align: center;'>⛪ Portal Ágape - Autenticação</h2>", unsafe_allow_html=True)
    
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        # CORREÇÃO CRÍTICA: Separando a lista retornada em duas variáveis distintas
        aba_login, aba_cadastro = st.tabs(["🔐 Entrar", "📝 Cadastrar Nova Conta"])
        
        with aba_login:
            username = st.text_input("Usuário", key="login_user").strip()
            password = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Acessar Portal", use_container_width=True):
                if username and password:
                    res = consultar_db("SELECT senha FROM usuarios WHERE usuario = :user", {"user": username})
                    
                    if not res.empty:
                        # Extração segura da string hash do DataFrame
                        senha_hash_banco = str(res.iloc[0]['senha'])
                        
                        if check_password_hash(senha_hash_banco, password):
                            st.session_state.logado = True
                            st.session_state.usuario_atual = username
                            st.success(f"Bem-vindo, {username}!")
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                    else:
                        st.error("Usuário ou senha incorretos.")
                else:
                    st.warning("Por favor, preencha todos os campos.")
                    
        with aba_cadastro:
            new_username = st.text_input("Escolha um Usuário", key="reg_user").strip()
            new_password = st.text_input("Escolha uma Senha", type="password", key="reg_pass")
            
            if st.button("Criar Conta", use_container_width=True):
                if new_username and new_password:
                    if len(new_password) < 4:
                        st.error("A senha precisa ter pelo menos 4 caracteres.")
                    else:
                        existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": new_username})
                        if existe.empty:
                            hash_senha = generate_password_hash(new_password, method="scrypt")
                            executar_query("INSERT INTO usuarios (usuario, senha) VALUES (:user, :senha)", 
                                           {"user": new_username, "senha": hash_senha})
                            st.success("Conta criada com sucesso! Acesse a aba 'Entrar' para fazer o login.")
                        else:
                            st.error("Este nome de usuário já está em uso.")
                else:
                    st.warning("Preencha todos os campos.")
else:
    col_tit, col_user = st.columns([3, 1])
    with col_tit:
        st.title("⛪ Portal Ágape")
    with col_user:
        st.markdown(f"👤 Logado como: **{st.session_state.usuario_atual}**")
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.logado = False
            st.session_state.usuario_atual = None
            st.rerun()

    aba1, aba2, aba3 = st.tabs(["📖 Bíblia Sagrada", "🎥 Vídeo Chat Premium", "⚙️ Painel do Sistema"])

    with aba1:
        st.header("Leitura e Busca Bíblica")
        tabela_existe = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
        
        if tabela_existe.empty:
            st.info("A base de dados da Bíblia ainda não foi sincronizada localmente.")
            if st.button("🚀 Baixar e Sincronizar Bíblia Agora", use_container_width=True):
                with st.spinner("Sincronizando os 66 livros... Aguarde."):
                    if carregar_biblia_completa():
                        st.success("Bíblia Sagrada integrada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Falha ao baixar os dados. Verifique a URL ou sua conexão.")
        else:
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
                st.markdown("---")
                st.caption("Sugestão de Leitura: Gênesis Capítulo 1")
                exemplo = consultar_db("SELECT capitulo, versiculo, texto FROM biblia WHERE livro = 'Gênesis' AND capitulo = 1 LIMIT 5")
                if not exemplo.empty:
                    for idx, row in exemplo.iterrows():
                        st.write(f"**{row['versiculo']}.** {row['texto']}")

    with aba2:
        st.header("Sala de Conferência Ágape")
        st.caption("Conexão direta com a sala de vídeo oficial.")
        st.html(f'<iframe src="{URL_CHAT_RAILWAY}" width="100%" height="700" style="border:none;" scrolling="yes"></iframe>')

    with aba3:
        st.header("Status das Instâncias e Conexões")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="Persistência Cache (Redis)", value="⚡ Conectado" if r_db else "⚠️ Desconectado")
        with col_m2:
            total_usuarios = consultar_db("SELECT COUNT(*) AS total FROM usuarios")
            st.metric(label="Usuários Cadastrados", value=int(total_usuarios.iloc[0]['total']) if not total_usuarios.empty else 0)
