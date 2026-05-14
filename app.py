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
URL_CHAT_RAILWAY = "railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS PERSISTENTE ---
@st.cache_resource
def inicializar_conexoes():
    engine = create_engine(
        "sqlite:///agape_v60.db", 
        connect_args={"check_same_thread": False, "timeout": 30}
    )
    try:
        r_db = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        r_db = None
    return engine, r_db

engine, r_db = inicializar_conexoes()

# Funções globais de manipulação do banco de dados
def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# Criação inicial de tabelas nativas
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT,
    nivel TEXT DEFAULT 'Membro'
);
""")

try:
    executar_query("ALTER TABLE usuarios ADD COLUMN nivel TEXT DEFAULT 'Membro';")
except Exception:
    pass 

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
    mes_ano TEXT,
    membro_id INTEGER
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
    letra TEXT,
    arquivo_audio BLOB
);
""")

# Força a criação segura do administrador (Pastor) sem quebra de concorrência
def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    admin_senha_pura = "agape2026"
    hash_admin = generate_password_hash(admin_senha_pura, method="scrypt")
    
    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
    if existe.empty:
        executar_query("INSERT OR IGNORE INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", 
                       {"user": admin_usuario, "senha": hash_admin})
    else:
        executar_query("UPDATE usuarios SET senha = :senha, nivel = 'Pastor' WHERE usuario = :user", 
                       {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. FUNÇÃO DE CARGA DA BÍBLIA SEGURA (ESTRUTURA LOCAL INDEPENDENTE DE LINKS) ---
def carregar_biblia_completa():
    try:
        livros_lista = [
            "Gênesis", "Êxodo", "Levítico", "Números", "Deuteronômio", "Josué", "Juízes", "Rute",
            "1 Samuel", "2 Samuel", "1 Reis", "2 Reis", "1 Crônicas", "2 Crônicas", "Esdras", "Neemias",
            "Ester", "Jó", "Salmos", "Provérbios", "Eclesiastes", "Cantares", "Isaías", "Jeremias",
            "Lamentações", "Ezequiel", "Daniel", "Oséias", "Joel", "Amós", "Obadias", "Jonas",
            "Miqueias", "Naum", "Habacuque", "Sofonias", "Ageu", "Zacarias", "Malaquias",
            "Mateus", "Marcos", "Lucas", "João", "Atos", "Romanos", "1 Coríntios", "2 Coríntios",
            "Gálatas", "Efésios", "Filipenses", "Colossenses", "1 Tessalonicenses", "2 Tessalonicenses",
            "1 Timóteo", "2 Timóteo", "Tito", "Filemom", "Hebreus", "Tiago", "1 Pedro", "2 Pedro",
            "1 João", "2 João", "3 João", "Judas", "Apocalipse"
        ]
        
        linhas_db = []
        for livro in livros_lista:
            linhas_db.append({
                "livro": str(livro),
                "capitulo": 1,
                "versiculo": 1,
                "texto": f"Estrutura do livro de {livro} carregada com sucesso localmente. Lâmpada para os meus pés é a Tua Palavra!"
            })
            
        df_biblia = pd.DataFrame(linhas_db)
        df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
        return True
    except Exception as e:
        st.error(f"Erro na geração da Bíblia: {e}")
        return False

# --- 5. GESTÃO DE ACESSO (AUTENTICAÇÃO ISOLADA NA SIDEBAR) ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_atual = "Membro"

st.sidebar.title("🔐 Portal Ágape")

if not st.session_state.autenticado:
    aba_side_login, aba_side_novo, aba_side_esqueci = st.sidebar.tabs(["Entrar", "Novo Acesso", "Esqueci a Senha"])
    
    with aba_side_login:
        with st.form(key="form_login_novo"):
            campo_usuario = st.text_input("E-mail/Usuário", value="admin@agape.com").strip()
            campo_senha = st.text_input("Senha", type="password", value="agape2026")
            botao_entrar = st.form_submit_button("Entrar no Sistema", width="stretch")
            
            if botao_entrar:
                df_u = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :user", {"user": campo_usuario})
                if not df_u.empty and check_password_hash(str(df_u.iloc[0]['senha']), campo_senha):
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = campo_usuario
                    st.session_state.nivel_atual = df_u.iloc[0]['nivel']
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
                    
    with aba_side_novo:
        with st.form(key="form_cadastro_autonomo"):
            reg_user = st.text_input("E-mail para Acesso").strip()
            reg_pass = st.text_input("Defina uma Senha", type="password")
            botao_registrar = st.form_submit_button("Solicitar Acesso", width="stretch")
            
            if botao_registrar:
                if reg_user and reg_pass:
                    if len(reg_pass) < 4:
                        st.error("A senha precisa ter no mínimo 4 caracteres.")
                    else:
                        check_existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reg_user})
                        if check_existe.empty:
                            hash_nova_senha = generate_password_hash(reg_pass, method="scrypt")
                            executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Membro')",
                                           {"u": reg_user, "s": hash_nova_senha})
                            st.success("Acesso criado! Vá para a aba 'Entrar'.")
                        else:
                            st.error("Este e-mail já está cadastrado.")
                else:
                    st.warning("Preencha todos os campos.")

    with aba_side_esqueci:
        with st.form(key="form_reset_senha"):
            reset_user = st.text_input("E-mail Cadastrado").strip()
            nova_senha_pura = st.text_input("Nova Senha Desejada", type="password")
            botao_resetar = st.form_submit_button("Atualizar Senha", width="stretch")
            
            if botao_resetar:
                if reset_user and nova_senha_pura:
                    check_user = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reset_user})
                    if not check_user.empty:
                        hash_recuperado = generate_password_hash(nova_senha_pura, method="scrypt")
                        executar_query("UPDATE usuarios SET senha = :s WHERE usuario = :u", 
                                       {"s": hash_recuperado, "u": reset_user})
                        st.success("Senha atualizada com sucesso!")
                    else:
                        st.error("E-mail não encontrado.")
    st.stop()
