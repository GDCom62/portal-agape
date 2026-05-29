import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

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
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
executar_query("CREATE TABLE IF NOT EXISTS escalas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ministerio TEXT, voluntario TEXT, periodo TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS escalas_visitas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, irmao_visitado TEXT, endereço TEXT, responsavel TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS visitantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, data_visita TEXT, observacoes TEXT, precisa_visita TEXT DEFAULT 'Não');")
executar_query("CREATE TABLE IF NOT EXISTS patrimonio (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, quantidade INTEGER, valor REAL, estado TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, objetivo TEXT, valor_alvo REAL, arrecadado REAL DEFAULT 0.0);")

# Garante o usuário Administrador padrão
admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

# --- 3. PROVEDOR INTERNO DA BÍBLIA (BANCO SQL LOCAL) ---
def extrair_dados_da_biblia():
    """Busca os dados do banco local mapeando colunas dinamicamente para evitar travamentos"""
    tabelas = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('versiculos', 'bible', 'biblia', 'texto_biblico')")
    if tabelas.empty:
        return pd.DataFrame(), "", "", "", ""
    
    tab_nome = str(tabelas.iloc[0, 0])
    info_cols = consultar_db(f"PRAGMA table_info([{tab_nome}])")
    cols = info_cols['name'].tolist() if not info_cols.empty else []
    
    c_livro = 'livro' if 'livro' in cols else ('livro_nome' if 'livro_nome' in cols else (cols[1] if len(cols) > 1 else ''))
    c_cap = 'capitulo' if 'capitulo' in cols else ('cap' if 'cap' in cols else (cols[2] if len(cols) > 2 else ''))
    c_ver = 'versiculo' if 'versiculo' in cols else ('ver' if 'ver' in cols else (cols[3] if len(cols) > 3 else ''))
    c_txt = 'texto' if 'texto' in cols else ('txt' if 'txt' in cols else (cols[4] if len(cols) > 4 else ''))
    
    df_livros = consultar_db(f"SELECT DISTINCT [{c_livro}] as livro_nome FROM [{tab_nome}] ORDER BY rowid ASC")
    return df_livros, tab_nome, c_livro, c_cap, c_ver, c_txt

# --- 4. ESTILIZAÇÃO VISUAL ---
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
            for idx, row in df_aniv.iterrows(): 
                st.info(f"🎂 **{row['nome']}** ({row['cargo']})")
        else: 
            st.caption("Nenhum aniversário registrado para este mês.")
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Completa (Módulo Offline de Alta Performance)")
        
        # Rotina de Verificação e Importação Local do arquivo biblia.sql
        nome_src_sql = "biblia.sql"
        tabelas_existentes = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('versiculos', 'bible', 'biblia', 'texto_biblico')")
        
        if tabelas_existentes.empty and os.path.exists(nome_src_src := nome_src_sql):
            st.warning("📦 O arquivo `biblia.sql` foi localizado! Clique abaixo para carregar todos os livros permanentemente offline.")
            if st.button("⚡ Sincronizar e Indexar Bíblia Completa"):
                with st.spinner("Estruturando os 66 livros no banco de dados local... Isso levará apenas alguns segundos."):
                    try:
                        with open(nome_src_src, "r", encoding="utf-8", errors="ignore") as f:
                            linhas = f.readlines()
                        
                        query_acumulada = ""
                        for linha in linhas:
                            l_limpa = linha.strip()
                            if not l_limpa or l_limpa.startswith("--") or l_limpa.startswith("/*"):
                                continue
                            query_acumulada += " " + l_limpa
                            if query_acumulada.endswith(";"):
                                q_final = query_acumulada.replace("unsigned int", "INTEGER").replace("unsigned", "").replace("UNSIGNED", "")
                                if not q_final.startswith("LOCK") and not q_final.startswith("UNLOCK"):
                                    executar_query(q_final)
                                query_acumulada = ""
                        st.success("🎉 Todos os 66 livros foram sincronizados com sucesso!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Erro durante a leitura do arquivo SQL: {ex}")
        
