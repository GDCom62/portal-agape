import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import redis, random

# --- CONFIGURAÇÕES BÁSICAS ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# URLs (Substitua pelas suas URLs oficiais no deploy)
URL_CHAT_RAILWAY = "https://railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- CONEXÃO BANCO E REDIS ---
# O 'check_same_thread': False é vital para o Streamlit não cair
engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False})

try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    r_db = None

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except:
            return pd.DataFrame()
def baixar_biblia_automatico():
    import requests
    try:
        with st.spinner("📖 Configurando a Bíblia Sagrada pela primeira vez... Por favor, aguarde 30 segundos."):
            url = "githubusercontent.com"
            df = pd.read_csv(url)
            df = df[['livro', 'capitulo', 'versiculo', 'texto']]
            df.columns = ['livro', 'cap', 'ver', 'texto']
            
            # Grava direto no banco de dados conectado
            with engine.begin() as conn:
                df.to_sql('biblia', conn, if_exists='replace', index=False)
            st.success("✅ Bíblia configurada com sucesso! Atualizando...")
            st.rerun()
    except Exception as e:
        st.error(f"Erro ao carregar Bíblia automaticamente: {e}")

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT, autor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS curtidas (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT, texto TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES ('Admin', 'admin@agape.com', :pw, 1)", {"pw": pw})

init_db()

# --- ESTILIZAÇÃO CSS ---
def aplicar_estilo():
    st.markdown("""<style>
        .stApp { background: linear-gradient(135deg, #f0f2f5 0%, #c9d6ff 100%); }
        [data-testid="stForm"] { background-color: white !important; padding: 30px !important; border-radius: 20px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important; border: none !important; max-width: 450px; margin: auto !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #ced0d4; margin-bottom: 10px; }
        .floating-louvor { position: fixed; bottom: 25px; right: 25px; width: 300px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-left: 6px solid #1877f2; border-radius: 12px; padding: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); z-index: 999999; }
        header, footer { visibility: hidden; }
    </style>""", unsafe_allow_html=True)

# --- COMPONENTES ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        try:
            df = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            st.session_state.versiculo_dia = df.iloc[0].to_dict() if not df.empty else {"texto": "O Senhor é bom.", "livro": "Salmos", "cap": 1, "ver": 1}
        except:
            st.session_state.versiculo_dia = {"texto": "Deus é fiel.", "livro": "1 Coríntios", "cap": 1, "ver": 9}
    
    v = st.session_state.versiculo_dia
    st.markdown(f'<div class="floating-louvor"><small style="color:#1877f2;font-weight:bold">PALAVRA DE VIDA</small><br><i style="color:#333">"{v["texto"]}"</i><br><div style="text-align:right;color:#555;font-size:14px"><b>{v["livro"]} {v["cap"]}:{v["ver"]}</b></div></div>', unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

aplicar_estilo()

if not st.session_state.logado:
    st.markdown("<br><h1 style='text-align:center; color:#1877f2;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
    if st.session_state.tela == "login":
        with st.form("login_f"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("Login inválido")
        if st.button("Cadastrar novo membro"): st.session_state.tela = "cadastro"; st.rerun()
    else:
        with st.form("cad_f"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("SALVAR"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:em,:s,0)", {"n":n,"em":em,"s":generate_password_hash(se)})
                st.success("Sucesso!"); st.session_state.tela = "login"; st.rerun()
        if st.button("Voltar"): st.session_state.tela = "login"; st.rerun()

else:
    # --- ÁREA DO USUÁRIO ---
    u = st.session_state.user
    render_louvor()
    if r_db: r_db.set(f"online:{u['nome']}", "on", ex=60)

    with st.sidebar:
        st.markdown(f"### Olá, {u['nome']}!")
        if st.button("🔄 Novo Louvor"):
            if 'versiculo_dia' in st.session_state: del st.session_state['versiculo_dia']
            st.rerun()
        if st.button("🚪 Sair"):
            st.session_state.clear(); st.rerun()

       # ORGANIZAÇÃO POR ABAS PARA NÃO TRAVAR
    aba_mural, aba_chat, aba_biblia = st.tabs(["🏠 Mural", "💬 Chat Ágape", "📖 Bíblia"])

    with aba_mural:
        with st.expander("📢 Postar Mensagem"):
            msg = st.text_area("O que deseja compartilhar?")
            if st.button("Publicar"):
                executar_query("INSERT INTO avisos (conteudo, data, autor) VALUES (:c,:d,:a)", {"c":msg, "d":datetime.now().strftime("%d/%m %H:%M"), "a":u['nome']})
                st.rerun()
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-post"><b>@{av["autor"]}</b> • <small>{av["data"]}</small><p>{av["conteudo"]}</p></div>', unsafe_allow_html=True)
            if u['is_admin'] and st.button("🗑️ Excluir", key=f"del_{av['id']}"):
                executar_query("DELETE FROM avisos WHERE id=:id", {"id":av['id']})
                st.rerun()

    with aba_chat:
        st.components.v1.iframe(f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=agape", height=700, scrolling=True)

    with aba_biblia:
        st.title("📖 Leitura Bíblica")
        
        # 1. Busca todos os livros cadastrados
        df_livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        
        if not df_livros.empty:
            lista_livros = df_livros['livro'].tolist()
            
            # Seletor do Livro
            livro_selecionado = st.selectbox("Escolha o Livro:", lista_livros)
            
            if livro_selecionado:
                # 2. Busca os capítulos existentes
                df_caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro = :l ORDER BY cap", {"l": livro_selecionado})
                lista_caps = df_caps['cap'].tolist()
                
                # Seletor do Capítulo
                cap_selecionado = st.selectbox("Escolha o Capítulo:", lista_caps)
                
                if cap_selecionado:
                    st.divider()
                    st.subheader(f"{livro_selecionado}, Capítulo {cap_selecionado}")
                    
                    # 3. Busca e exibe todos os versículos
                    df_versiculos = consultar_db(
                        "SELECT ver, texto FROM biblia WHERE livro = :l AND cap = :c ORDER BY ver",
                        {"l": livro_selecionado, "c": cap_selecionado}
                    )
                    
                    # Exibe o texto formatado
                    for _, row in df_versiculos.iterrows():
                        st.markdown(f"**{row['ver']}** {row['texto']}")
        else:
            st.warning("Nenhum livro encontrado no banco de dados. Certifique-se de rodar o script de importação.")
