import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

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
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    
    # Verificação de colunas para o Bate-papo
    try: consultar_db("SELECT para_user FROM mensagens LIMIT 1")
    except:
        executar_query('DROP TABLE IF EXISTS mensagens')
        executar_query('CREATE TABLE mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    # [Seu bloco de login aqui...]
    st.title("⛪ Portal Ágape")
    with st.form("login"):
        e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
            if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                st.rerun()
else:
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        tam_fonte = st.select_slider("Tamanho Letra", options=range(18, 40, 2), value=24) if menu in ["📢 Mural", "📖 Bíblia"] else 18
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    # --- MENU: BATE-PAPO ---
    if menu == "🎥 Bate-papo":
        st.title("💬 Bate-papo & Reunião")
        
        # COLUNA LATERAL DE CONTATOS
        col_contatos, col_conversa = st.columns([0.3, 0.7])
        
        with col_contatos:
            st.subheader("👥 Enviar para:")
            lista_membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n": u['nome']})
            destinatario = st.radio("Selecione o contato:", ["Todos (Grupo)"] + list(lista_membros['nome']))
        
        with col_conversa:
            st.info(f"Conversando com: **{destinatario}**")
            
            # EXIBIÇÃO DE MENSAGENS (Filtro para Privado ou Público)
            chat_box = st.container(height=400)
            if destinatario == "Todos (Grupo)":
                msgs = consultar_db("SELECT * FROM mensagens WHERE para_user = 'Todos (Grupo)' ORDER BY id ASC")
            else:
                msgs = consultar_db("SELECT * FROM mensagens WHERE (de_user=:u AND para_user=:d) OR (de_user=:d AND para_user=:u) ORDER BY id ASC", {"u": u['nome'], "d": destinatario})

            with chat_box:
                for _, r in msgs.iterrows():
                    eu = r['de_user'] == u['nome']
                    align, cor = ("flex-end", "#dcf8c6") if eu else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div style="background:{cor}; padding:10px; border-radius:10px; margin-bottom:5px; max-width:80%; border:1px solid #ddd;"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
                    if r['anexo_data']: st.download_button(label=f"📁 Baixar {r['anexo_nome']}", data=base64.b64decode(r['anexo_data']), file_name=r['anexo_nome'], key=f"c_{r['id']}")

            # ÁREA DE ENVIO E VÍDEO
            with st.form("envio_final", clear_on_submit=True):
                msg_txt = st.text_area("Digite sua mensagem...")
                c1, c2 = st.columns([0.6, 0.4])
                arquivo = c1.file_uploader("Anexar Arquivo", type=['pdf','jpg','png','docx'])
                
                # LINK DE VÍDEO CONFIGURADO (Sala única para o portal)
                sala_video = "AgapePortal_Geral" if destinatario == "Todos (Grupo)" else f"Agape_{min(u['nome'], destinatario)}_{max(u['nome'], destinatario)}"
                c2.markdown(f'<br><a href="https://jit.si{sala_video}" target="_blank"><div style="background:#1e3a8a; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold; cursor:pointer;">🎥 Iniciar Chamada Vídeo</div></a>', unsafe_allow_html=True)
                
                if st.form_submit_button("Enviar Mensagem"):
                    b64, n_arq = "", ""
                    if arquivo:
                        n_arq = arquivo.name
                        b64 = base64.b64encode(arquivo.read()).decode()
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_nome, anexo_data, data) VALUES (:d, :p, :t, :an, :ad, :dt)",
                                  {"d": u['nome'], "p": destinatario, "t": msg_txt, "an": n_arq, "ad": b64, "dt": datetime.now().strftime("%H:%M")})
                    st.rerun()

    # --- OUTROS MENUS (Mural, Bíblia, Financeiro) ---
    # [Mantenha os blocos conforme os envios anteriores...]
