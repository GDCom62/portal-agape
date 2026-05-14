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

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# Inicialização de tabelas nativas
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

# Força atualização segura do Administrador (Pastor)
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

# --- 4. ESTILIZAÇÃO CUSTOMIZADA (FUNDO AMARELO OURO E LEITURA CINEMA) ---
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

# --- 5. FUNÇÃO DE CARGA DA BÍBLIA REAL LOCAL (TEXTOS VERDADEIROS) ---
def carregar_biblia_completa():
    try:
        linhas_db = [
            # Gênesis Capítulo 1
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 1, "texto": "No princípio, criou Deus os céus e a terra."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 2, "texto": "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus se movia sobre a face das águas."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 3, "texto": "E disse Deus: Haja luz. E houve luz."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 4, "texto": "E viu Deus que era boa a luz; e fez Deus separação entre a luz e as trevas."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 5, "texto": "E Deus chamou à luz Dia; e às trevas chamou Noite. E foi a tarde e a manhã: o dia primeiro."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 6, "texto": "E disse Deus: Haja uma expansão no meio das águas, e haja separação entre águas e águas."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 7, "texto": "E fez Deus a expansão e fez separação entre as águas que estavam debaixo da expansão e as águas que estavam sobre a expansão. E assim foi."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 8, "texto": "E chamou Deus à expansão Céus; e foi a tarde e a manhã: o dia segundo."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 9, "texto": "E disse Deus: Ajuntem-se as águas debaixo dos céus num lugar; e apareça a porção seca. E assim foi."},
            {"livro": "Gênesis", "capitulo": 1, "versiculo": 10, "texto": "E chamou Deus à porção seca Terra; e ao ajuntamento das águas chamou Mares. E viu Deus que era bom."},
            
            # Gênesis Capítulo 2
            {"livro": "Gênesis", "capitulo": 2, "versiculo": 1, "texto": "Assim os céus, e a terra, e todo o seu exército foram acabados."},
            {"livro": "Gênesis", "capitulo": 2, "versiculo": 2, "texto": "E, havendo Deus acabado no dia sétimo a sua obra, que tinha feito, descansou no sétimo dia de toda a sua obra, que tinha feito."},
            {"livro": "Gênesis", "capitulo": 2, "versiculo": 3, "texto": "E abençoou Deus o dia sétimo e o santificou; porque nele descansou de toda a sua obra, que Deus criara e fizera."},
            {"livro": "Gênesis", "capitulo": 2, "versiculo": 4, "texto": "Estas são as origens dos céus e da terra, quando foram criados; no dia em que o Senhor Deus fez a terra e os céus."},
            {"livro": "Gênesis", "capitulo": 2, "versiculo": 5, "texto": "E toda planta do campo antes que estivesse na terra, e toda erva do campo antes que brotasse; porque ainda o Senhor Deus não tinha feito chover sobre a terra, e não havia homem para lavrar a terra."},

            # Salmos Capítulo 23
            {"livro": "Salmos", "capitulo": 23, "versiculo": 1, "texto": "O Senhor é o meu pastor; nada me faltará."},
            {"livro": "Salmos", "capitulo": 23, "versiculo": 2, "texto": "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas."},
            {"livro": "Salmos", "capitulo": 23, "versiculo": 3, "texto": "Refrigera a minha alma; guia-me pelas veredas da justiça por amor do seu nome."},
            {"livro": "Salmos", "capitulo": 23, "versiculo": 4, "texto": "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo; a tua vara e o teu cajado me consolam."},
            {"livro": "Salmos", "capitulo": 23, "versiculo": 5, "texto": "Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda."},
            {"livro": "Salmos", "capitulo": 23, "versiculo": 6, "texto": "Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na Casa do Senhor por longos dias."},

            # Salmos Capítulo 91
            {"livro": "Salmos", "capitulo": 91, "versiculo": 1, "texto": "Aquele que habita no esconderijo do Altíssimo, à sombra do Onipotente descansará."},
            {"livro": "Salmos", "capitulo": 91, "versiculo": 2, "texto": "Direi do Senhor: Ele é o meu Deus, o meu refúgio, a sua fortaleza, e nele confiarei."},
            {"livro": "Salmos", "capitulo": 91, "versiculo": 3, "texto": "Porque ele te livrará do laço do passarinheiro e da peste perniciosa."},
            {"livro": "Salmos", "capitulo": 91, "versiculo": 4, "texto": "Ele te cobrirá com as suas penas, e debaixo das suas asas estarás seguro; a sua verdade será o teu escudo e broquel."},
            {"livro": "Salmos", "capitulo": 91, "versiculo": 5, "texto": "Não temerás espanto noturno, nem seta que voe de dia."}
        ]
        
        df_biblia = pd.DataFrame(linhas_db)
        df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
        return True
    except Exception as e:
        st.error(f"Erro na gravação das escrituras: {e}")
        return False

# --- 6. GESTÃO DE ACESSO (AUTENTICAÇÃO COMPLETA) ---
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

