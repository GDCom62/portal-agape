import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import redis, random

# --- CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")
URL_CHAT_RAILWAY = "https://railway.app" # URL do seu Flask
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# Conexão Redis
try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    st.error("Erro ao conectar ao Redis.")

# --- BANCO DE DADOS (SQLite) ---
# Substitua sua linha da engine por esta:
engine = create_engine(
    "sqlite:///agape_v60.db", 
    connect_args={"check_same_thread": False}
)

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except:
            return pd.DataFrame()

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT, autor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS curtidas (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT, texto TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    
    # Criar Admin Padrão
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- ESTILIZAÇÃO CSS ---
def aplicar_estilo():
    st.markdown("""<style>
        /* Fundo e Geral */
        .stApp { background: linear-gradient(135deg, #f0f2f5 0%, #c9d6ff 100%); }
        
        /* Card de Login Centralizado */
        [data-testid="stForm"] {
            background-color: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
            border: none !important;
            max-width: 450px;
            margin: auto !important;
        }

        /* Estilo do Mural */
        .card-post { 
            background: white; padding: 20px; border-radius: 12px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #ced0d4; 
            margin-bottom: 0px;
        }
        
        /* Louvor Flutuante */
        .floating-louvor {
            position: fixed; bottom: 25px; right: 25px; width: 300px;
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
            border-left: 6px solid #1877f2; border-radius: 12px;
            padding: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); z-index: 999999;
        }

        /* Botões */
        .stButton>button { border-radius: 50px !important; font-weight: bold !important; }
        
        /* Esconder Streamlit Header/Footer */
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>""", unsafe_allow_html=True)

# --- COMPONENTES VISUAIS ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        df = consultar_db("SELECT * FROM biblia")
        if not df.empty:
            st.session_state.versiculo_dia = df.sample(1).iloc[0].to_dict()
        else:
            st.session_state.versiculo_dia = {"texto": "O Senhor é o meu pastor.", "livro": "Salmos", "cap": 23, "ver": 1}
    
    v = st.session_state.versiculo_dia
    st.markdown(f"""
        <div class="floating-louvor">
            <small style="color:#1877f2;font-weight:bold">PALAVRA DE VIDA</small><br>
            <i style="color:#333">"{v['texto']}"</i><br>
            <div style="text-align:right; color:#555; font-size:14px"><b>{v['livro']} {v['cap']}:{v['ver']}</b></div>
        </div>
    """, unsafe_allow_html=True)

def verificar_notificacoes():
    n = r_db.get("ultima_notificacao")
    if n: st.toast(n, icon="📢")

# --- LÓGICA DE TELAS ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

aplicar_estilo()

if not st.session_state.logado:
    st.markdown("<br><h1 style='text-align:center; color:#1877f2;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
    
    if st.session_state.tela == "login":
        with st.form("login_f"):
            st.subheader("Entrar no Portal")
            e = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("E-mail ou senha inválidos.")
        if st.button("Criar nova conta"): 
            st.session_state.tela = "cadastro"; st.rerun()
    else:
        with st.form("cad_f"):
            st.subheader("Novo Cadastro")
            n = st.text_input("Nome")
            em = st.text_input("E-mail")
            se = st.text_input("Senha", type="password")
            if st.form_submit_button("CADASTRAR"):
                pw = generate_password_hash(se)
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:em,:pw,0)", {"n":n,"em":em,"pw":pw})
                st.success("Conta criada!"); st.session_state.tela = "login"; st.rerun()
        if st.button("Voltar ao Login"): 
            st.session_state.tela = "login"; st.rerun()

else:
    # --- ÁREA LOGADA ---
    u = st.session_state.user
    r_db.set(f"online:{u['nome']}", "online", ex=60)
    verificar_notificacoes()
    render_louvor()

    with st.sidebar:
        st.markdown(f"### Olá, {u['nome']}! 🕊️")
        qtd_on = len(r_db.keys("online:*"))
        st.success(f"● {qtd_on} Online agora")
        menu = st.radio("Navegação", ["🏠 Mural", "💬 Chat Ágape", "📖 Bíblia"])
        
        st.divider()
        if st.button("🔄 Novo Louvor"):
            if 'versiculo_dia' in st.session_state: del st.session_state['versiculo_dia']
            st.rerun()
        if st.button("🚪 Sair"):
            r_db.delete(f"online:{u['nome']}")
            st.session_state.clear(); st.rerun()

    if menu == "🏠 Mural":
        st.title("Mural da Igreja")
        with st.expander("📢 Compartilhar algo"):
            msg = st.text_area("Mensagem")
            if st.button("Postar"):
                executar_query("INSERT INTO avisos (conteudo, data, autor) VALUES (:c,:d,:a)", 
                              {"c":msg, "d":datetime.now().strftime("%d/%m %H:%M"), "a":u['nome']})
                r_db.set("ultima_notificacao", f"Novo post de {u['nome']}", ex=10)
                st.rerun()

        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-post"><b>@{av["autor"]}</b> • <small>{av["data"]}</small><p>{av["conteudo"]}</p></div>', unsafe_allow_html=True)
            
            # Curtidas e Comentários
            c1, c2, c3 = st.columns([0.2, 0.6, 0.2])
            curtidas = consultar_db("SELECT count(*) as total FROM curtidas WHERE aviso_id=:id", {"id":av['id']}).iloc[0]['total']
            if c1.button(f"❤️ {curtidas}", key=f"lk_{av['id']}"):
                executar_query("INSERT INTO curtidas (aviso_id, usuario) VALUES (:id,:u)", {"id":av['id'], "u":u['nome']})
                st.rerun()
            
            with c2.expander("Comentários"):
                for _, com in consultar_db("SELECT * FROM comentarios WHERE aviso_id=:id", {"id":av['id']}).iterrows():
                    st.write(f"**{com['usuario']}**: {com['texto']}")
                with st.form(f"f_{av['id']}", clear_on_submit=True):
                    t = st.text_input("Comentar")
                    if st.form_submit_button("OK"):
                        executar_query("INSERT INTO comentarios (aviso_id, usuario, texto, data) VALUES (:id,:u,:t,:d)", 
                                      {"id":av['id'], "u":u['nome'], "t":t, "d":""})
                        st.rerun()
            
            if u['is_admin'] and c3.button("🗑️", key=f"del_{av['id']}"):
                executar_query("DELETE FROM avisos WHERE id=:id", {"id":av['id']})
                st.rerun()
            st.divider()

    elif menu == "💬 Chat Ágape":
        st.components.v1.iframe(f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=agape", height=700, scrolling=True)

    elif menu == "📖 Bíblia":
        st.title("Bíblia Sagrada")
        busca = st.text_input("Pesquisar versículo...")
        if busca:
            res = consultar_db("SELECT * FROM biblia WHERE texto LIKE :b LIMIT 20", {"b":f"%{busca}%"})
            st.table(res[['livro', 'cap', 'ver', 'texto']])
