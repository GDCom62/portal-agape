import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONEXÃO BANCO DE DADOS LOCAL ---
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

# Criar tabelas necessárias do sistema
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
executar_query("CREATE TABLE IF NOT EXISTS texto_biblico (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

# --- 3. CARGA AUTOMÁTICA DA BÍBLIA INTEIRA (OFFLINE DEFINITIVO) ---
@st.cache_resource
def baixar_e_instalar_biblia():
    # Verifica se a tabela da bíblia local já possui os dados carregados
    check_base = consultar_db("SELECT id FROM texto_biblico LIMIT 1")
    if check_base.empty:
        try:
            # Baixa uma cópia compacta em JSON da Bíblia Almeida (NVI/AA) livre de bloqueios
            url_json = "https://githubusercontent.com"
            resposta = requests.get(url_json, timeout=10)
            if resposta.status_code == 200:
                dados_biblia = resposta.json()
                # Insere os dados estruturados no banco local
                with engine.begin() as conn:
                    for livro_dados in dados_biblia:
                        nome_livro = livro_dados["name"]
                        for cap_idx, capitulo in enumerate(livro_dados["chapters"]):
                            for ver_idx, versiculo_texto in enumerate(capitulo):
                                conn.execute(
                                    text("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"),
                                    {"l": nome_livro, "c": cap_idx + 1, "v": ver_idx + 1, "t": versiculo_texto}
                                )
                return True
        except Exception as e:
            st.error(f"Aviso de sincronização inicial: {str(e)}")
    return True

# Dispara a verificação em segundo plano
baixar_e_instalar_biblia()

# Sincronizar dados do Admin padrão
admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

# --- 4. DESIGN CUSTOMIZADO EM AMARELO OURO ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 25px; border-radius: 12px; border: 1px solid #e0a800; color: #212529 !important; }
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

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        df_v_dia = consultar_db("SELECT texto, livro, capitulo, versiculo FROM texto_biblico WHERE livro LIKE '%João%' AND capitulo = 3 AND versiculo = 16")
        if not df_v_dia.empty:
            st.markdown(f'<div class="versiculo-box"><h4>"{df_v_dia.loc[0, "texto"]}"</h4><span style="color:#fff;">— {df_v_dia.loc[0, "livro"]} {df_v_dia.loc[0, "capitulo"]}:{df_v_dia.loc[0, "versiculo"]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira..."</h4><span style="color:#fff;">— João 3:16 (Carregando Base...)</span></div>', unsafe_allow_html=True)
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    # --- ABA ATUALIZADA: BÍBLIA COMPLETA COM BUSCA POR PALAVRA-CHAVE ---
    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Offline & Pesquisa")
        
        modo_leitura = st.radio("Escolha o modo:", ["Leitura por Capítulo", "Pesquisar por Palavra-Chave"], horizontal=True)
        
        if modo_leitura == "Leitura por Capítulo":
            # Lista dinâmica de livros baseada nos dados reais injetados no banco
            df_livros = consultar_db("SELECT DISTINCT livro FROM texto_biblico ORDER BY id ASC")
            lista_livros = df_livros["livro"].tolist() if not df_livros.empty else ["Gênesis", "Êxodo", "Salmos", "João", "Apocalipse"]
            
            c1, c2 = st.columns(2)
            l_nome = c1.selectbox("Selecione o Livro:", lista_livros)
            c_num = c2.number_input("Selecione o Capítulo:", min_value=1, max_value=150, value=1, step=1)
            
            if st.button("📖 Abrir Capítulo Completo", use_container_width=True):
                df_local = consultar_db("SELECT versiculo, texto FROM texto_biblico WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": l_nome, "c": c_num})
                if not df_local.empty:
                    html = f"<div class='leitura-box'><h4>📜 {l_nome} — Capítulo {c_num}</h4><br>"
                    for i, r in df_local.iterrows(): 
                        html += f"<p><b style='color:#FFA500;'>{r['versiculo']}.</b> {r['texto']}</p>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.warning("Aguarde a sincronização inicial do banco de dados terminar ou certifique-se de que o capítulo digitado existe.")
                    
        else:
            # SISTEMA DE PALAVRA-CHAVE SOLICITADO
            termo_busca = st.text_input("Digite a palavra ou frase que deseja encontrar na Bíblia:").strip()
            if termo_busca:
                # Query otimizada que varre todos os 31 mil versículos instantaneamente localizados no SQLite
                df_busca = consultar_db("SELECT livro, capitulo, versiculo, texto FROM texto_biblico WHERE texto LIKE :t LIMIT 50", {"t": f"%{termo_busca}%"})
                
                if not df_busca.empty:
                    st.success(f"Foram encontrados resultados para '{termo_busca}' (Exibindo até 50 correspondências):")
                    for i, r in df_busca.iterrows():
                        st.markdown(f"""
                        <div class="leitura-box" style="margin-bottom:12px;">
                            <span style="color:#FFA500; font-weight:bold;">📖 {r['livro']} {r['capitulo']}:{r['versiculo']}</span><br>
                            <p style="margin-top:5px; font-style:italic;">"{r['texto']}"</p>
