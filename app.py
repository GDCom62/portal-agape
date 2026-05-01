import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide")
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

# --- INICIALIZAÇÃO DB ---
executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, nome TEXT, texto TEXT, video_url TEXT, data TEXT)')
executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
executar_query('CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)')

# --- LOGIN (Simplificado para o exemplo rodar) ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    # ... (Mantenha seu código de login aqui)
    st.title("⛪ Portal Ágape - Login")
    if st.button("Simular Login Admin"): 
        st.session_state.logado = True
        st.session_state.user = {"nome": "Admin", "codigo": "ADM-001", "is_admin": 1}
        st.rerun()
else:
    u = st.session_state.user
    menu = st.sidebar.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False

    # --- LÓGICA DE ADMIN (CARGA BÍBLIA) ---
    if admin_mode:
        t1, t2 = st.tabs(["📖 Carga Bíblia", "💬 Gestão Chat"])
        with t1:
            st.subheader("Importar Bíblia (CSV)")
            arquivo = st.file_opener = st.file_uploader("Arraste o CSV da Bíblia aqui", type="csv")
            if arquivo:
                df_biblia = pd.read_csv(arquivo)
                df_biblia.to_sql('biblia', engine, if_exists='append', index=False)
                st.success("Bíblia carregada com sucesso!")

    # --- BATE-PAPO COM VÍDEO ---
    elif menu == "🎥 Bate-papo":
        st.title("🎥 Bate-papo & Vídeos")
        
        # Lista de membros online (Simulação/Seleção)
        col_membros, col_chat = st.columns([1, 3])
        
        with col_membros:
            st.markdown("### 🟢 Online")
            membros = consultar_db("SELECT nome FROM membros")
            for m in membros['nome']:
                if st.button(f"💬 {m}", key=m): st.session_state.destino = m

        with col_chat:
            dest = st.session_state.get('destino', 'Todos')
            st.info(f"Enviando para: **{dest}**")
            
            chat_container = st.container(height=400)
            df_msg = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
            
            with chat_container:
                for _, row in df_msg.iterrows():
                    is_me = row['nome'] == u['nome']
                    color = "#dcf8c6" if is_me else "#ffffff"
                    st.markdown(f'<div style="background:{color}; padding:10px; border-radius:10px; margin-bottom:5px;"><b>{row["nome"]}:</b> {row["texto"]}</div>', unsafe_allow_html=True)
                    if row['video_url']:
                        st.video(row['video_url'])

            with st.form("chat_form", clear_on_submit=True):
                txt = st.text_input("Sua mensagem")
                vid = st.text_input("Link do Vídeo (YouTube/Vimeo) - Opcional")
                if st.form_submit_button("Enviar"):
                    executar_query("INSERT INTO mensagens (nome, texto, video_url, data) VALUES (:n, :t, :v, :d)",
                                  {"n": u['nome'], "t": txt, "v": vid, "d": datetime.now().strftime("%H:%M")})
                    st.rerun()

    # --- BÍBLIA (LEITURA) ---
    elif menu == "📖 Bíblia":
        st.title("📖 Sagrada Escritura")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            livro_sel = st.selectbox("Selecione o Livro", livros['livro'])
            capitulos = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro = :l", {"l": livro_sel})
            cap_sel = st.selectbox("Capítulo", capitulos['cap'])
            versiculos = consultar_db("SELECT ver, texto FROM biblia WHERE livro = :l AND cap = :c", {"l": livro_sel, "c": cap_sel})
            for _, v in versiculos.iterrows():
                st.write(f"**{v['ver']}** {v['texto']}")
        else:
            st.warning("Bíblia ainda não carregada. Vá ao Modo Admin para importar.")
