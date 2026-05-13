import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import redis
import requests

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONFIGURAÇÕES DE AMBIENTE (RAILWAY / UPSTASH) ---
URL_CHAT_RAILWAY = "railway.app"
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS ---
@st.cache_resource
def inicializar_conexoes():
    # Cria conexão persistente com o SQLite
    engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False})
    
    # Cria conexão com o Redis
    try:
        r_db = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        r_db = None
        
    return engine, r_db

engine, r_db = inicializar_conexoes()

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# --- 4. FUNÇÃO DE CARGA DA BÍBLIA ---
def carregar_biblia_completa():
    try:
        # URL exemplo de JSON bíblico estruturado em PT-BR
        url = "githubusercontent.com"
        resposta = requests.get(url, timeout=15)
        
        if resposta.status_code == 200:
            dados_totais = resposta.json()
            linhas_db = []
            
            for livro_dados in dados_totais:
                nome_livro = livro_dados.get("name")
                for c_idx, capitulo in enumerate(livro_dados.get("chapters", []), start=1):
                    for v_idx, versiculo in enumerate(capitulo, start=1):
                        linhas_db.append({
                            "livro": nome_livro,
                            "capitulo": c_idx,
                            "versiculo": v_idx,
                            "texto": versiculo
                        })
            
            df_biblia = pd.DataFrame(linhas_db)
            df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
            return True
    except Exception as e:
        st.error(f"Erro na carga: {e}")
        return False

# --- 5. INTERFACE DO USUÁRIO (STREAMLIT) ---
st.title("⛪ Portal Ágape")

abas = st.tabs(["📖 Bíblia Sagrada", "🎥 Vídeo Chat Premium", "⚙️ Configurações"])

with abas[0]:
    st.header("Leitura e Busca Bíblica")
    
    # Verifica se a tabela bíblia existe no banco
    verificar_tabela = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
    
    if verificar_tabela.empty:
        st.warning("A base de dados da Bíblia ainda não foi configurada.")
        if st.button("🚀 Baixar e Configurar Bíblia Agora"):
            with st.spinner("Carregando livros..."):
                if carregar_biblia_completa():
                    st.success("Bíblia carregada com sucesso! Atualize a página.")
    else:
        # Sistema de busca simples
        termo_busca = st.text_input("🔍 Digite uma palavra ou versículo para buscar:")
        if termo_busca:
            resultados = consultar_db(
                "SELECT livro, capitulo, versiculo, texto FROM biblia WHERE texto LIKE :busca LIMIT 50",
                {"busca": f"%{termo_busca}%"}
            )
            if not resultados.empty:
                st.dataframe(resultados, use_container_width=True)
            else:
                st.info("Nenhum resultado encontrado.")

with abas[1]:
    st.header("Sala de Transmissão Ágape")
    # Incorpora o seu app de chat do Railway diretamente aqui dentro
    st.components.v1.iframe(URL_CHAT_RAILWAY, height=650, scrolling=True)

with abas[2]:
    st.header("Status do Sistema")
    st.metric(label="Conexão Redis", value="Ativo" if r_db else "Inativo")
