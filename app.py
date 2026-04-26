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
    .palavra-dia-card h2, .palavra-dia-card p, .palavra-dia-card div { color: white !important; }
    .aviso-img { width: 100%; max-height: 500px; object-fit: contain; border-radius: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v8.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params=params)
        return df

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, referencia TEXT, devocional TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT DEFAULT "Pendente")')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY, data TEXT, codigo_membro TEXT, valor REAL, tipo TEXT)')
    
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
        t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_log:
            with st.form("login"):
                e = st.text_input("E-mail")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict() # Proteção contra AttributeError
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("Dados incorretos.")
        with t_cad:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastrado! Código: {c}")
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    menu = ["📢 Mural Ágape", "📊 Transparência", "📜 Meu Extrato", "📻 Rádio Gospel", "📖 Bíblia"]
    if u['is_admin'] == 1: menu.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", menu)
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- 📊 TRANSPARÊNCIA ---
    if escolha == "📊 Transparência":
        st.title("📊 Prestação de Contas")
        df_fin = consultar_db("SELECT valor FROM financas")
        saldo = df_fin['valor'].sum() if not df_fin.empty else 0.0
        
        meta_n = consultar_db("SELECT valor FROM configuracoes WHERE chave='meta_nome'")
        meta_v = consultar_db("SELECT valor FROM configuracoes WHERE chave='meta_valor'")
        
        if not meta_n.empty and not meta_v.empty:
            v_meta = float(meta_v.iloc[0]['valor'])
            if v_meta > 0:
                st.subheader(f"🎯 Meta: {meta_n.iloc[0]['valor']}")
                st.progress(min(saldo/v_meta, 1.0))
                st.write(f"R$ {saldo:,.2f} de R$ {v_meta:,.2f}")

        st.metric("Saldo Líquido em Caixa", f"R$ {saldo:,.2f}")
        df_l = consultar_db("SELECT data, codigo_membro, valor, tipo FROM financas ORDER BY id DESC")
        st.dataframe(df_l, use_container_width=True, hide_index=True)

    # --- 📜 MEU EXTRATO ---
    elif escolha == "📜 Meu Extrato":
        st.title("📜 Meu Histórico")
        df_p = consultar_db("SELECT data, valor, tipo FROM financas WHERE codigo_membro=:c ORDER BY id DESC", {"c": u['codigo']})
        if not df_p.empty:
            st.metric("Meu Total", f"R$ {df_p['valor'].sum():,.2f}")
            st.dataframe(df_p, use_container_width=True)
        else: st.warning("Nenhum registro para o seu código.")

    # --- ⚙️ ADMIN ---
    elif escolha == "⚙️ Admin":
        t1, t2, t3 = st.tabs(["💰 Lançar", "🎯 Meta", "📢 Mural"])
        with t1:
            mems = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0")
            with st.form("f_adm"):
                n_sel = st.selectbox("Membro", mems['nome'].tolist()) if not mems.empty else ""
                v_sel = st.number_input("Valor", 0.0)
                t_sel = st.selectbox("Tipo", ["Dízimo", "Oferta", "Despesa"])
                if st.form_submit_button("Gravar"):
                    c_sel = mems[mems['nome'] == n_sel]['codigo'].values[0]
                    v_f = v_sel if t_sel != "Despesa" else -v_sel
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d,:c,:v,:t)", 
                                   {"d": datetime.now().strftime("%d/%m/%Y"), "c": c_sel, "v": v_f, "t": t_sel})
                    st.success("OK!")
        with t2:
            n_m = st.text_input("Objetivo")
            v_m = st.number_input("Alvo", 0.0)
            if st.button("Definir Meta"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('meta_nome', :v)", {"v": n_m})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('meta_valor', :v)", {"v": str(v_m)})
                st.success("Meta atualizada!")

    # --- 📢 MURAL ---
    elif escolha == "📢 Mural Ágape":
        pd_df = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_df.empty:
            p = pd_df.iloc[0]
            st.markdown(f'<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p>"{p["versiculo"]}"</p><strong>— {p["referencia"]}</strong><br><br>{p["devocional"]}</div>', unsafe_allow_html=True)
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in avisos.iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    # --- RÁDIO ---
    elif escolha == "📻 Rádio Gospel":
        conf = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        url = conf.iloc[0]['valor'] if not conf.empty else "https://zeno.fm"
        st.audio(url)

    # --- BÍBLIA ---
    elif escolha == "📖 Bíblia":
        livs = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livs.empty:
            l = st.selectbox("Livro", livs['livro'].tolist())
            cap_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})
            cap = st.selectbox("Capítulo", cap_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap})
            for _, v in versos.iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")
