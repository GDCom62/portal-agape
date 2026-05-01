import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# Estilos CSS
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .card-flutuante { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #1e3a8a; }
    .chat-bubble { padding: 12px; border-radius: 15px; margin-bottom: 10px; max-width: 85%; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, video_url TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)')

init_db()

# --- 3. LOGICA DE LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    # (Mantenha aqui seu bloco de formulário de login original)
    st.title("⛪ Portal Ágape")
    with st.form("login"):
        e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
            if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                st.rerun()
            else: st.error("Erro no login")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 🙏 Olá, {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    # --- ADMINISTRAÇÃO ---
    if admin_mode:
        st.title("⚙️ Painel Administrativo")
        t1, t2, t3 = st.tabs(["📢 Mural", "💰 Finanças", "📖 Bíblia"])
        with t1:
            with st.form("mural_admin"):
                tit = st.text_input("Título do Aviso")
                cont = st.text_area("Conteúdo")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", {"t":tit, "c":cont, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")
        with t2:
            st.write("Lançamentos Financeiros")
            # Adicione aqui seu formulário de lançamentos financeiro
        with t3:
            st.write("Configurar Bíblia / Palavra do dia")

    # --- MENU: MURAL ---
    elif menu == "📢 Mural":
        st.title("📢 Mural de Avisos")
        palavra = consultar_db("SELECT valor FROM configuracoes WHERE chave='palavra_dia'")
        if not palavra.empty: st.info(f"📖 **Palavra do Dia:** {palavra.iloc[0]['valor']}")
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-flutuante"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)

    # --- MENU: FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            ent = df[df['tipo']=='Entrada']['valor'].sum()
            sai = df[df['tipo']=='Saída']['valor'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", f"R$ {ent:,.2f}")
            c2.metric("Saídas", f"R$ {sai:,.2f}")
            c3.metric("Saldo", f"R$ {ent-sai:,.2f}")
            st.dataframe(df, use_container_width=True)
        else: st.info("Sem registros.")

    # --- MENU: BATE-PAPO ---
    elif menu == "🎥 Bate-papo":
        st.title("🎥 Bate-papo Interno")
        
        col_membros, col_conversa = st.columns([1, 3])
        
        with col_membros:
            st.subheader("👥 Contatos")
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n": u['nome']})
            contato_sel = st.selectbox("Enviar para:", ["Todos"] + list(membros['nome']))
        
        with col_conversa:
            chat_area = st.container(height=400)
            # Filtra mensagens (Gerais ou Privadas entre os dois)
            df_msg = consultar_db("SELECT * FROM mensagens WHERE para_user = 'Todos' OR (de_user = :u AND para_user = :c) OR (de_user = :c AND para_user = :u)", 
                                 {"u": u['nome'], "c": contato_sel})
            
            with chat_area:
                for _, row in df_msg.iterrows():
                    is_me = row['de_user'] == u['nome']
                    align, color = ("flex-end", "#dcf8c6") if is_me else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display: flex; flex-direction: column; align-items: {align};"><div class="chat-bubble" style="background-color: {color};"><b>{row["de_user"]}</b><br>{row["texto"]}<br><small style="color:gray">{row["data"]}</small></div></div>', unsafe_allow_html=True)
                    if row['video_url']: st.video(row['video_url'])

            with st.form("msg_form", clear_on_submit=True):
                txt = st.text_input("Mensagem para " + contato_sel)
                vid = st.text_input("Link de Vídeo (Opcional)")
                if st.form_submit_button("Enviar") and txt:
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, video_url, data) VALUES (:d, :p, :t, :v, :dt)",
                                  {"d": u['nome'], "p": contato_sel, "t": txt, "v": vid, "dt": datetime.now().strftime("%H:%M")})
                    st.rerun()
