import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import json
import requests
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONFIGURAÇÕES DE AMBIENTE ---
URL_CHAT_RAILWAY = "https://railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS PERSISTENTE & REDIS ---
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

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# Inicialização segura das tabelas nativas do sistema
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
    mes_aniversario TEXT,
    observacoes TEXT
);
""")

try:
    executar_query("ALTER TABLE membros ADD COLUMN observacoes TEXT DEFAULT '';")
except Exception:
    pass

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

# Sincronização do Administrador Nativo
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

# --- 4. ESTILIZAÇÃO CUSTOMIZADA RESTAURADA (AMARELO OURO) ---
st.markdown("""
    <style>
    .stApp, div[data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
    }
    .stMetric, div[data-testid="stMetricValue"], div[data-testid="metric-container"], .card-flutuante, .cartao-membro {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 16px !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.1) !important;
        border: 1px solid #e0a800 !important;
        color: #212529 !important;
    }
    .versiculo-box {
        background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important;
        color: #FFD700 !important;
        padding: 30px !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        margin-bottom: 25px !important;
        border: 2px solid #FFD700 !important;
        text-align: center !important;
    }
    .texto-sagrado-grande {
        font-size: 24px !important;
        font-family: 'Georgia', serif !important;
        line-height: 1.6 !important;
        margin-bottom: 15px !important;
        color: #FFD700 !important;
        text-align: justify !important;
    }
    .numero-versiculo {
        color: #ffffff !important;
        font-weight: bold !important;
        margin-right: 8px !important;
    }
    .pix-card {
        background-color: #ffffff !important;
        padding: 30px;
        border-radius: 20px;
        border: 2px dashed #008080;
        text-align: center;
        box-shadow: 0 6px 16px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. GESTÃO DE ACESSO (AUTENTICAÇÃO COMPLETA) ---
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
                if not df_u.empty and check_password_hash(str(df_u.iloc['senha']), campo_senha):
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = campo_usuario
                    st.session_state.nivel_atual = df_u.iloc['nivel']
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
if st.session_state.nivel_atual == "Pastor":
    aba_mural, aba_biblia, aba_louvores, aba_pix, aba_membros, aba_financeiro, aba_credenciais = st.tabs(
        ["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos", "👥 Gestão de Membros", "💰 Financeiro", "🔐 Credenciais"]
    )
else:
    aba_mural, aba_biblia, aba_louvores, aba_pix = st.tabs(
        ["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos"]
    )

# ABA 1: CONTEÚDO INICIAL (MURAL E INTEGRAÇÃO DE CHAT REDIS)
with aba_mural:
    col_topo1, col_topo2 = st.columns(2)
    with col_topo1:
        st.markdown("""
        <div class='versiculo-box'>
            <h3 style='margin:0; color:#FFD700; font-family: Georgia, serif;'>📖 Palavra do Dia</h3>
            <p style='font-size: 20px; font-style: italic; margin-top:12px; color:#ffffff;'>
                "O Senhor é o meu pastor, nada me faltará. Deita-me em verdes pastos, guia-me mansamente a águas tranquilas."
            </p>
            <p style='text-align: right; font-weight: bold; margin:0; color:#FFD700;'>Salmos 23:1-2</p>
        </div>
        """, unsafe_allow_html=True)
        
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
        st.subheader("🎥 Sala de Transmissão & Mural Online")
        st.link_button("🚀 Entrar na Vídeo Chamada Ao Vivo", URL_CHAT_RAILWAY, width="stretch")
        st.markdown("---")
        st.subheader("💬 Mural de Interações Online (Redis)")
        
        if r_db:
            user_chat = st.session_state.usuario_atual if st.session_state.usuario_atual else "Irmão"
            r_db.set(f"online:{user_chat}", "online", ex=60)
            usuarios_ativos = [k.replace("online:", "") for k in r_db.keys("online:*")]
            st.markdown(f"🟢 **Membros Ativos:** {', '.join(usuarios_ativos)}")
            
            with st.form("chat_mural_local", clear_on_submit=True):
                msg_texto = st.text_input("Envie uma palavra ou pedido de oração no mural:")
                if st.form_submit_button("Enviar Mensagem"):
                    if msg_texto:
                        payload_msg = {"user": user_chat, "text": msg_texto, "time": datetime.datetime.now().strftime("%H:%M")}
                        r_db.rpush("chat:agape_oficial", json.dumps(payload_msg))
                        r_db.ltrim("chat:agape_oficial", -50, -1)
                        st.rerun()
            
            for m in reversed(r_db.lrange("chat:agape_oficial", 0, -1)):
                try:
                    m_data = json.loads(m)
                    st.markdown(f"**[{m_data['time']}] {m_data['user']}:** {m_data['text']}")
                except Exception:
                    pass
        else:
            st.info("Mural interativo offline.")

# ABA 2: BÍBLIA SAGRADA REAL ONLINE (API DE ALTA DISPONIBILIDADE)
with aba_biblia:
    st.header("📖 Leitura Bíblica Oficial (Almeida Revista e Corrigida)")
    
    livros_canônicos_66 = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
        "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
        "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
        "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah",
        "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
        "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
        "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
        "1 John", "2 John", "3 John", "Judas", "Revelation"
    ]
    
    sub_aba_leitura, sub_aba_busca = st.tabs(["📖 Navegar por Capítulo", "🔍 Buscar por Palavra-Chave"])
    
    with sub_aba_leitura:
        c_livro, c_cap = st.columns(2)
        with c_livro:
            livro_sel = st.selectbox("Escolha o Livro Sagrado", livros_canônicos_66)
        with c_cap:
            cap_sel = st.number_input("Escolha o Capítulo", min_value=1, max_value=150, value=1, step=1)
            
        if st.button("📖 Abrir Capítulo em Modo Cinema", width="stretch"):
            with st.spinner("Buscando escrituras legítimas na nuvem..."):
                try:
                    # CORREÇÃO CRÍTICA: Adicionada a barra '/' após a URL e parâmetro '@almeida' para carregar em Português
                    link_api = f"https://bible-api.com{livro_sel}+{cap_sel}?translation=almeida"
                    resposta = requests.get(link_api, timeout=12)
                    
                    if resposta.status_code == 200:
                        dados_bible = resposta.json()
                        st.markdown(f"<div class='versiculo-box'><h2 style='color:#FFD700; margin:0;'>✨ {livro_sel} - Capítulo {cap_sel} ✨</h2></div>", unsafe_allow_html=True)
                        
                        conteudo_html = "<div class='versiculo-box' style='text-align: left !important;'>"
                        for v in dados_bible.get("verses", []):
                            num_ver = v.get("verse")
                            txt_ver = v.get("text").strip()
                            conteudo_html += f"<p class='texto-sagrado-grande'><span class='numero-versiculo'>{num_ver}.</span> {txt_ver}</p>"
                        conteudo_html += "</div>"
                        st.markdown(conteudo_html, unsafe_allow_html=True)
                    else:
                        st.error("Erro ao localizar este capítulo na API. Verifique se o livro possui essa numeração.")
                except Exception as e:
                    st.error(f"Não foi possível conectar ao servidor de escrituras: {e}")

    with sub_aba_busca:
        busca_termo = st.text_input("🔍 Buscar termo exato na API:")
        if busca_termo:
            resposta_b = requests.get(f"https://bible-api.com{busca_termo}?translation=almeida", timeout=15)
            if resposta_b.status_code == 200:
                dados_busca = resposta_b.json()
                st.info(f"Exibindo resultado correspondente para: '{busca_termo}'")
                st.write(dados_busca.get("text", "Nenhum bloco retornado."))
            else:
                st.info("Termo não localizado.")

