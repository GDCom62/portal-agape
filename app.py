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

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    .mural-card { background-color: white; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .palavra-dia-card { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white !important; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 30px; }
    .palavra-dia-card h2, .palavra-dia-card p { color: white !important; }
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
                    st.success(f"Cadastrado! Seu código é: {c}")
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
        url_reset = f"{url}?v={datetime.now().microsecond}"
        st.markdown(f"""<div style='text-align:center; padding:30px; background:white; border-radius:20px; border: 1px solid #eee;'>
            <h3 style='color:#1e3a8a;'>Estação Conectada</h3><br>
            <audio controls autoplay style='width:100%'><source src="{url_reset}" type="audio/mpeg"></audio>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄 Reiniciar Player"): st.rerun()

    # --- TRANSPARÊNCIA ---
    elif escolha == "📊 Transparência":
        st.title("📊 Prestação de Contas")
        df_fin = consultar_db("SELECT data, codigo_membro, valor, tipo FROM financas ORDER BY id DESC")
        if not df_fin.empty:
            st.metric("Total de Receitas", f"R$ {df_fin['valor'].sum():,.2f}")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else: st.info("Nenhum lançamento financeiro.")

    # --- MURAL ---
    elif escolha == "📢 Mural Ágape":
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f"""<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p style='font-size: 1.4em; font-style: italic;'>"{p['versiculo']}"</p><strong>— {p['referencia']}</strong><br><br><div>{p['devocional']}</div></div>""", unsafe_allow_html=True)
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p><small>{r["data"]}</small></div>', unsafe_allow_html=True)

    # --- AO VIVO ---
    elif escolha == "📺 Ao Vivo":
        st.title("📺 Transmissão ao Vivo")
        l_stat = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_ativa'")
        l_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
        if not l_stat.empty and l_stat.iloc[0]['valor'] == 'Sim':
            embed = l_url.iloc[0]['valor'].replace("watch?v=", "embed/")
            st.markdown(f'<iframe width="100%" height="500" src="{embed}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
            st.subheader("💬 Chat da Live")
            with st.form("live_chat", clear_on_submit=True):
                m_chat = st.text_input("Sua mensagem")
                if st.form_submit_button("Enviar"):
                    executar_query("INSERT INTO chat_live (nome, mensagem, hora) VALUES (:n, :m, :h)", {"n": u['nome'], "m": m_chat, "h": datetime.now().strftime("%H:%M")})
                    st.rerun()
            for _, m in consultar_db("SELECT * FROM chat_live ORDER BY id DESC LIMIT 10").iterrows():
                st.markdown(f"**{m['nome']}**: {m['mensagem']}")
        else: st.info("Sem live ativa.")

    # --- ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Administração")
        tab1, tab2, tab3, tab4 = st.tabs(["📻 Rádio", "💰 Finanças", "📢 Avisos", "👥 Membros"])
        with tab1:
            res_link = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
            atual = res_link.iloc[0]['valor'] if not res_link.empty else ""
            with st.form("set_radio"):
                novo_link = st.text_input("Link MP3 da Rádio", value=atual)
                if st.form_submit_button("Salvar Rádio"):
                    executar_query("DELETE FROM configuracoes WHERE chave='radio_url'")
                    executar_query("INSERT INTO configuracoes (chave, valor) VALUES ('radio_url', :v)", {"v": novo_link})
                    st.success("Salvo!"); st.rerun()
        with tab2:
            with st.form("add_fin"):
                c, v, t = st.text_input("Código Membro"), st.number_input("Valor", 0.0), st.selectbox("Tipo", ["Dízimo", "Oferta"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d, :c, :v, :t)", {"d": datetime.now().strftime("%d/%m/%Y"), "c": c, "v": v, "t": t})
                    st.success("Sucesso!")
        with tab3:
            with st.form("add_av"):
                ti, co, f = st.text_input("Título"), st.text_area("Mensagem"), st.file_uploader("Foto", type=['jpg', 'png'])
                if st.form_submit_button("Postar"):
                    img_b64 = f"data:image/png;base64,{base64.b64encode(f.getvalue()).decode()}" if f else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_url) VALUES (:t, :c, :d, :i)", {"t":ti, "c":co, "d":datetime.now().strftime("%d/%m/%Y"), "i":img_b64})
                    st.success("Postado!")
        with tab4:
            st.dataframe(consultar_db("SELECT nome, email, codigo FROM membros"))

    # --- BÍBLIA (Simplificada para o código não ficar gigante) ---
    elif escolha == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap}).iterrows():
                st.write(f"**{v['versiculo']}** {v['texto']}")

    # --- OUVIDORIA ---
    elif escolha == "📣 Ouvidoria":
        with st.form("ouv"):
            msg = st.text_area("Sua mensagem (Elogio ou Sugestão)")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO ouvidoria (data, mensagem, autor) VALUES (:d, :m, :a)", {"d": datetime.now().strftime("%d/%m/%Y"), "m": msg, "a": u['nome']})
                st.success("Enviado!")