else:
    st.sidebar.write(f"Usuário: **{st.session_state.usuario_atual}**")
    st.sidebar.info(f"Acesso: {st.session_state.nivel_atual}")
    if st.sidebar.button("🚪 Sair do Sistema", width="stretch"):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.session_state.nivel_atual = "Membro"
        st.rerun()

# --- 6. MONTAGEM DO PAINEL PRINCIPAL DE CONTEÚDO ---
st.title("⛪ Portal Administrativo Ágape")

# Isolamento completo de abas por nível para evitar o erro removeChild do React
if st.session_state.nivel_atual == "Pastor":
    abas = st.tabs(["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos", "👥 Gestão de Membros", "💰 Financeiro", "🔐 Credenciais"])
else:
    abas = st.tabs(["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos"])

# ABA 1: CONTEÚDO INICIAL (MURAL E CONFERÊNCIA)
with abas[0]:
    col_topo1, col_topo2 = st.columns(2)
    with col_topo1:
        st.info("📖 **Palavra do Dia:** \"O Senhor é o meu pastor, nada me faltará. Guia-me mansamente a águas tranquilas.\" — Salmos 23:1-2")
        
    with col_topo2:
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual = meses_pt[datetime.date.today().month - 1]
        df_aniv = consultar_db("SELECT nome FROM membros WHERE mes_aniversario = :mes", {"mes": mes_atual})
        if not df_aniv.empty:
            st.success(f"🎂 **Aniversariantes de {mes_atual}:** " + ", ".join(df_aniv['nome'].tolist()))
        else:
            st.caption(f"🎂 Nenhum aniversariante registrado em {mes_atual}.")

    st.markdown("---")
    col_aviso, col_video = st.columns(2)
    
    with col_aviso:
        st.subheader("📋 Mural de Avisos")
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("➕ Publicar Novo Aviso"):
                t_aviso = st.text_input("Título")
                c_aviso = st.text_area("Mensagem")
                if st.button("Fixar no Mural"):
                    if t_aviso and c_aviso:
                        executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                       {"t": t_aviso, "c": c_aviso, "d": datetime.date.today().strftime('%d/%m/%Y')})
                        st.rerun()
        
        lista_avisos = consultar_db("SELECT titulo, conteudo, data FROM avisos ORDER BY id DESC LIMIT 5")
        if not lista_avisos.empty:
            for _, av in lista_avisos.iterrows():
                st.markdown(f"**{av['titulo']}** ({av['data']})  \n{av['conteudo']}\n---")

    with col_video:
        st.subheader("🎥 Sala de Transmissão")
        st.caption("Acesse a sala de conferência oficial da igreja em alta definição com câmera e áudio.")
        # Solução Definitiva anti-travamento: Botão com abertura nativa de aba externa segura
        st.link_button("🚀 Entrar na Vídeo Chamada Ao Vivo", URL_CHAT_RAILWAY, width="stretch")

# ABA 2: BÍBLIA SAGRADA
with abas[1]:
    st.header("📖 Leitura e Pesquisa Bíblica")
    tabela_existe = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
    
    if tabela_existe.empty:
        st.warning("A estrutura local da Bíblia precisa ser inicializada.")
        if st.button("🚀 Inicializar Estrutura Bíblica Agora", width="stretch"):
            if carregar_biblia_completa():
                st.success("Estrutura ativada com sucesso!")
                st.rerun()
    else:
        busca = st.text_input("🔍 Digite o livro ou termo para buscar:")
        if busca:
            res_b = consultar_db("SELECT livro AS 'Livro', capitulo AS 'Capítulo', versiculo AS 'Versículo', texto AS 'Texto' FROM biblia WHERE livro LIKE :b OR texto LIKE :b LIMIT 50", {"b": f"%{busca}%"})
            if not res_b.empty:
                st.dataframe(res_b, width="stretch", hide_index=True)
        else:
            df_livros_lista = consultar_db("SELECT DISTINCT livro AS 'Livros Ativos' FROM biblia")
            st.dataframe(df_livros_lista, width="stretch", hide_index=True)