# ABA 3: LOUVORES
with aba_louvores:
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
                st.success("Louvor cadastrado!")
                st.rerun()
                
    lista_louvores = consultar_db("SELECT id, titulo, artista FROM louvores ORDER BY titulo ASC")
    if not lista_louvores.empty:
        selecionado = st.selectbox("Escolha um Louvor", lista_louvores['titulo'] + " - " + lista_louvores['artista'])
        if selecionado:
            t_sel = selecionado.split(" - ")
            dados_l = consultar_db("SELECT letra, arquivo_audio FROM louvores WHERE titulo = :t LIMIT 1", {"t": t_sel})
            if not dados_l.empty:
                st.subheader(selecionado)
                reg_audio = dados_l.iloc['arquivo_audio']
                if reg_audio is not None:
                    st.audio(bytes(reg_audio), format="audio/mp3")
                st.text(dados_l.iloc['letra'])

# ABA 4: OFERTAS E DÍZIMOS VIA PIX
with aba_pix:
    st.header("💝 Dízimos, Ofertas e Contribuições")
    st.markdown("""
    <div class='pix-card'>
        <h3 style='color: #008080; margin: 0;'>🔑 Chave Pix Oficial</h3>
        <code style='font-size: 20px; color: #333; display: block; margin: 15px 0;'>admin@agape.com</code>
        <p><b>Favorecido:</b> Igreja Evangélica Ágape de Saquarema</p>
    </div>
    """, unsafe_allow_html=True)

