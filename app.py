import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import redis, random, requests

# --- CONFIGURAÇÕES BÁSICAS ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# URLs Oficiais (Substitua pelas suas URLs reais do Railway)
URL_CHAT_RAILWAY = "railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- CONEXÃO BANCO E REDIS ---
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

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, data TEXT, autor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS curtidas (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, aviso_id INTEGER, usuario TEXT, texto TEXT, data TEXT)')
    
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

# --- COMPONENTES VISUAIS (LOUVOR FIXADO) ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        st.session_state.versiculo_dia = {
            "texto": "O Senhor é o meu pastor, nada me faltará.",
            "ref": "Salmos 23:1"
        }
    v = st.session_state.versiculo_dia
    st.markdown(f'<div class="floating-louvor"><small style="color:#1877f2;font-weight:bold">PALAVRA DE VIDA</small><br><i style="color:#333">"{v["texto"]}"</i><br><div style="text-align:right;color:#555;font-size:14px"><b>{v["ref"]}</b></div></div>', unsafe_allow_html=True)

# --- CONTROLE DE SESSÃO ---
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
            if st.form_submit_button("CADASTRAR"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:em,:s,0)", {"n":n,"em":em,"s":generate_password_hash(se)})
                st.success("Sucesso!"); st.session_state.tela = "login"; st.rerun()
        if st.button("Voltar"): st.session_state.tela = "login"; st.rerun()

else:
    # --- ÁREA LOGADA DO USUÁRIO ---
    u = st.session_state.user
    render_louvor()
    if r_db: r_db.set(f"online:{u['nome']}", "on", ex=60)

    with st.sidebar:
        st.markdown(f"### Olá, {u['nome']}! 🕊️")
        if st.button("🔄 Novo Louvor"):
            if 'versiculo_dia' in st.session_state: del st.session_state['versiculo_dia']
            st.rerun()
        if st.button("🚪 Sair"):
            st.session_state.clear(); st.rerun()

    # ABAS DE NAVEGAÇÃO INTERNA
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
        st.title("📖 Leitura Bíblica Almeida")
        st.write("Selecione o livro e o capítulo para renderizar os textos sagrados.")

        # Dicionário mapeado para a API do repositório público Almeida Revista e Corrigida
        livros_dict = {
            "Gênesis": "gn", "Êxodo": "ex", "Levítico": "lv", "Números": "num", "Deuteronômio": "dt",
            "Josué": "js", "Juízes": "jz", "Rute": "rt", "1 Samuel": "1sm", "2 Samuel": "2sm",
            "1 Reis": "1re", "2 Reis": "2re", "1 Crônicas": "1cr", "2 Crônicas": "2cr",
            "Esdras": "ez", "Neemias": "ne", "Ester": "et", "Jó": "jo", "Salmos": "ps",
            "Provérbios": "pv", "Eclesiastes": "ec", "Cânticos": "ct", "Isaías": "is",
            "Jeremias": "jr", "Lamentações": "lm", "Ezequiel": "ezq", "Daniel": "dn",
            "Oséias": "os", "Joel": "jl", "Amós": "am", "Obadias": "ob", "Jonas": "jn",
            "Miquéias": "mq", "Naum": "na", "Habacuque": "hc", "Sofonias": "sf",
            "Ageu": "ag", "Zacarias": "zc", "Malaquias": "ml",
            "Mateus": "mt", "Marcos": "mc", "Lucas": "lc", "João": "jo", "Atos": "at",
            "Romanos": "rm", "1 Coríntios": "1co", "2 Coríntios": "2co", "Gálatas": "gl",
            "Efésios": "ef", "Filipenses": "fp", "Colossenses": "cl",
            "1 Tessalonicenses": "1ts", "2 Tessalonicenses": "2ts",
            "1 Timóteo": "1tm", "2 Timóteo": "2tm", "Tito": "tt", "Filemom": "fm",
            "Hebreus": "hb", "Tiago": "tg", "1 Pedro": "1pe", "2 Pedro": "2pe",
            "1 João": "1jo", "2 João": "2jo", "3 João": "3jo", "Judas": "jd", "Apocalipse": "ap"
        }

        livro_pt = st.selectbox("Escolha o Livro:", list(livros_dict.keys()))
        livro_api = livros_dict[livro_pt]

        cap_selecionado = st.number_input("Escolha o Capítulo:", min_value=1, max_value=150, value=1, step=1)

        if st.button("📖 Ler Capítulo", use_container_width=True):
            with st.spinner("Buscando textos sagrados..."):
                # Requisição direta para o CDN estável de arquivos JSON bíblicos do repositório do MaatheusGois
                url_api = f"https://raw.githubusercontent.com/maatheusgois/bible/main/versions/pt-br/arc/{livro_api}/{cap_selecionado}.json"
                try:
                    resposta = requests.get(url_api, timeout=10)
                    if resposta.status_code == 200:
                        dados = resposta.json()
                        st.divider()
                        st.subheader(f"📖 {livro_pt} - Capítulo {cap_selecionado}")
                        
                        # Estruturação dinâmica versículo por versículo na tela
                        for id_ver, texto_ver in dados.items():
                            st.markdown(f"**{id_ver}** {texto_ver.strip()}")
                    else:
                        st.error("Capítulo inválido ou inexistente para este livro.")
                except:
                    st.error("Ocorreu uma lentidão na rede externa. Por favor, tente clicar novamente.")
