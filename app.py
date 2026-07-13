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
        # Busca automaticamente a variável de ambiente GEMINI_API_KEY do Streamlit
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
        except: 
            return pd.DataFrame()

# Criação inicial das tabelas do sistema
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

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

# --- 3. DICIONÁRIO BÍBLICO NATIVO AUTOMÁTICO ---
BIBLIA_ESTAVEL = {
    "Gênesis": {
        1: {
            1: "No princípio criou Deus os céus e a terra.", 
            2: "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo.", 
            3: "E disse Deus: Haja luz; e houve luz.", 
            4: "E viu Deus que era boa a luz; e fez Deus separação entre a luz e as trevas.", 
            5: "E Deus chamou à luz Dia; e às trevas chamou Noite."
        }
    },
    "Números": {
        4: {
            1: "Falou mais o Senhor a Moisés e a Arão, dizendo:", 
            2: "Toma a soma dos filhos de Coate, dentre os filhos de Levi...", 
            3: "Da idade de trinta anos para cima até aos cinquenta anos...", 
            4: "Este será o serviço dos filhos de Coate na tenda da congregação."
        }
    },
    "Salmos": {
        23: {
            1: "O Senhor é o meu pastor, nada me faltará.", 
            2: "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.", 
            3: "Refrigera a minha alma; guia-me pelas veredas da justiça.", 
            4: "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum.", 
            5: "Preparas uma mesa perante mim na presença dos meus inimigos.", 
            6: "Certamente que a bondade e a misericórdia me seguirão."
        }
    },
    "João": {
        3: {
            16: "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", 
            17: "Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo.", 
            18: "Quem crê nele não é condizido à condenação."
        }
    }
}

if "roteiro_culto" not in st.session_state:
    st.session_state.roteiro_culto = []

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
        "Início & Versículos", "Bíblia Completa & Filtro IA", "Comunhão Online (Jitsi)", 
        "Rádio Web & Transmissão", "Membros", "Cadastro de Visitantes", 
        "Escala de Cultos", "Escala de Visitas", "Financeiro & Dízimos Protegidos", 
        "Patrimônio da Igreja", "Avisos", "Louvores"
    ]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    # --- FUNÇÃO DE AUXÍLIO PARA RECOMENDAÇÃO DE LOUVORES VIA IA ---
    def sugerir_louvores_ia(texto_v, ref_v):
        if not client_gemini:
            return "Chave de IA (GEMINI_API_KEY) não configurada no ambiente para recomendações em tempo real."
        try:
            config = types.GenerateContentConfig(
                system_instruction=(
                    "Atue como um experiente diretor de culto e ministro de louvor. Com base no versículo fornecido, "
                    "sugira 3 louvores ou hinos populares no meio cristão evangélico brasileiro que combinem "
                    "perfeitamente com o tema central do texto. Seja breve na justificativa."
                ),
                temperature=0.4
            )
            prompt = f"Sugira louvores inspirados no versículo: {ref_v} - '{texto_v}'"
            response = client_gemini.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            return f"Não foi possível contactar a IA: {e}"

    # --- NOVO RECURSO: ANÁLISE EXEGÉTICA DO VERSÍCULO COMPLETO ---
    def analisar_versiculo_ia(texto_v, ref_v):
        if not client_gemini:
            return "Chave de IA não configurada."
        try:
            config = types.GenerateContentConfig(
                system_instruction=(
                    "Você é um teólogo cristão ortodoxo erudito. Faça um breve resumo exegético/devocional "
                    "do versículo enviado, explicando o contexto histórico e uma aplicação prática para a igreja hoje."
                ),
                temperature=0.3
            )
            prompt = f"Faça o estudo teológico do versículo: {ref_v} - '{texto_v}'"
            response = client_gemini.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            return f"Erro na análise: {e}"

    if escolha == "Início & Versículos":
