import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io, re

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    
    # Criar Admin Padrão
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("⛪ Portal Ágape - Bem-vindo")
    t1, t2 = st.tabs(["🔐 Login", "📝 Cadastro"])
    with t1:
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Dados incorretos.")
else:
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # CSS Estilos
    st.markdown(f"""<style>
        .stApp {{ background-color: #f8fafc; }}
        .card-mural {{ background: white; padding: 20px; border-radius: 15px; border-left: 10px solid #1e3a8a; margin-bottom: 20px; color: black; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .caixa-leitura {{ background: white; padding: 20px; border-radius: 10px; border: 1px solid #1e3a8a; color: black; font-size: 22px; }}
    </style>""", unsafe_allow_html=True)

    if admin_mode:
        st.title("⚙️ Administração")
        tab_m, tab_f = st.tabs(["📢 Mural", "💰 Financeiro"])
        
        with tab_m:
            st.subheader("Publicar ou Editar Mural")
            avisos_existentes = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            opcao = st.selectbox("Ação", ["Novo Aviso"] + [f"Editar: {row['titulo']}" for _, row in avisos_existentes.iterrows()])
            
            with st.form("form_mural", clear_on_submit=True):
                if "Editar" in opcao:
                    id_edit = int(re.search(r'Editar: (.*)', opcao).group(1) != None) # Simplificado para o exemplo
                    row_edit = avisos_existentes[avisos_existentes['titulo'] == opcao.split(": ")[1]].iloc[0]
                    tit = st.text_input("Título", value=row_edit['titulo'])
                    cont = st.text_area("Conteúdo", value=row_edit['conteudo'])
                else:
                    tit = st.text_input("Título")
                    cont = st.text_area("Conteúdo")
                
                foto = st.file_uploader("Upload de Foto", type=['jpg','png','jpeg'])
                
                if st.form_submit_button("Salvar no Mural"):
                    img_b64 = base64.b64encode(foto.read()).decode() if foto else ""
                    if "Editar" in opcao:
                        executar_query("UPDATE avisos SET titulo=:t, conteudo=:c, img_data=:i WHERE id=:id", {"t":tit, "c":cont, "i":img_b64, "id":row_edit['id']})
                    else:
                        executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t, :c, :i, :d)", {"t":tit, "c":cont, "i":img_b64, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()

            st.divider()
            st.subheader("Excluir Avisos")
            for _, r in avisos_existentes.iterrows():
                if st.button(f"🗑️ Apagar Aviso: {r['titulo']}", key=f"del_{r['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":r['id']}); st.rerun()

        with tab_f:
            st.subheader("Lançamentos Financeiros")
            with st.form("form_fin"):
                desc = st.text_input("Descrição")
                valor = st.number_input("Valor R$", min_value=0.0)
                tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d, :v, :t, :dt)", {"d":desc, "v":valor, "t":tipo, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.rerun()
            
            st.divider()
            df_fin = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
            for _, r in df_fin.iterrows():
                c1, c2 = st.columns([0.8, 0.2])
                c1.write(f"**{r['descricao']}** | R$ {r['valor']:.2f} ({r['tipo']})")
                if c2.button("Apagar", key=f"dfin_{r['id']}"):
                    executar_query("DELETE FROM financeiro WHERE id=:id", {"id": r['id']})
                    st.rerun()

    elif menu == "📢 Mural":
        st.title("📢 Mural de Avisos")
        # Palavra do dia automática
        p = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
        if not p.empty:
            st.info(f"📖 **Palavra do Dia:** \"{p.iloc[0]['texto']}\" ({p.iloc[0]['livro']} {p.iloc[0]['cap']}:{p.iloc[0]['ver']})")
        
        for _, row in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            st.markdown(f'<div class="card-mural"><h4>{row["titulo"]}</h4><p>{row["conteudo"]}</p><small>{row["data"]}</small></div>', unsafe_allow_html=True)
            if row['img_data']:
                st.image(base64.b64decode(row['img_data']), width=400)

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            e = df[df['tipo']=='Entrada']['valor'].sum()
            s = df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo Geral", f"R$ {e-s:,.2f}", delta=e-s)
            st.dataframe(df, use_container_width=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia")
        l_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not l_db.empty:
            l_s = st.selectbox("Livro", l_db['livro'])
            c_s = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_s})['cap'])
            txts = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_s, "c":c_s})
            txt_html = "".join([f"<p><b>{v['ver']}</b> {v['texto']}</p>" for _, v in txts.iterrows()])
            st.markdown(f'<div class="caixa-leitura">{txt_html}</div>', unsafe_allow_html=True)

    elif menu == "🎥 Bate-papo":
        st.title("🎥 Bate-papo")
        st.link_button("🎥 Abrir Chamada de Vídeo (Jitsi)", "https://jit.si", use_container_width=True)
        # Código de chat simplificado conforme conversas anteriores