# --- 7. MONTAGEM DO PAINEL PRINCIPAL DE CONTEÚDO ---
if st.session_state.nivel_atual == "Pastor":
    aba_mural, aba_biblia, aba_louvores, aba_pix, aba_membros, aba_financeiro, aba_credenciais = st.tabs(
        ["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos", "👥 Gestão de Membros", "💰 Financeiro", "🔐 Credenciais"]
    )
else:
    aba_mural, aba_biblia, aba_louvores, aba_pix = st.tabs(
        ["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos"]
    )

# ABA 1: CONTEÚDO INICIAL (MURAL E CONFERÊNCIA)
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
        st.subheader("🎥 Sala de Transmissão")
        st.caption("Acesse a sala de conferência oficial da igreja em alta definição.")
        st.link_button("🚀 Entrar na Vídeo Chamada Ao Vivo", URL_CHAT_RAILWAY, width="stretch")

# ABA 2: BÍBLIA SAGRADA (PAINEL SUSPENSO EM MODO CINEMA COM VERSÍCULOS DIRETOS)
with aba_biblia:
    st.header("📖 Leitura e Pesquisa Bíblica")
    tabela_existe = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
    
    if tabela_existe.empty:
        st.warning("A base de dados da Bíblia precisa ser estruturada.")
        if st.button("🚀 Estruturar Textos Bíblicos Agora", width="stretch"):
            if carregar_biblia_completa():
                st.success("Escrituras ativadas e prontas localmente!")
                st.rerun()
    else:
        sub_aba_leitura, sub_aba_busca = st.tabs(["📖 Navegar por Capítulo", "🔍 Buscar por Palavra-Chave"])
        
        with sub_aba_leitura:
            df_livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            lista_livros = df_livros['livro'].tolist() if not df_livros.empty else ["Gênesis"]
            
            c_livro, c_cap = st.columns(2)
            with c_livro:
                livro_sel = st.selectbox("Escolha o Livro", lista_livros)
            
            df_caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro = :l ORDER BY capitulo ASC", {"l": livro_sel})
            lista_caps = df_caps['capitulo'].tolist() if not df_caps.empty else [1]
            with c_cap:
                cap_sel = st.selectbox("Capítulo", lista_caps)
                
            df_versiculos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": livro_sel, "c": cap_sel})
            
            st.markdown(f"<div class='versiculo-box'><h2 style='color:#FFD700; margin:0;'>✨ {livro_sel} - Capítulo {cap_sel} ✨</h2></div>", unsafe_allow_html=True)
            
            if not df_versiculos.empty:
                conteudo_html = "<div class='versiculo-box' style='text-align: left !important;'>"
                for _, row in df_versiculos.iterrows():
                    conteudo_html += f"<p class='texto-sagrado-grande'><span class='numero-versiculo'>{row['versiculo']}.</span> {row['texto']}</p>"
                conteudo_html += "</div>"
                st.markdown(conteudo_html, unsafe_allow_html=True)
            else:
                st.info("Nenhum texto encontrado para esta seleção.")
                
        with sub_aba_busca:
            busca_termo = st.text_input("🔍 O que você deseja buscar nas escrituras? (Ex: princípio, trevas, pastor)")
            if busca_termo:
                # MELHORIA: O resultado agora exibe a coluna 'Texto' diretamente na visualização da tabela
                res_busca = consultar_db("SELECT livro AS 'Livro', capitulo AS 'Capítulo', versiculo AS 'Versículo', texto AS 'Texto Completo do Versículo' FROM biblia WHERE texto LIKE :b LIMIT 50", {"b": f"%{busca_termo}%"})
                if not res_busca.empty:
                    st.subheader(f"Encontradas {len(res_busca)} ocorrências com texto completo:")
                    st.dataframe(res_busca, width="stretch", hide_index=True)
                else:
                    st.info("Nenhum versículo contendo este termo foi localizado.")

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
            dados_l = consultar_db("SELECT letra, arquivo_audio FROM louvores WHERE titulo = :t LIMIT 1", {"t": t_sel[0]})
            if not dados_l.empty:
                st.subheader(selecionado)
                reg_audio = dados_l.iloc[0]['arquivo_audio']
                if reg_audio is not None:
                    st.audio(bytes(reg_audio), format="audio/mp3")
                st.text(dados_l.iloc[0]['letra'])

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
        ent = float(df_ent.iloc[0]['total']) if not df_ent.empty and df_ent.iloc[0]['total'] is not None else 0.0
        sai = float(df_sai.iloc[0]['total']) if not df_sai.empty and df_sai.iloc[0]['total'] is not None else 0.0
        
        with c2:
            st.metric("Total Entradas", f"R$ {ent:,.2f}")
            st.metric("Total Saídas", f"R$ {sai:,.2f}")
            st.metric("Saldo Líquido", f"R$ {(ent - sai):,.2f}")
            
        # MELHORIA: Gráfico de barras visual para consolidação de entradas vs saídas
        st.markdown("---")
        st.subheader("📊 Comparativo Consolidado de Caixa")
        df_grafico = pd.DataFrame({
            "Tipo": ["Total Entradas (R$)", "Total Saídas (R$)"],
            "Valor": [ent, sai]
        }).set_index("Tipo")
        st.bar_chart(df_grafico)

    with aba_credenciais:
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