# ABAS GESTÃO EXCLUSIVA DO PASTOR
if st.session_state.nivel_atual == "Pastor":
    with aba_membros:
        st.header("👥 Gestão de Membros")
        filtro_nome = st.text_input("🔍 Pesquisar membro por nome:")
            
        with st.form("form_membro", clear_on_submit=True):
            n_m = st.text_input("Nome do Membro")
            t_m = st.text_input("Telefone")
            c_m = st.selectbox("Cargo", ["Membro", "Diácono", "Presbítero", "Pastor"])
            m_a = st.selectbox("Mês de Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            obs_m = st.text_area("📝 Observações Especiais (Batismo, Histórico, etc.)")
            
            if st.form_submit_button("Salvar Registro"):
                if n_m:
                    executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario, observacoes) VALUES (:n, :t, :c, :d, :m, :obs)",
                                   {"n": n_m, "t": t_m, "c": c_m, "d": datetime.date.today().strftime('%d/%m/%Y'), "m": m_a, "obs": obs_m})
                    st.rerun()
                    
        sql_membros = "SELECT nome AS Nome, telefone AS Telefone, cargo AS Cargo, mes_aniversario AS Aniversário, observacoes AS Observações FROM membros"
        if filtro_nome:
            sql_membros += f" WHERE nome LIKE '%{filtro_nome}%'"
        membros_df = consultar_db(sql_membros)
        st.dataframe(membros_df, width="stretch", hide_index=True)

    with aba_financeiro:
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
        ent = float(df_ent.iloc['total']) if not df_ent.empty and df_ent.iloc['total'] is not None else 0.0
        sai = float(df_sai.iloc['total']) if not df_sai.empty and df_sai.iloc['total'] is not None else 0.0
        
        with c2:
            st.metric("Total Entradas", f"R$ {ent:,.2f}")
            st.metric("Total Saídas", f"R$ {sai:,.2f}")
            st.metric("Saldo Líquido", f"R$ {(ent - sai):,.2f}")
            
        st.markdown("---")
        st.subheader("📊 Comparativo Consolidado de Caixa")
        df_grafico = pd.DataFrame({
            "Tipo": ["Total Entradas (R$)", "Total Saídas (R$)"],
            "Valor": [ent, sai]
        }).set_index("Tipo")
        st.bar_chart(df_grafico)
        
        st.markdown("---")
        st.subheader("❌ Área de Exclusão de Lançamentos")
        historico_df = consultar_db("SELECT id AS 'ID', tipo AS 'Tipo', descricao AS 'Descrição', valor AS 'Valor (R$)', data AS 'Data' FROM financeiro ORDER BY id DESC")
        if not historico_df.empty:
            st.dataframe(historico_df, width="stretch", hide_index=True)
            id_para_deletar = st.number_input("Digite o ID do lançamento que deseja apagar:", min_value=1, step=1)
            
            confirmar_exclusao = st.checkbox("⚠️ Confirmo que selecionei o ID correto e desejo apagar permanentemente.")
            if st.button("❌ Apagar Lançamento Selecionado", type="primary"):
                if confirmar_exclusao:
                    executar_query("DELETE FROM financeiro WHERE id = :id", {"id": id_para_deletar})
                    st.success("Lançamento removido com sucesso!")
                    st.rerun()
                else:
                    st.warning("Marque a caixa de confirmação antes de clicar no botão.")

    with aba_credenciais:
        st.header("🔐 Controle de Usuários")
        with st.form("novo_user"):
            u_nome = st.text_input("E-mail").strip()
            u_senha = st.text_input("Senha", type="password")
            u_nivel = st.selectbox("Nível", ["Membro", "Pastor"])
            if st.form_submit_button("Gerar Usuário"):
                if u_nome and u_senha:
                    check_e = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": u_nome})
                    if check_e.empty:
                        executar_query("INSERT OR IGNORE INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, :n)",
                                       {"u": u_nome, "s": generate_password_hash(u_senha, method="scrypt"), "n": u_nivel})
                        st.success("Conta criada com sucesso!")
