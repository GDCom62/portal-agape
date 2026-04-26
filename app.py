import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import json
import base64
import io

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    .mural-card { background-color: white; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .palavra-dia-card { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white !important; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 30px; }
    .palavra-dia-card h2, .palavra-dia-card p, .palavra-dia-card div { color: white !important; }
    .aviso-img { width: 100%; max-height: 500px; object-fit: contain; border-radius: 10px; margin-bottom: 15px; }
    .live-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 15px; box-shadow: 0 10px 15px rgba(0,0,0,0.2); margin-bottom: 20px; }
    .live-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v13.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS playlist (id INTEGER PRIMARY KEY, nome TEXT, url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY, data TEXT, codigo_membro TEXT, valor REAL, tipo TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.title("⛪ Portal Ágape")
        t_log, t_cad, t_rec = st.tabs(["🔐 Entrar", "📝 Cadastro", "🔑 Esqueci Senha"])
        
        with t_log:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()}); st.rerun()
                    st.error("Dados incorretos.")
        
        with t_cad:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastro realizado! Seu código para doações e recuperação é: {c}")

        with t_rec:
            with st.form("rec"):
                re_e, re_c, re_s = st.text_input("E-mail"), st.text_input("Código AG-XXXX"), st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Redefinir"):
                    check = consultar_db("SELECT id FROM membros WHERE email=:e AND codigo=:c", {"e":re_e, "c":re_c})
                    if not check.empty:
                        executar_query("UPDATE membros SET senha=:s WHERE email=:e", {"s": generate_password_hash(re_s), "e": re_e})
                        st.success("Senha atualizada!")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    opcoes = ["📢 Mural", "📺 Ao Vivo", "🎶 Louvores", "📖 Bíblia", "📊 Transparência"]
    if u['is_admin'] == 1: opcoes.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", opcoes)
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- AO VIVO (VÍDEO) ---
    if escolha == "📺 Ao Vivo":
        st.title("📺 Transmissão ao Vivo")
        l_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
        l_stat = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_ativa'")
        if not l_stat.empty and l_stat.iloc[0]['valor'] == 'Sim':
            embed = l_stat.iloc[0]['valor'] if "embed" in l_url.iloc[0]['valor'] else l_url.iloc[0]['valor'].replace("watch?v=", "embed/")
            st.markdown(f'<div class="live-container"><iframe src="{embed}" allowfullscreen></iframe></div>', unsafe_allow_html=True)
        else: st.info("Não há transmissões no momento.")

    # --- MURAL ---
    elif escolha == "📢 Mural":
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    # --- LOUVORES (PLAYLIST) ---
    elif escolha == "🎶 Louvores":
        st.title("🎶 Playlist Ágape")
        m_list = consultar_db("SELECT * FROM playlist")
        for _, m in m_list.iterrows():
            with st.container(border=True):
                st.write(f"🎵 **{m['nome']}**")
                st.audio(m['url'])

    # --- BÍBLIA ---
    elif escolha == "📖 Bíblia":
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap}).iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")

    # --- TRANSPARÊNCIA ---
    elif escolha == "📊 Transparência":
        df = consultar_db("SELECT data, codigo_membro, valor, tipo FROM financas ORDER BY id DESC")
        st.metric("Saldo Total", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

    # --- ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("Administração")
        t1, t2, t3, t4 = st.tabs(["🔴 Live/Playlist", "💰 Finanças", "📖 Bíblia", "📢 Mural"])
        
        with t1:
            st.subheader("Configurar Vídeo ao Vivo")
            l_u = st.text_input("URL YouTube")
            l_a = st.selectbox("Ativar Live?", ["Não", "Sim"])
            if st.button("Gravar Live"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v":l_u})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_ativa', :v)", {"v":l_a})
            
            st.divider()
            st.subheader("Adicionar Louvor (Link MP3)")
            n_m = st.text_input("Nome Música")
            u_m = st.text_input("Link URL")
            if st.button("Salvar Música"):
                executar_query("INSERT INTO playlist (nome, url) VALUES (:n, :u)", {"n":n_m, "u":u_m})

        with t2:
            membros = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0")
            with st.form("f_fin"):
                sel = st.selectbox("Membro", membros['nome'].tolist()) if not membros.empty else ""
                val = st.number_input("Valor", 0.0)
                if st.form_submit_button("Lançar"):
                    cod = membros[membros['nome'] == sel]['codigo'].values
                    executar_query("INSERT INTO financas (data, codigo_membro, valor) VALUES (:d, :c, :v)", {"d": datetime.now().strftime("%d/%m/%Y"), "c": cod, "v": val})
        
        with t3:
            f = st.file_uploader("acf.json", type=['json'])
            if f and st.button("Importar Bíblia"):
                dados = json.load(f)
                for liv in dados:
                    for ic, cl in enumerate(liv.get('chapters', [])):
                        for iv, tv in enumerate(cl):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l": str(liv.get('name')), "c": ic+1, "v": iv+1, "t": str(tv)})
                st.success("Bíblia Pronta!")
