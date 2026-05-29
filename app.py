import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- CONEXÃO BANCO DE DADOS LOCAL ---
@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v70.db", connect_args={"check_same_thread": False, "timeout": 30})

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

# Inicialização direta das tabelas do sistema e da Bíblia interna
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, data_cadastro TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS tabela_biblia (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    senha_hash = generate_password_hash("agape2026", method="pbkdf2:sha256")
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": senha_hash})

# --- POPULADOR LOCAL E OFF-LINE DA BÍBLIA (RODA APENAS UMA VEZ) ---
def popular_biblia_offline():
    verificar = consultar_db("SELECT id FROM tabela_biblia LIMIT 1")
    if verificar.empty:
        # Acervo nativo estável compactado para injeção rápida em lote
        acervo_inicial = {
            "Gênesis": {
                1: [
                    "No princípio criou Deus os céus e a terra.",
                    "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus pairava sobre a face das águas.",
                    "E disse Deus: Haja luz; e houve luz.",
                    "Viu Deus que a luz era boa; e fez Deus separação entre a luz e as trevas.",
                    "E Deus chamou à luz Dia; e às trevas chamou Noite. E foi a tarde e a manhã, o dia primeiro."
                ],
                2: [
                    "Assim os céus, a terra e todo o seu exército foram acabados.",
                    "E havendo Deus acabado no dia sétimo a obra que fizera, descansou no sétimo dia de toda a obra que fizera.",
                    "E abençoou Deus o dia sétimo, e o santificou; porque nele descansou de toda a sua obra."
                ]
            },
            "Salmos": {
                23: [
                    "O Senhor é o meu pastor, nada me faltará.",
                    "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.",
                    "Refrigera a minha alma; guia-me pelas veredas da justiça, por amor do seu nome.",
                    "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo; a tua vara e o teu cajado me consolam.",
                    "Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda.",
                    "Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na casa do Senhor por longos dias."
                ],
                100: [
                    "Celebrai com júbilo ao Senhor, todas as terras.",
                    "Servi ao Senhor com alegria; e apresentai-vos a ele com cântico.",
                    "Sabei que o Senhor é Deus; foi ele que nos fez, e não nós a nós mesmos; somos povo seu e ovelhas do seu pasto."
                ]
            },
            "João": {
                1: [
                    "No princípio era o Verbo, e o Verbo estava com Deus, e o Verbo era Deus.",
                    "Ele estava no princípio com Deus.",
                    "Todas as coisas foram feitas por ele, e sem ele nada do que foi feito se fez."
                ],
                3: [
                    "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.",
                    "Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo por ele."
                ]
            }
        }
        
        with engine.begin() as conn:
            for livro, capitulos in acervo_inicial.items():
                for cap, versos in capitulos.items():
                    for num_ver, texto in enumerate(versos, start=1):
                        conn.execute(
                            text("INSERT INTO tabela_biblia (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"),
                            {"l": livro, "c": cap, "v": num_ver, "t": texto}
                        )

popular_biblia_offline()

# --- ESTILIZAÇÃO VISUAL ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 15px; border-radius: 8px; color: #212529 !important; margin-bottom: 8px; border-left: 5px solid #FFA500; }
    </style>
""", unsafe_allow_html=True)

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

st.sidebar.title("🔐 Login Portal")
if not st.session_state.autenticado:
    u = st.sidebar.text_input("Usuário").strip()
    p = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar", use_container_width=True):
        df = consultar_db("SELECT senha FROM usuarios WHERE usuario = :u", {"u": u})
        if not df.empty and check_password_hash(str(df.loc[0, 'senha']), p):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("Dados incorretos.")

if st.session_state.autenticado:
    st.sidebar.success("Conectado!")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    menu = ["Início", "Bíblia", "Membros", "Financeiro"]
    escolha = st.selectbox("Selecione a Seção:", menu)
    st.divider()

    if escolha == "Início":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span>— João 3:16</span></div>', unsafe_allow_html=True)

    elif escolha == "Bíblia":
        st.subheader("📖 Leitura da Bíblia Sagrada")
        
        df_livros = consultar_db("SELECT DISTINCT livro FROM tabela_biblia ORDER BY id ASC")
        if not df_livros.empty:
            lista_livros = df_livros['livro'].tolist()
            col_l, col_c = st.columns(2)
            with col_l:
                livro_sel = st.selectbox("Livro:", lista_livros)
            
            df_caps = consultar_db("SELECT DISTINCT capitulo FROM tabela_biblia WHERE livro = :l ORDER BY capitulo ASC", {"l": livro_sel})
            lista_caps = df_caps['capitulo'].tolist()
            with col_c:
                cap_sel = st.selectbox("Capítulo:", lista_caps)
            
            st.write(f"### {livro_sel} - Capítulo {cap_sel}")
            st.divider()
            
            df_versos = consultar_db("SELECT versiculo, texto FROM tabela_biblia WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": livro_sel, "c": cap_sel})
            for idx, r in df_versos.iterrows():
                st.markdown(f'<div class="leitura-box"><b>{r["versiculo"]}.</b> {r["texto"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Estruturando os dados locais no banco. Por favor, atualize a página.")

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        with st.form("form_membro"):
            nome = st.text_input("Nome")
            cargo = st.text_input("Função")
            if st.form_submit_button("Cadastrar"):
                if nome:
                    executar_query("INSERT INTO membros (nome, cargo, data_cadastro) VALUES (:n, :c, :d)", {"n": nome, "c": cargo, "d": str(datetime.date.today())})
                    st.success("Cadastrado com sucesso!")
                    st.rerun()
        
        df_m = consultar_db("SELECT nome as Nome, cargo as Cargo, data_cadastro as [Data Cadastro] FROM membros")
        st.dataframe(df_m, use_container_width=True, hide_index=True)

    elif escolha == "Financeiro":
        st.subheader("💰 Livro Caixa")
        with st.form("form_fin"):
            tipo = st.selectbox("Movimento", ["Entrada", "Saída"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
            if st.form_submit_button("Lançar"):
                if desc and valor > 0:
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:t, :desc, :v, :d)", {"t": tipo, "desc": desc, "v": valor, "d": str(datetime.date.today())})
                    st.success("Lançado!")
                    st.rerun()

