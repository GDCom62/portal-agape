import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import redis, random

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
    
    # CORREÇÃO CRÍTICA: Usa len() no DataFrame para garantir validação correta e evitar duplicação
    check_admin = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
    if len(check_admin) == 0:
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

# --- BASE DE DADOS NATIVA DA BÍBLIA (100% OFFLINE) ---
biblia_local = {
    "Salmos": {
        "23": {"1": "O Senhor é o meu pastor, nada me faltará.", "2": "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.", "3": "Refrigera a minha alma; guia-me pelas veredas da justiça, por amor do seu nome.", "4": "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo.", "5": "Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda.", "6": "Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na casa do Senhor por longos dias."},
        "91": {"1": "Aquele que habita no esconderijo do Altíssimo, à sombra do Onipotente descansará.", "2": "Direi do Senhor: Ele é o meu Deus, o meu refúgio, a minha fortaleza, e nele confarei.", "3": "Porque ele te livrará do laço do passarinheiro, e da peste perniciosa.", "4": "Ele te cobrirá com as suas penas, e debaixo das suas asas te confiarás; a sua verdade será o teu escudo e broquel."}
    },
    "João": {
        "3": {"16": "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."}
    },
    "Filipenses": {
        "4": {"13": "Tudo posso naquele que me fortalece."}
    },
    "Gênesis": {
        "1": {"1": "No princípio criou Deus os céus e a terra.", "2": "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus se movia sobre a face das águas.", "3": "E disse Deus: Haja luz; e houve luz."}
    }
}

# --- COMPONENTES VISUAIS (LOUVOR FIXADO) ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        livro = random.choice(list(biblia_local.keys()))
        cap = random.choice(list(biblia_local[livro].keys()))
        ver = random.choice(list(biblia_local[livro][cap].keys()))
        st.session_state.versiculo_dia = {
            "texto": biblia_local[livro][cap][ver],
            "ref": f"{livro} {cap}:{ver}"
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
                if len(res) > 0 and check_password_hash(res.iloc[0]['senha'], s):
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
        # CORREÇÃO DO AVISO: Substituído st.components.v1.iframe por st.iframe moderno
        st.iframe(f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=agape", height=700, scrolling=True)

    with aba_biblia:
        st.title("📖 Leitura Bíblica Local")
        st.write("Acesso ultrarrápido aos principais livros e capítulos.")

        livro_pt = st.selectbox("Escolha o Livro:", list(biblia_local.keys()))
        lista_capitulos = list(biblia_local[livro_pt].keys())
        cap_selecionado = st.selectbox("Escolha o Capítulo:", lista_capitulos)

        if st.button("📖 Ler Capítulo", use_container_width=True):
            st.divider()
            st.subheader(f"📖 {livro_pt} - Capítulo {cap_selecionado}")
            versiculos = biblia_local[livro_pt][cap_selecionado]
            for id_ver, texto_ver in versiculos.items():
                st.markdown(f"**{id_ver}** {texto_ver}")
