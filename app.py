import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json, redis, random

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")
URL_CHAT_RAILWAY = "https://railway.app"
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- CONEXÃO REDIS ---
try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    st.error("Erro ao conectar ao Redis.")

# --- ESTILIZAÇÃO CUSTOMIZADA ---
def aplicar_estilo():
    st.markdown("""<style>
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #1c1e21 !important; font-size: 16px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        
        /* Estilo dos Cards do Mural */
        .card-post { 
            background: white; padding: 20px; border-radius: 12px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; 
            border: 1px solid #ced0d4; 
        }
        
        /* LOUVOR FLUTUANTE PREMIUM */
        .floating-louvor {
            position: fixed;
            bottom: 25px;
            right: 25px;
            width: 320px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-left: 6px solid #1877f2;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            z-index: 999999;
            animation: fadeIn 1s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        
        .label-louvor { color: #1877f2 !important; font-weight: bold; font-size: 12px !important; text-transform: uppercase; margin-bottom: 5px; display: block; }
        .texto-louvor { font-style: italic; color: #1c1e21 !important; line-height: 1.4; font-size: 16px !important; font-weight: 500; }
        .ref-louvor { text-align: right; margin-top: 8px; font-weight: bold; color: #4b4f56; font-size: 14px !important; }
    </style>""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params=None):
    if params is None: params = {}
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params=None):
    if params is None: params = {}
    with engine.connect() as conn:
        try: return pd.read_sql_query(text(sql), conn, params=params)
        except: return pd.DataFrame()

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    
    # Inserir alguns versículos padrão se a bíblia estiver vazia
    if consultar_db("SELECT id FROM biblia LIMIT 1").empty:
        v_padrao = [
            ("Salmos", 23, 1, "O Senhor é o meu pastor, nada me faltará."),
            ("João", 3, 16, "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito."),
            ("Filipenses", 4, 13, "Tudo posso naquele que me fortalece."),
            ("Salmos", 126, 3, "Grandes coisas fez o Senhor por nós, por isso estamos alegres.")
        ]
        for l, c, v, t in v_padrao:
            executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":l,"c":c,"v":v,"t":t})

    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- COMPONENTE DE LOUVOR ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        df_biblia = consultar_db("SELECT * FROM biblia")
        if not df_biblia.empty:
            st.session_state.versiculo_dia = df_biblia.sample(1).iloc[0]
        else:
            st.session_state.versiculo_dia = {"texto": "Deus é amor.", "livro": "1 João", "cap": 4, "ver": 8}

    v = st.session_state.versiculo_dia
    st.markdown(f"""
        <div class="floating-louvor">
            <span class="label-louvor">📖 Palavra de Vida</span>
            <div class="texto-louvor">"{v['texto']}"</div>
            <div class="ref-louvor">— {v['livro']} {v['cap']}:{v['ver']}</div>
        </div>
    """, unsafe_allow_html=True)

# --- LÓGICA DE NAVEGAÇÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

aplicar_estilo()

if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center; color:#1877f2;'>Portal Ágape</h1>", unsafe_allow_html=True)
    if st.session_state.tela == "login":
        with st.form("login_form"):
            st.subheader("Acesse sua conta")
            e = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    u_data = res.iloc[0].to_dict()
                    st.session_state.update({"logado": True, "user": u_data})
                    r_db.set(f"online:{u_data['nome']}", "online", ex=60)
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")
        st.button("Não tem conta? Cadastre-se", on_click=lambda: st.session_state.update({"tela": "cadastro"}))
    else:
        with st.form("cad_form"):
            st.subheader("Criar nova conta")
            n = st.text_input("Nome Completo")
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:em,:se,0)", 
                              {"n":n, "em":em, "se":generate_password_hash(se)})
                st.success("Conta criada! Faça login.")
                st.session_state.tela = "login"
                st.rerun()
        st.button("Voltar ao Login", on_click=lambda: st.session_state.update({"tela": "login"}))

else:
    # --- ÁREA LOGADA ---
    u = st.session_state.user
    r_db.set(f"online:{u['nome']}", "online", ex=60)
    
    # Exibe o louvor flutuante em todas as telas logadas
    render_louvor()

    with st.sidebar:
        st.markdown(f"### Bem-vindo, \n## {u['nome']}! 🕊️")
        st.divider()
        menu = st.radio("Navegação", ["🏠 Mural da Igreja", "💬 Chat Ágape", "📖 Bíblia Sagrada"], label_visibility="collapsed")
        
        st.divider()
        if st.button("🔄 Nova Palavra de Louvor"):
            st.session_state.pop('versiculo_dia')
            st.rerun()
            
        if st.button("🚪 Sair do Portal", use_container_width=True):
            r_db.delete(f"online:{u['nome']}")
            st.session_state.clear()
            st.rerun()

    if menu == "🏠 Mural da Igreja":
        st.title("Mural da Comunidade")
        
        # Área para Admin postar avisos
        if u['is_admin']:
            with st.expander("📢 Postar Novo Aviso (Admin)"):
                msg = st.text_area("Mensagem do aviso")
                if st.button("Publicar"):
                    executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c, :d)", 
                                  {"c": msg, "d": datetime.now().strftime("%d/%m/%Y %H:%M")})
                    st.success("Postado!")
                    st.rerun()

        # Exibição dos avisos
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, row in avisos.iterrows():
            st.markdown(f"""
                <div class="card-post">
                    <small style='color:#65676b'>{row['data']}</small>
                    <p style='margin-top:10px;'>{row['conteudo']}</p>
                </div>
            """, unsafe_allow_html=True)

    elif menu == "💬 Chat Ágape":
        st.title("Chat Online Premium")
        link = f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=agape_oficial"
        st.markdown(f"""
            <div style="text-align:center; padding:100px 20px; background:white; border-radius:15px; border:1px solid #ddd;">
                <h2>Conecte-se com os irmãos</h2>
                <p>O chat abrirá em uma nova aba segura.</p><br>
                <a href="{link}" target="_blank" 
                   style="background:#1877f2; color:white; padding:18px 45px; text-decoration:none; border-radius:30px; font-weight:bold; font-size:20px;">
                   ENTRAR NO CHAT AGORA
                </a>
            </div>
        """, unsafe_allow_html=True)

    elif menu == "📖 Bíblia Sagrada":
        st.title("Pesquisa Bíblica")
        busca = st.text_input("Buscar palavra ou livro...")
        if busca:
            res = consultar_db("SELECT * FROM biblia WHERE texto LIKE :b OR livro LIKE :b LIMIT 20", {"b": f"%{busca}%"})
            st.dataframe(res, use_container_width=True)
        else:
            st.info("Digite algo para buscar na base de dados da igreja.")

