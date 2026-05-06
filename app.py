import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, re, unicodedata
import redis
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURAÇÕES E ESTILO DIVINO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# Conexão Redis (Ambiente Docker ou Local)
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
try:
    r_chat = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)
except:
    st.error("Falha ao conectar ao servidor de mensagens.")

def aplicar_estilo_divino(tam_fonte):
    st.markdown(f"""
        <style>
        .stApp {{ background: #fdfbf0; }}
        h1, h2, h3 {{ color: #b8860b !important; text-align: center; font-weight: bold; font-family: 'Georgia', serif; }}
        p, span, label, li, .stMarkdown, .stSelectbox label {{ color: #000000 !important; font-weight: 600 !important; }}
        .card-mural {{ background: white; padding: 20px; border-radius: 15px; border: 2px solid #ffd700; margin-bottom: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .palavra-do-dia {{ background: #fff3ad; padding: 30px; border-radius: 20px; border: 3px double #b8860b; text-align: center; margin-bottom: 30px; }}
        .palavra-texto {{ font-size: 32px !important; color: #1e3a8a !important; font-family: serif; font-style: italic; font-weight: bold; line-height: 1.3; }}
        .caixa-leitura {{ background: white; padding: 30px; border-radius: 10px; border: 2px solid #b8860b; font-size: {tam_fonte}px !important; line-height: 1.7; color: black !important; font-family: serif; }}
        /* Estilo Balão WhatsApp */
        .chat-container {{ display: flex; flex-direction: column; gap: 10px; padding: 10px; }}
        .bubble {{ padding: 10px 15px; border-radius: 15px; max-width: 80%; position: relative; margin-bottom: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); font-size: 16px; }}
        .bubble.mine {{ align-self: flex-end; background-color: #dcf8c6; border-bottom-right-radius: 2px; }}
        .bubble.others {{ align-self: flex-start; background-color: white; border-bottom-left-radius: 2px; }}
        .chat-user {{ font-size: 0.75em; font-weight: bold; color: #075e54; display: block; }}
        .chat-time {{ font-size: 0.65em; color: #999; float: right; margin-top: 4px; margin-left: 8px; }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def limpar_link(texto):
    texto = unicodedata.normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', texto)

def exibir_logo(largura=150):
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)
    else: st.markdown(f'<h1 style="text-align:center; color:#b8860b; margin:0;">⛪ ÁGAPE</h1>', unsafe_allow_html=True)

# --- 3. LOGIN / ÁREA LOGADA ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_divino(22)
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        exibir_logo(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Criada! Código: {c}")

else:
    u = st.session_state.user
    with st.sidebar:
        exibir_logo(80)
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural da Fé", "📖 Bíblia Sagrada", "🎥 Comunhão", "💰 Tesouraria"])
        tam_fonte = st.select_slider("Tamanho Fonte", options=range(18, 48, 2), value=24)
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    aplicar_estilo_divino(tam_fonte)

    # --- MENU COMUNHÃO (O CHAT UPGRADE) ---
    if menu == "🎥 Comunhão":
        st_autorefresh(interval=3000, key="chat_refresh") # Atualiza a cada 3s
        st.title("💬 Espaço de Comunhão")
        
        c1, c2 = st.columns([0.3, 0.7])
        
        with c1:
            st.subheader("👥 Irmãos")
            m_db = consultar_db("SELECT nome FROM membros ORDER BY nome ASC")
            outros = [n for n in m_db['nome'] if n != u['nome']]
            dest = st.radio("Conversar com:", ["Todos (Grupo)"] + outros)
            
            # Define o Canal do Redis
            if dest == "Todos (Grupo)":
                canal = "chat_geral"
            else:
                nomes = sorted([u['nome'], dest])
                canal = f"chat_{limpar_link(nomes[0])}_{limpar_link(nomes[1])}"

            st.divider()
            st.link_button("🎥 VÍDEO CHAMADA", f"https://jit.si_{canal}", use_container_width=True)

        with c2:
            st.subheader(f"Chat: {dest}")
            
            # Container de mensagens
            container = st.container(height=450)
            with container:
                msgs = r_chat.lrange(canal, 0, -1)
                for m_raw in msgs:
                    m = json.loads(m_raw)
                    is_mine = m['user'] == u['nome']
                    classe = "mine" if is_mine else "others"
                    
                    # Renderiza o balão
                    st.markdown(f"""
                        <div class="chat-container" style="align-items: {'flex-end' if is_mine else 'flex-start'};">
                            <div class="bubble {classe}">
                                <span class="chat-user">{m['user']}</span>
                                {m['text']}
                                <span class="chat-time">{m['time']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

            # Campo de envio
            with st.form("msg_form", clear_on_submit=True):
                msg_input = st.text_input("Digite sua mensagem e aperte Enter", placeholder="Sua mensagem...")
                if st.form_submit_button("Enviar"):
                    if msg_input:
                        payload = json.dumps({
                            "user": u['nome'],
                            "text": msg_input,
                            "time": datetime.now().strftime("%H:%M")
                        })
                        r_chat.rpush(canal, payload)
                        r_chat.ltrim(canal, -50, -1)
                        st.rerun()

    # --- (Outros menus omitidos para brevidade, mantenha o seu código original neles) ---
    elif menu == "📢 Mural da Fé":
        st.title("📢 Mural da Fé")
        # ... seu código do Mural aqui ...
