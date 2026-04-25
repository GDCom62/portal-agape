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
    .palavra-dia-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white !important; padding: 30px; border-radius: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); margin-bottom: 30px; text-align: center;
    }
    .palavra-dia-card h2, .palavra-dia-card p { color: white !important; }
    .mural-card {
        background-color: white; padding: 25px; border-radius: 15px;
        border-top: 5px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    .aviso-img { width: 100%; max-height: 500px; object-fit: contain; border-radius: 10px; margin-bottom: 15px; }
    .live-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 15px; box-shadow: 0 10px 15px rgba(0,0,0,0.2); }
    .live-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
    .chat-msg { background: white; padding: 10px; border-radius: 10px; margin-bottom: 5px; border-left: 3px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v6.db", pool_pre_ping=True)

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
    executar_query('CREATE TABLE IF NOT EXISTS chat_live (id INTEGER PRIMARY KEY, nome TEXT, mensagem TEXT, hora TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN / SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.markdown("<h1 style='text-align: center;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
        t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_log:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data}); st.rerun()
                    st.error("Dados incorretos.")
        with t_cad:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                   {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastro realizado! Código: {c}")
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    opcoes = ["📢 Mural Ágape", "📺 Ao Vivo", "📖 Ler a Bíblia", "🙏 Pedidos de Oração"]
    if u['is_admin'] == 1: opcoes.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", opcoes)
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- AO VIVO ---
    if escolha == "📺 Ao Vivo":
        st.markdown("<h1>📺 Transmissão ao Vivo</h1>", unsafe_allow_html=True)
        live_status = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_ativa'")
        live_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
        if not live_status.empty and live_status.iloc[0]['valor'] == 'Sim':
            url = live_url.iloc[0]['valor'].replace("watch?v=", "embed/")
            st.markdown(f'<div class="live-container"><iframe src="{url}" allowfullscreen></iframe></div>', unsafe_allow_html=True)
            st.divider()
            st.subheader("💬 Interação da Comunidade")
            with st.form("chat_form", clear_on_submit=True):
                msg = st.text_input("Deixe sua mensagem...")
                if st.form_submit_button("Enviar"):
                    if msg:
                        executar_query("INSERT INTO chat_live (nome, mensagem, hora) VALUES (:n, :m, :h)",
                                       {"n": u['nome'], "m": msg, "h": datetime.now().strftime("%H:%M")})
                        st.rerun()
            mensagens = consultar_db("SELECT * FROM chat_live ORDER BY id DESC LIMIT 15")
            for _, m in mensagens.iterrows():
                st.markdown(f"<div class='chat-msg'><b>{m['nome']}</b> <small>{m['hora']}</small><br>{m['mensagem']}</div>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma transmissão ativa.")

    # --- MURAL ---
    elif escolha == "📢 Mural Ágape":
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f"""<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p style='font-size: 1.4em; font-style: italic;'>"{p['versiculo']}"</p><strong>— {p['referencia']}</strong><div style='margin-top:20px;'>{p['devocional']}</div></div>""", unsafe_allow_html=True)

        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img_tag = f'<img src="{r["img_url"]}" class="aviso-img">' if r.get("img_url") else ""
            st.markdown(f"""<div class="mural-card">{img_tag}<h3>{r['titulo']}</h3><p style="color: #475569;">{r['conteudo']}</p><small>📅 {r['data']}</small></div>""", unsafe_allow_html=True)

    # --- BÍBLIA ---
    elif escolha == "📖 Ler a Bíblia":
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros_df.empty:
            c1, c2 = st.columns(2)
            l_sel = c1.selectbox("Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l_sel})
            c_sel = c2.selectbox("Capítulo", caps_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l_sel, "c": c_sel})
            st.markdown(f"### {l_sel} - Capítulo {c_sel}")
            for _, v in versos.iterrows():
                st.markdown(f"<div style='background:white; padding:10px; border-radius:8px; margin-bottom:5px;'><b>{v['versiculo']}</b> {v['texto']}</div>", unsafe_allow_html=True)

    # --- ORAÇÃO ---
    elif escolha == "🙏 Pedidos de Oração":
        st.header("🙏 Espaço de Intercessão")
        with st.form("ora_f", clear_on_submit=True):
            ped = st.text_area("Escreva seu pedido:")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data) VALUES (:n, :p, :d)", {"n": u['nome'], "p": ped, "d": datetime.now().strftime("%d/%m/%Y %H:%M")})
                st.success("Pedido enviado!")

    # --- ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Painel Gestor")
        t1, t2, t3, t4, t5 = st.tabs(["✨ Palavra do Dia", "📢 Mural", "🔴 Live", "👥 Membros", "🙏 Orações"])
        
        with t1:
            with st.form("f_pd"):
                v, r, d = st.text_area("Versículo"), st.text_input("Referência"), st.text_area("Devocional")
                if st.form_submit_button("Atualizar"):
                    executar_query("INSERT INTO palavra_dia (versiculo, referencia, devocional) VALUES (:v, :r, :d)", {"v":v, "r":r, "d":d})
                    st.success("Atualizado!")

        with t2:
            st.subheader("📢 Novo Comunicado com Foto")
            with st.form("av_admin", clear_on_submit=True):
                tit = st.text_input("Título do Aviso")
                cont = st.text_area("Mensagem detalhada")
                foto_arquivo = st.file_uploader("Selecione uma foto (PNG, JPG)", type=['png', 'jpg', 'jpeg'])
                if st.form_submit_button("Postar Aviso"):
                    if tit and cont:
                        img_str = ""
                        if foto_arquivo:
                            img_str = f"data:image/jpeg;base64,{base64.b64encode(foto_arquivo.getvalue()).decode()}"
                        executar_query("INSERT INTO avisos (titulo, conteudo, data, img_url) VALUES (:t, :c, :d, :i)", 
                                       {"t": tit, "c": cont, "d": datetime.now().strftime("%d/%m/%Y %H:%M"), "i": img_str})
                        st.success("✅ Postado!")
                        st.rerun()

        with t3:
            with st.form("live_admin"):
                ativa = st.selectbox("Ativar Live?", ["Não", "Sim"])
                link = st.text_input("Link YouTube")
                if st.form_submit_button("Salvar"):
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_ativa', :v)", {"v": ativa})
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :u)", {"u": link})
                    st.success("Salvo!")
            if st.button("🗑️ Limpar Chat"):
                executar_query("DELETE FROM chat_live"); st.rerun()

        with t4:
            st.dataframe(consultar_db("SELECT nome, email, codigo FROM membros"), use_container_width=True)

        with t5:
            ordata = consultar_db("SELECT * FROM oracoes WHERE status='Pendente'")
            for _, o in ordata.iterrows():
                st.write(f"**{o['nome_membro']}**: {o['pedido']}")
                if st.button("Marcar Orado", key=o['id']):
                    executar_query("UPDATE oracoes SET status='Atendido' WHERE id=:id", {"id": o['id']}); st.rerun()
