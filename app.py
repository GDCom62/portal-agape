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
    .chat-msg { background: white; padding: 10px; border-radius: 10px; margin-bottom: 5px; border-left: 3px solid #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v7.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, referencia TEXT, devocional TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT DEFAULT "Pendente")')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS chat_live (id INTEGER PRIMARY KEY, nome TEXT, mensagem TEXT, hora TEXT)')
    # NOVAS TABELAS: Finanças e Ouvidoria
    executar_query('CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY, data TEXT, codigo_membro TEXT, valor REAL, tipo TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS ouvidoria (id INTEGER PRIMARY KEY, data TEXT, tipo TEXT, mensagem TEXT, autor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.title("⛪ Portal Ágape")
        t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_log:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
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
                    st.success(f"Cadastrado! Seu código: {c}")
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    opcoes = ["📢 Mural Ágape", "📻 Rádio Gospel", "📊 Transparência", "📺 Ao Vivo", "📖 Bíblia", "🙏 Orações", "📣 Ouvidoria"]
    if u['is_admin'] == 1: opcoes.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", opcoes)
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- RÁDIO GOSPEL ---
    if escolha == "📻 Rádio Gospel":
        st.title("📻 Rádio Ágape Online")
        radio_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        url = radio_url.iloc[0]['valor'] if not radio_url.empty else "https://zeno.fm"
        st.markdown(f"""<div style='text-align:center; padding:50px; background:white; border-radius:20px;'>
            <h3>Tocando agora...</h3><br>
            <audio controls autoplay style='width:100%'><source src="{url}" type="audio/mpeg"></audio>
        </div>""", unsafe_allow_html=True)

    # --- TRANSPARÊNCIA ---
    elif escolha == "📊 Transparência":
        st.title("📊 Prestação de Contas")
        df_fin = consultar_db("SELECT data, codigo_membro, valor, tipo FROM financas ORDER BY id DESC")
        if not df_fin.empty:
            st.metric("Total de Receitas", f"R$ {df_fin['valor'].sum():,.2f}")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else: st.info("Nenhum registro financeiro disponível.")

    # --- OUVIDORIA ---
    elif escolha == "📣 Ouvidoria":
        st.title("📣 Elogios e Sugestões")
        with st.form("ouvidoria_f", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Elogio", "Sugestão", "Reclamação"])
            msg = st.text_area("Sua mensagem")
            anonimo = st.checkbox("Enviar como Anônimo")
            if st.form_submit_button("Enviar"):
                autor = "Anônimo" if anonimo else u['nome']
                executar_query("INSERT INTO ouvidoria (data, tipo, mensagem, autor) VALUES (:d, :t, :m, :a)",
                               {"d": datetime.now().strftime("%d/%m/%Y"), "t": tipo, "m": msg, "a": autor})
                st.success("Obrigado! Sua mensagem foi enviada ao conselho.")

    # --- ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Painel Gestor")
        tab_f, tab_o, tab_r, tab_l = st.tabs(["💰 Lançar Finanças", "👂 Ouvidoria", "📻 Rádio", "📺 Live"])
        
        with tab_f:
            with st.form("f_fin"):
                cod = st.text_input("Código do Membro")
                val = st.number_input("Valor", min_value=0.0)
                tp = st.selectbox("Tipo", ["Dízimo", "Oferta", "Doação"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d, :c, :v, :t)",
                                   {"d": datetime.now().strftime("%d/%m/%Y"), "c": cod, "v": val, "t": tp})
                    st.success("Lançado!")

        with tab_o:
            st.write(consultar_db("SELECT * FROM ouvidoria ORDER BY id DESC"))

        with tab_r:
            with st.form("r_f"):
                url_r = st.text_input("Link Streaming Rádio (MP3)")
                if st.form_submit_button("Salvar Rádio"):
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :v)", {"v": url_r})
                    st.success("Link atualizado!")
        
        with tab_l:
            with st.form("live_f"):
                ativa = st.selectbox("Live ativa?", ["Não", "Sim"])
                url_l = st.text_input("URL YouTube")
                if st.form_submit_button("Salvar"):
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_ativa', :v)", {"v": ativa})
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :u)", {"u": url_l})
                    st.success("Salvo!")

    # --- MURAL (Omitido aqui por espaço, mas deve ser mantido do código anterior) ---
    elif escolha == "📢 Mural Ágape":
        # (Código do Mural com fotos e Palavra do Dia que já temos)
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f"""<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p style='font-size: 1.4em; font-style: italic;'>"{p['versiculo']}"</p><strong>— {p['referencia']}</strong></div>""", unsafe_allow_html=True)
        
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img_tag = f'<img src="{r["img_url"]}" class="aviso-img">' if r.get("img_url") else ""
            st.markdown(f'<div class="mural-card">{img_tag}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)
