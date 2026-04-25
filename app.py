import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import json
import base64

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    .mural-card { background-color: white; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .aviso-img { width: 100%; max-height: 500px; object-fit: contain; border-radius: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v7.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, referencia TEXT, devocional TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT DEFAULT "Pendente")')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY, data TEXT, codigo_membro TEXT, valor REAL, tipo TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS ouvidoria (id INTEGER PRIMARY KEY, data TEXT, tipo TEXT, mensagem TEXT, autor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. LOGIN ---
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.title("⛪ Portal Ágape")
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Dados incorretos.")
# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    opcoes = ["📢 Mural Ágape", "📻 Rádio Gospel", "📊 Transparência", "📺 Ao Vivo", "📖 Bíblia", "🙏 Orações", "📣 Ouvidoria"]
    if u['is_admin'] == 1: opcoes.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", opcoes)
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- RÁDIO ---
    if escolha == "📻 Rádio Gospel":
        st.title("📻 Rádio Ágape Online")
        conf = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        url = conf.iloc[0]['valor'] if not conf.empty else "https://zeno.fm"
        st.markdown(f"""<div style='text-align:center; padding:30px; background:white; border-radius:20px; border: 1px solid #eee;'>
            <h3 style='color:#1e3a8a;'>Sintonizando...</h3><br>
            <audio id="meuaudio" controls autoplay style='width:100%'><source src="{url}" type="audio/mpeg"></audio>
            <p style='margin-top:10px; color:gray;'>Link atual: {url}</p>
        </div>""", unsafe_allow_html=True)

    # --- TRANSPARÊNCIA ---
    elif escolha == "📊 Transparência":
        st.title("📊 Prestação de Contas")
        df_fin = consultar_db("SELECT data, codigo_membro, valor, tipo FROM financas ORDER BY id DESC")
        if not df_fin.empty:
            c1, c2 = st.columns(2)
            c1.metric("Total de Receitas", f"R$ {df_fin['valor'].sum():,.2f}")
            c2.metric("Qtd de Lançamentos", len(df_fin))
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else: st.info("Nenhum lançamento financeiro.")

    # --- ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Painel do Administrador")
        t1, t2, t3, t4 = st.tabs(["📻 Rádio", "💰 Finanças", "📢 Avisos", "👥 Membros"])
        
        with t1:
            st.subheader("Configurar Link da Rádio")
            # Busca link atual para mostrar no campo
            link_atual_df = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
            link_inicial = link_atual_df.iloc[0]['valor'] if not link_atual_df.empty else ""
            
            with st.form("form_radio"):
                novo_link = st.text_input("Cole o link MP3/Stream da rádio:", value=link_inicial)
                if st.form_submit_button("✅ Gravar Link da Rádio"):
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :v)", {"v": novo_link})
                    st.success("Rádio configurada com sucesso!")
                    st.rerun()

        with t2:
            with st.form("fin"):
                c, v, t = st.text_input("Cód. Membro"), st.number_input("Valor", 0.0), st.selectbox("Tipo", ["Dízimo", "Oferta"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d, :c, :v, :t)",
                                   {"d": datetime.now().strftime("%d/%m/%Y"), "c": c, "v": v, "t": t})
                    st.success("Lançado!")

        with t3:
            # (Manter lógica de avisos com foto anterior)
            st.info("Utilize a aba Mural para ver o resultado.")

        with t4:
            st.dataframe(consultar_db("SELECT nome, email, codigo FROM membros"))

    # --- MURAL (CÓDIGO SIMPLIFICADO) ---
    elif escolha == "📢 Mural Ágape":
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f'<div class="mural-card" style="background:#1e3a8a; color:white;"><h2>📖 Palavra do Dia</h2><p>"{p["versiculo"]}"</p><strong>— {p["referencia"]}</strong></div>', unsafe_allow_html=True)
        
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            st.markdown(f'<div class="mural-card"><h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)