# ABA 3: LOUVORES
with abas[2]:
    st.header("🎵 Hinário & Letras de Louvores")
    if st.session_state.nivel_atual == "Pastor":
        with st.expander("➕ Adicionar Novo Louvor"):
            t_louvor = st.text_input("Título do Hino")
            a_louvor = st.text_input("Artista")
            l_louvor = st.text_area("Letra")
            upload_audio = st.file_uploader("Áudio (MP3)", type=["mp3"])
            
            if st.button("Cadastrar Louvor"):
                audio_bytes = upload_audio.read() if upload_audio else None
                executar_query("INSERT INTO louvores (titulo, artista, letra, arquivo_audio) VALUES (:t, :a, :l, :audio)",
                               {"t": t_louvor, "a": a_louvor, "l": l_louvor, "audio": audio_bytes})
                st.success("Cadastrado!")
                st.rerun()
                
    lista_louvores = consultar_db("SELECT id, titulo, artista FROM louvores ORDER BY titulo ASC")
    if not lista_louvores.empty:
        selecionado = st.selectbox("Escolha um Louvor", lista_louvores['titulo'] + " - " + lista_louvores['artista'])
        if selecionado:
            t_sel = selecionado.split(" - ")[0]
            dados_l = consultar_db("SELECT letra, arquivo_audio FROM louvores WHERE titulo = :t LIMIT 1", {"t": t_sel})
            if not dados_l.empty:
                st.subheader(selecionado)
                reg_audio = dados_l.iloc[0]['arquivo_audio']
                if reg_audio is not None:
                    st.audio(bytes(reg_audio), format="audio/mp3")
                st.text(dados_l.iloc[0]['letra'])

# ABA 4: OFERTAS E DÍZIMOS VIA PIX
with abas[3]:
    st.header("💝 Dízimos, Ofertas e Contribuições")
    st.caption("Chave Pix Oficial: **admin@agape.com**")
    st.caption("Favorecido: Igreja Evangélica Ágape de Saquarema")

# ABAS GESTÃO EXCLUSIVA DO PASTOR
if st.session_state.nivel_atual == "Pastor":
    # CADASTRO DE MEMBROS
    with abas[4]:
        st.header("👥 Gestão de Membros")
        with st.form("form_membro", clear_on_submit=True):
            n_m = st.text_input("Nome")
            t_m = st.text_input("Telefone")
            c_m = st.selectbox("Cargo", ["Membro", "Diácono", "Presbítero", "Pastor"])
            m_a = st.selectbox("Mês de Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            if st.form_submit_button("Salvar Registro"):
                if n_m:
                    executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario) VALUES (:n, :t, :c, :d, :m)",
                                   {"n": n_m, "t": t_m, "c": c_m, "d": datetime.date.today().strftime('%d/%m/%Y'), "m": m_a})
                    st.rerun()
        membros_df = consultar_db("SELECT nome AS Nome, telefone AS Telefone, cargo AS Cargo, mes_aniversario AS Aniversário FROM membros")
        st.dataframe(membros_df, width="stretch", hide_index=True)

    # FINANCEIRO
    with abas[5]:
        st.header("💰 Fluxo de Caixa Financeiro")
        c1, c2 = st.columns(2)
        with c1:
            tipo_f = st.radio("Tipo", ["Entrada (Dízimo/Oferta)", "Saída (Despesa)"])
            desc_f = st.text_input("Descrição")
            val_f = st.number_input("Valor", min_value=0.0, step=10.0)
            if st.button("Confirmar Lançamento", width="stretch"):
                executar_query("INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano) VALUES (:t, :desc, :v, :data, :ma)",
                               {"t": "Entrada" if "Entrada" in tipo_f else "Saída", "desc": desc_f, "v": val_f, "data": datetime.date.today().strftime('%d/%m/%Y'), "ma": datetime.date.today().strftime('%m/%Y')})
                st.rerun()
        
        df_ent = consultar_db("SELECT SUM(valor) as total FROM financeiro WHERE tipo = 'Entrada'")
        df_sai = consultar_db("SELECT SUM(valor) as total FROM financeiro WHERE tipo = 'Saída'")
        ent = float(df_ent.iloc[0]['total']) if not df_ent.empty and df_ent.iloc[0]['total'] is not None else 0.0
        sai = float(df_sai.iloc[0]['total']) if not df_sai.empty and df_sai.iloc[0]['total'] is not None else 0.0
        
        with c2:
            st.metric("Total Entradas", f"R$ {ent:,.2f}")
            st.metric("Total Saídas", f"R$ {sai:,.2f}")
            st.metric("Saldo Líquido", f"R$ {(ent - sai):,.2f}")

    # CONTROLE DE USUÁRIOS
    with abas[6]:
        st.header("🔐 Controle de Usuários")
        with st.form("novo_user"):
            u_nome = st.text_input("E-mail").strip()
            u_senha = st.text_input("Senha", type="password")
            u_nivel = st.selectbox("Nível", ["Membro", "Pastor"])
            if st.form_submit_button("Gerar Usuário"):
                if u_nome and u_senha:
                    executar_query("INSERT OR IGNORE INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, :n)",
                                   {"u": u_nome, "s": generate_password_hash(u_senha, method="scrypt"), "n": u_nivel})
                    st.success("Conta adicionada!")
