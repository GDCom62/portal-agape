import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json

# Tenta importar a câmera (WebRTC)
try:
    from streamlit_webrtc import webrtc_streamer
    HAS_WEBRTC = True
except ImportError:
    HAS_WEBRTC = False

# --- 1. CONFIGURAÇÕES E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .card-flutuante {
        background: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 5px solid #1e3a8a;
    }
    .chat-bubble {
        padding: 10px; border-radius: 15px; margin-bottom: 10px; max-width: 80%;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
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
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def logo_central(largura):
    if os.path.exists(URL_LOGO):
        with open(URL_LOGO, "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        logo_central(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad", clear_on_submit=True):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta", use_container_width=True):
                    if n and em and se:
                        c = "AG-" + "".join(random.choices(string.digits, k=4))
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                        st.success(f"Conta criada! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        logo_central(100)
        st.markdown(f"<p style='text-align: center;'>🙏 <b>{u['nome']}</b><br><small>Cód: {u['codigo']}</small></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Administração")
        tab1, tab2, tab3 = st.tabs(["📢 Mural & ACF", "💰 Finanças", "💬 Chat"])
        
        with tab1:
            st.subheader("Palavra do Dia / Bíblia")
            txt_biblia = st.text_area("Texto Bíblico ou JSON ACF")
            if st.button("Salvar Palavra"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('palavra_dia', :v)", {"v": txt_biblia})
                st.success("Salvo!")
            
            st.divider()
            with st.form("novo_aviso"):
                t, c = st.text_input("Título Aviso"), st.text_area("Conteúdo")
                if st.form_submit_button("Publicar Mural"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":t,"c":c,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()

        with tab2:
            with st.form("fin_admin"):
                c1, c2 = st.columns(2)
                cod_m = c1.text_input("Cód. Membro (ou IGREJA)")
                val_m = c2.number_input("Valor", min_value=0.0)
                tipo_m = st.selectbox("Tipo", ["Entrada", "Saída"])
                desc_m = st.text_input("Descrição")
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (codigo_doador, descricao, valor, tipo, data) VALUES (:c,:d,:v,:t,:dt)", 
                                  {"c":cod_m, "d":desc_m, "v":val_m, "t":tipo_m, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.success("Lançado!")

        with tab3:
            if st.button("Limpar Histórico de Mensagens"):
                executar_query("DELETE FROM mensagens")
                st.rerun()

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural de Avisos")
            p = consultar_db("SELECT valor FROM configuracoes WHERE chave='palavra_dia'")
            if not p.empty: st.info(f"📖 **Palavra do Dia:** {p.iloc[0]['valor']}")
            
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, av in avisos.iterrows():
                st.markdown(f'<div class="card-flutuante"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)

        elif menu == "🎥 Bate-papo":
            st.title("🎥 Bate-papo & Vídeo")
            aba_c, aba_v = st.tabs(["💬 Mensagens", "📷 Câmera"])
            
            with aba_c:
                c_lista, c_msg = st.columns([0.3, 0.7])
                with c_lista:
                    st.write("👥 Contatos")
                    membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n":u['nome']})
                    contato = st.selectbox("Falar com:", ["Todos"] + list(membros['nome']))
                
                with c_msg:
                    area = st.container(height=350)
                    msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
                    with area:
                        for _, row in msgs.iterrows():
                            is_me = row['de_user'] == u['nome']
                            align, color = ("flex-end", "#dcf8c6") if is_me else ("flex-start", "#ffffff")
                            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: {align};"><div class="chat-bubble" style="background-color: {color};"><b>{row["de_user"]}</b><br>{row["texto"]}<br><small style="color:gray">{row["data"]}</small></div></div>', unsafe_allow_html=True)
                    
                    with st.form("envia", clear_on_submit=True):
                        t_msg = st.text_input("Mensagem")
                        if st.form_submit_button("Enviar") and t_msg:
                            executar_query("INSERT INTO mensagens (de_user, para_user, texto, data) VALUES (:d,:p,:t,:dt)", 
                                          {"d":u['nome'], "p":contato, "t":t_msg, "dt":datetime.now().strftime("%H:%M")})
                            st.rerun()

            with aba_v:
                if HAS_WEBRTC:
                    webrtc_streamer(key="camera-agape")
                else:
                    st.error("Módulo de câmera não carregado. Verifique o requirements.txt")

        elif menu == "💰 Financeiro":
            st.title("💰 Meu Financeiro")
            df = consultar_db("SELECT * FROM financeiro")
            if not df.empty:
                ent = df[df['tipo']=='Entrada']['valor'].sum()
                sai = df[df['tipo']=='Saída']['valor'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Entradas", f"R$ {ent:,.2f}")
                c2.metric("Saídas", f"R$ {sai:,.2f}")
                c3.metric("Saldo", f"R$ {ent-sai:,.2f}")
                st.divider()
                st.dataframe(df, use_container_width=True)
            else: st.info("Nenhum registro.")

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia")
            st.write("Selecione o Livro e Capítulo (Importe o JSON no modo Admin)")
