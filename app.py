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

# Criação inicial protegida de tabelas
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

# Força atualização segura do Administrador (Pastor) com tratamento de erro robusto
def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    admin_senha_pura = "agape2026"
    hash_admin = generate_password_hash(admin_senha_pura, method="scrypt")
    
    try:
        existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
        if existe.empty:
            executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", 
                           {"user": admin_usuario, "senha": hash_admin})
        else:
            executar_query("UPDATE usuarios SET senha = :senha, nivel = 'Pastor' WHERE usuario = :user", 
                           {"user": admin_usuario, "senha": hash_admin})
    except Exception:
        executar_query("DROP TABLE IF EXISTS usuarios;")
        executar_query("CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", 
                       {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. ESTILIZAÇÃO CUSTOMIZADA (FUNDO AMARELO OURO) ---
st.markdown("""
    <style>
    .stApp {
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
        background: linear-gradient(135deg, #212529 0%, #000000 100%);
        color: #FFD700;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        margin-bottom: 25px;
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

# --- 5. FUNÇÃO DE CARGA DA BÍBLIA LOCAL (IMUNE A ERROS DE INTERNET) ---
def carregar_biblia_completa():
    try:
        # Dicionário local contendo versículos-chave consolidados de todos os livros para o banco nunca falhar
        livros_dados = [
            ("Gênesis", 1, 1, "No princípio, criou Deus os céus e a terra."),
            ("Êxodo", 3, 14, "Disse Deus a Moisés: EU SOU O QUE SOU."),
            ("Levítico", 19, 18, "Amarás o teu próximo como a ti mesmo. Eu sou o Senhor."),
            ("Números", 6, 24, "O Senhor te abençoe e te guarde."),
            ("Deuteronômio", 6, 5, "Amarás, pois, o Senhor, teu Deus, de todo o teu coração."),
            ("Josué", 1, 9, "Não fui eu que lhe ordenei? Seja forte e corajoso!"),
            ("Juízes", 5, 31, "Assim, ó Senhor, pereçam todos os teus inimigos!"),
            ("Rute", 1, 16, "O teu povo é o meu povo, o teu Deus é o meu Deus."),
            ("1 Samuel", 7, 12, "Até aqui nos ajudou o Senhor."),
            ("2 Samuel", 22, 33, "Deus é a minha grande fortaleza e torna perfeito o meu caminho."),
            ("1 Reis", 3, 9, "Dá, pois, ao teu servo um coração compreensivo para julgar o teu povo."),
            ("2 Reis", 2, 9, "Peço-te que haja porção dupla de teu espírito sobre mim."),
            ("1 Crônicas", 16, 34, "Deem graças ao Senhor, porque ele é bom; o seu amor dura para sempre."),
            ("2 Crônicas", 7, 14, "Se o meu povo, que se chama pelo meu nome, se humilhar e orar..."),
            ("Esdras", 7, 10, "Pois Esdras tinha decidido dedicar-se a estudar a Lei do Senhor."),
            ("Neemias", 8, 10, "A alegria do Senhor é a vossa força."),
            ("Ester", 4, 14, "Quem sabe se não foi para uma conjuntura como esta que você atingiu a realeza?"),
            ("Jó", 19, 25, "Eu sei que o meu Redentor vive e que por fim se levantará sobre a terra."),
            ("Salmos", 23, 1, "O Senhor é o meu pastor; nada me faltará."),
            ("Salmos", 119, 105, "Lâmpada para os meus pés é tua palavra e luz, para o meu caminho."),
            ("Provérbios", 1, 7, "O temor do Senhor é o princípio do saber."),
            ("Eclesiastes", 3, 1, "Tudo tem o seu tempo determinado, e há tempo para todo o propósito debaixo do céu."),
            ("Cantares", 8, 7, "Nem as muitas águas conseguem apagar o amor."),
            ("Isaías", 9, 6, "Porque um menino nos nasceu, um filho se nos deu; e o governo estará sobre os seus ombros."),
            ("Isaías", 40, 31, "Mas os que esperam no Senhor renovam as suas forças."),
            ("Jeremias", 29, 11, "Porque sou eu que conheço os planos que tenho para vocês', diz o Senhor."),
            ("Lamentações", 3, 22, "As misericórdias do Senhor são a causa de não sermos consumidos."),
            ("Ezequiel", 36, 26, "Darei a vocês um coração novo e porei um espírito novo em vocês."),
            ("Daniel", 6, 22, "O meu Deus enviou o seu anjo, que fechou a boca dos leões."),
            ("Oséias", 6, 3, "Conheçamos e prossigamos em conhecer ao Senhor."),
            ("Joel", 2, 28, "E há de ser que, depois, derramarei o meu Espírito sobre toda a carne."),
            ("Amós", 5, 24, "Corra, porém, o juízo como as águas, e a justiça, como o ribeiro perene."),
            ("Obadias", 1, 21, "E o reino será do Senhor."),
            ("Jonas", 2, 9, "Do Senhor vem a salvação."),
            ("Miqueias", 6, 8, "Ele mostrou a você o que é bom: praticar a justiça, amar a fidelidade e andar humildemente."),
            ("Naum", 1, 7, "O Senhor é bom, uma fortaleza no dia da angústia."),
            ("Habacuque", 3, 17, "Ainda que a figueira não floresça... todavia, eu me alegrarei no Senhor."),
            ("Sofonias", 3, 17, "O Senhor, teu Deus, está no meio de ti, poderoso para salvar."),
            ("Ageu", 2, 9, "A glória desta última casa será maior do que a da primeira."),
            ("Zacarias", 4, 6, "Não por força nem por violência, mas pelo meu Espírito, diz o Senhor."),
            ("Malaquias", 4, 2, "Mas para vocês que reverenciam o meu nome, o sol da justiça levantará trazendo cura."),
            ("Mateus", 6, 33, "Mas busquem primeiro o Reino de Deus e a sua justiça."),
            ("Marcos", 16, 15, "E disse-lhes: Ide por todo o mundo, pregai o evangelho a toda criatura."),
            ("Lucas", 1, 37, "Porque para Deus nada é impossível."),
            ("João", 3, 16, "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito."),
            ("João", 14, 6, "Respondeu Jesus: Eu sou o caminho, a verdade e a vida."),
            ("Atos", 1, 8, "Mas receberão poder quando o Espírito Santo descer sobre vocês."),
            ("Romanos", 8, 28, "Sabemos que Deus age em todas as coisas para o bem daqueles que o amam."),
            ("1 Coríntios", 13, 13, "Assim, permanecem agora estes três: a fé, a esperança e o amor. O maior deles é o amor."),
            ("2 Coríntios", 12, 9, "A minha graça te basta, porque o meu poder se aperfeiçoa na fraqueza."),
            ("Gálatas", 5, 22, "Mas o fruto do Espírito é: amor, alegria, paz, paciência, amabilidade..."),
            ("Efésios", 2, 8, "Pois vocês são salvos pela graça, por meio da fé; e isto não vem de vocês, é dom de Deus."),
            ("Filipenses", 4, 13, "Tudo posso naquele que me fortalece."),
            ("Colossenses", 3, 23, "Tudo o que fizerem, façam de todo o coração, como para o Senhor."),
            ("1 Tessalonicenses", 5, 17, "Orem continuamente."),
            ("2 Tessalonicenses", 3, 3, "Pois o Senhor é fiel; ele os fortalecerá e os guardará do Maligno."),
            ("1 Timóteo", 6, 12, "Combata o bom combate da fé."),
            ("2 Timóteo", 4, 7, "Combati o bom combate, acabei a carreira, guardei a fé."),
            ("Tito", 3, 5, "Não por causa de atos de justiça que tivéssemos praticado, mas por causa da sua misericórdia."),
            ("Filemom", 1, 7, "Seu amor me tem dado grande alegria e consolação."),
            ("Hebreus", 11, 1, "Ora, a fé é a certeza daquilo que esperamos e a prova das coisas que não vemos."),
            ("Tiago", 4, 7, "Portanto, submetam-se a Deus. Resistam ao Diabo, e ele fugirá de vocês."),
            ("1 Pedro", 5, 7, "Lancem sobre ele toda a vossa ansiedade, porque ele tem cuidado de vós."),
            ("2 Pedro", 3, 9, "O Senhor não demora em cumprir a sua promessa... Ele é paciente com vocês."),
            ("1 João", 4, 8, "Aquele que não ama não conhece a Deus, porque Deus é amor."),
            ("2 João", 1, 6, "E o amor é este: que andemos em conformidade com os seus mandamentos."),
            ("3 João", 1, 4, "Não tenho maior alegria do que ouvir que meus filhos estão andando na verdade."),
            ("Judas", 1, 24, "Àquele que é poderoso para impedir que vocês caiam..."),
            ("Apocalipse", 22, 20, "Aquele que dá testemunho destas coisas diz: 'Sim, venho em breve!' Amém. Vem, Senhor Jesus!")
        ]
        
        linhas_db = []
        for livro, cap, ver, texto in livros_dados:
            linhas_db.append({
                "livro": str(livro),
                "capitulo": int(cap),
                "versiculo": int(ver),
                "texto": str(texto)
            })
            
        df_biblia = pd.DataFrame(linhas_db)
        df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
        return True
    except Exception as e:
        st.error(f"Erro local na carga da Bíblia: {e}")
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
            botao_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
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
            botao_registrar = st.form_submit_button("Solicitar Acesso", use_container_width=True)
            
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
                            st.success("Acesso criado! Mude para a aba 'Entrar'.")
                        else:
                            st.error("Este e-mail de usuário já está cadastrado.")
                else:
                    st.warning("Preencha todos os campos obrigatórios.")

    with aba_side_esqueci:
        with st.form(key="form_reset_senha"):
            st.caption("Insira o seu e-mail cadastrado e defina a nova senha abaixo.")
            reset_user = st.text_input("E-mail Cadastrado").strip()
            nova_senha_pura = st.text_input("Nova Senha Desejada", type="password")
            botao_resetar = st.form_submit_button("Resetar e Atualizar Senha", use_container_width=True)
            
            if botao_resetar:
                if reset_user and nova_senha_pura:
                    check_user = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reset_user})
                    if not check_user.empty:
                        hash_recuperado = generate_password_hash(nova_senha_pura, method="scrypt")
                        executar_query("UPDATE usuarios SET senha = :s WHERE usuario = :u", 
                                       {"s": hash_recuperado, "u": reset_user})
                        st.success("Senha atualizada! Prossiga para o Login.")
                    else:
                        st.error("E-mail não encontrado no sistema.")
                else:
                    st.warning("Preencha o e-mail e a nova senha.")
    st.stop()
else:
    st.sidebar.write(f"Usuário: **{st.session_state.usuario_atual}**")
    st.sidebar.info(f"Acesso: {st.session_state.nivel_atual}")
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.session_state.nivel_atual = "Membro"
        st.rerun()

# --- 7. MONTAGEM DO PAINEL PRINCIPAL DE CONTEÚDO ---
st.title("⛪ Portal Administrativo Ágape")

if st.session_state.nivel_atual == "Pastor":
    abas = st.tabs(["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos", "👥 Gestão de Membros", "💰 Financeiro", "🔐 Credenciais"])
else:
    abas = st.tabs(["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores", "💝 Ofertas e Dízimos"])

# ABA 1: CONTEÚDO INICIAL
with abas[0]:
    col_topo1, col_topo2 = st.columns(2)
    with col_topo1:
        st.markdown("""
        <div class='versiculo-box'>
            <h3 style='margin:0; color:#FFD700;'>📖 Palavra do Dia</h3>
            <p style='font-size: 16px; font-style: italic; margin-top:10px;'>\"O Senhor é o meu pastor, nada me faltará. Deita-me em verdes pastos, guia-me mansamente a águas tranquilas.\"</p>
            <p style='text-align: right; font-weight: bold; margin:0;'>Salmos 23:1-2</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_topo2:
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual = meses_pt[datetime.date.today().month - 1]
        
        st.markdown(f"""
        <div style='background: white; padding: 20px; border-radius: 20px; border: 1px solid #e0a800; min-height: 145px;'>
            <h3 style='margin:0; color:#212529;'>🎂 Aniversariantes de {mes_atual}</h3>
        """, unsafe_allow_html=True)
        
        df_aniv = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :mes", {"mes": mes_atual})
        if not df_aniv.empty:
            nomes_aniv = ", ".join([f"<b>{row['nome']}</b> ({row['cargo']})" for _, row in df_aniv.iterrows()])
            st.markdown(f"<p style='color:#333; margin-top:10px; font-size:16px;'>🎉 Parabéns a: {nomes_aniv}!</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:gray; margin-top:10px;'>Nenhum membro faz aniversário este mês.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    col_aviso, col_video = st.columns(2)
    
    with col_aviso:
        st.header("📋 Mural de Avisos")
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("➕ Novo Aviso (Exclusivo Pastor)"):
                t_aviso = st.text_input("Título do Aviso")
                c_aviso = st.text_area("Conteúdo")
                if st.button("Publicar Aviso"):
                    if t_aviso and c_aviso:
                        executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                       {"t": t_aviso, "c": c_aviso, "d": datetime.date.today().strftime('%d/%m/%Y')})
                        st.success("Publicado!")
                        st.rerun()
        
        lista_avisos = consultar_db("SELECT titulo, conteudo, data FROM avisos ORDER BY id DESC LIMIT 5")
        if not lista_avisos.empty:
            for _, av in lista_avisos.iterrows():
                st.markdown(f"""
                <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #FFA500;'>
                    <h4 style='margin:0;'>{av['titulo']}</h4>
                    <p style='color: gray; font-size: 12px;'>Postado em: {av['data']}</p>
                    <p style='margin:0; color:#333;'>{av['conteudo']}</p>
                </div>
                """, unsafe_allow_html=True)

    with col_video:
        st.header("🎥 Conferência Ao Vivo")
        st.html(f'<iframe src="{URL_CHAT_RAILWAY}" width="100%" height="450" style="border:none; border-radius: 15px; background: white;" scrolling="yes" allow="camera; microphone"></iframe>')

# ABA 2: BÍBLIA SAGRADA
with abas[1]:
    st.header("📖 Leitura e Pesquisa Bíblica")
    tabela_existe = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
    
    if tabela_existe.empty:
        st.info("A base de dados local da Bíblia precisa ser estruturada.")
        if st.button("🚀 Inicializar Estrutura Bíblica Agora", use_container_width=True):
            with st.spinner("Estruturando os 66 Livros internamente..."):
                if carregar_biblia_completa():
                    st.success("Bíblia Sagrada ativada localmente com sucesso!")
                    st.rerun()
    else:
        busca = st.text_input("🔍 Digite o nome de um livro ou trecho para buscar na Bíblia:")
        if busca:
            res_b = consultar_db("SELECT livro AS 'Livro', capitulo AS 'Capítulo', versiculo AS 'Versículo', texto AS 'Texto' FROM biblia WHERE texto LIKE :b OR livro LIKE :b LIMIT 50", {"b": f"%{busca}%"})
            if not res_b.empty:
                st.dataframe(res_b, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum resultado encontrado para esta palavra.")
        else:
            st.subheader("Índice de Livros Prontos para Consulta")
            df_livros_lista = consultar_db("SELECT DISTINCT livro AS 'Livros Disponíveis' FROM biblia")
            if not df_livros_lista.empty:
                st.dataframe(df_livros_lista, use_container_width=True, hide_index=True)

# ABA 3: LOUVORES
with abas[2]:
    st.header("🎵 Hinário & Letras de Louvores")
    if st.session_state.nivel_atual == "Pastor":
        with st.expander("➕ Adicionar Novo Louvor"):
            t_louvor = st.text_input("Título do Hino")
            a_louvor = st.text_input("Ministério / Artista")
            l_louvor = st.text_area("Letra Completa")
            upload_audio = st.file_uploader("Arquivo de Áudio (Opcional - MP3)", type=["mp3"])
            
            if st.button("Cadastrar Louvor"):
                audio_bytes = upload_audio.read() if upload_audio else None
                executar_query("INSERT INTO louvores (titulo, artista, letra, arquivo_audio) VALUES (:t, :a, :l, :audio)",
                               {"t": t_louvor, "a": a_louvor, "l": l_louvor, "audio": audio_bytes})
                st.success("Louvor cadastrado!")
                st.rerun()
                
    lista_louvores = consultar_db("SELECT id, titulo, artista FROM louvores ORDER BY titulo ASC")
    if not lista_louvores.empty:
        selecionado = st.selectbox("Escolha um Louvor para exibir", lista_louvores['titulo'] + " - " + lista_louvores['artista'])
        if selecionado:
            t_sel = selecionado.split(" - ")[0]
            dados_l = consultar_db("SELECT letra, arquivo_audio FROM louvores WHERE titulo = :t LIMIT 1", {"t": t_sel})
            
            if not dados_l.empty:
                st.subheader(selecionado)
                registro_audio = dados_l.iloc[0]['arquivo_audio']
                if registro_audio is not None:
                    st.audio(bytes(registro_audio), format="audio/mp3")
                st.text(dados_l.iloc[0]['letra'])

# ABA 4: DOAÇÕES E DÍZIMOS VIA PIX
with abas[3]:
    st.header("💝 Dízimos, Ofertas e Contribuições")
    st.caption("Gere a sua contribuição diretamente via Pix de forma prática e segura.")
    
    col_pix_info, col_pix_qr = st.columns(2)
    with col_pix_info:
        st.markdown("""
        <div class='pix-card'>
            <h3 style='color: #008080; margin: 0;'>🔑 Chave Pix Oficial</h3>
            <p style='font-size: 14px; color: gray; margin-top: 5px;'>Clique duas vezes no campo abaixo para copiar:</p>
            <code style='font-size: 20px; background-color: #f1f3f5; padding: 10px 15px; border-radius: 8px; color: #333; display: block; border: 1px solid #ced4da;'>
                admin@agape.com
            </code>
            <br>
            <p style='text-align: left; font-size: 15px; color: #495057;'>
                <b>Banco Destino:</b> Banco Nu Pagamentos (Nubank)<br>
                <b>Favorecido:</b> Igreja Evangélica Ágape de Saquarema<br>
                <b>Finalidade:</b> Manutenção da obra, missões locais e expansão social.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_pix_qr:
        st.subheader("📷 Escaneie o QR Code")
        st.info("Pastor: Substitua este bloco por st.image('qrcode.png') para fixar a imagem oficial.")
        st.markdown("<div style='background: #f8f9fa; border: 1px solid #ddd; height:200px; border-radius:15px; display:flex; align-items:center; justify-content:center; color:gray;'>[Área do QR Code Pix]</div>", unsafe_allow_html=True)

# ABAS EXCLUSIVAS GESTÃO DO PASTOR
if st.session_state.nivel_atual == "Pastor":
    with abas[4]:
        st.header("👥 Cadastro de Membros")
        with st.form("form_membro", clear_on_submit=True):
            n_m = st.text_input("Nome Completo")
            t_m = st.text_input("Telefone / WhatsApp")
            c_m = st.selectbox("Cargo Eclesiástico", ["Membro", "Diácono", "Presbítero", "Evangelista", "Pastor", "Missionária"])
            m_a = st.selectbox("Mês de Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            if st.form_submit_button("Salvar Membro"):
                if n_m:
                    executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario) VALUES (:n, :t, :c, :d, :m)",
                                   {"n": n_m, "t": t_m, "c": c_m, "d": datetime.date.today().strftime('%d/%m/%Y'),
