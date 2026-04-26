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
    with engine.begin() as conn: conn.execute(text(sql), params)

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
                        u_data = res.iloc[0].to_dict()
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
    
    opcoes = ["📢 Mural Ágape", "📊 Transparência", "📜 Meu Extrato", "📻 Rádio Gospel", "📖 Bíblia", "🙏 Orações"]
    if u['is_admin'] == 1: opcoes.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", opcoes)
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- 📊 TRANSPARÊNCIA COM META ---
    if escolha == "📊 Transparência":
        st.title("📊 Transparência Financeira")
        df_fin = consultar_db("SELECT valor FROM financas")
        saldo_total = df_fin['valor'].sum() if not df_fin.empty else 0.0
        
        meta_n = consultar_db("SELECT valor FROM configuracoes WHERE chave='meta_nome'")
        meta_v = consultar_db("SELECT valor FROM configuracoes WHERE chave='meta_valor'")
        
        if not meta_n.empty and not meta_v.empty:
            valor_m = float(meta_v.iloc[0]['valor'])
            if valor_m > 0:
                st.subheader(f"🎯 Meta: {meta_n.iloc[0]['valor']}")
                progresso = min(saldo_total / valor_m, 1.0)
                st.progress(progresso)
                st.write(f"R$ {saldo_total:,.2f} de R$ {valor_m:,.2f} ({progresso*100:.1f}%)")
        
        st.metric("Saldo em Caixa", f"R$ {saldo_total:,.2f}")
        df_lista = consultar_db("SELECT data, codigo_membro, valor, tipo FROM financas ORDER BY id DESC")
        st.dataframe(df_lista, use_container_width=True, hide_index=True)

    # --- 📜 MEU EXTRATO (NOVO) ---
    elif escolha == "📜 Meu Extrato":
        st.title("📜 Meu Histórico de Contribuições")
        cod_user = u['codigo']
        st.info(f"Exibindo dados para o código: **{cod_user}**")
        
        df_pessoal = consultar_db("SELECT data, valor, tipo FROM financas WHERE codigo_membro=:c ORDER BY id DESC", {"c": cod_user})
        
        if not df_pessoal.empty:
            st.metric("Meu Total Contribuído", f"R$ {df_pessoal['valor'].sum():,.2f}")
            st.dataframe(df_pessoal, use_container_width=True, hide_index=True)
            
            # Download do Extrato
            towrap = io.BytesIO()
            with pd.ExcelWriter(towrap, engine='xlsxwriter') as wr: df_pessoal.to_excel(wr, index=False)
            st.download_button("📥 Baixar Meu Extrato (Excel)", towrap.getvalue(), f"extrato_{cod_user}.xlsx")
        else:
            st.warning("Nenhum registro encontrado para o seu código.")

    # --- ⚙️ ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Administração")
        t1, t2, t3 = st.tabs(["💰 Lançamentos", "🎯 Gestão de Meta", "📢 Mural"])
        with t1:
            mems = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0 ORDER BY nome ASC")
            with st.form("f_fin", clear_on_submit=True):
                n_sel = st.selectbox("Escolha o Irmão(ã)", mems['nome'].tolist()) if not mems.empty else "Nenhum"
                val = st.number_input("Valor", 0.0)
                tipo = st.selectbox("Categoria", ["Dízimo", "Oferta", "Doação Meta", "Despesa"])
                if st.form_submit_button("Gravar"):
                    cod = mems[mems['nome'] == n_sel]['codigo'].values[0]
                    v_f = val if tipo != "Despesa" else -val
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d,:c,:v,:t)",
                                   {"d": datetime.now().strftime("%d/%m/%Y"), "c": cod, "v": v_f, "t": tipo})
                    st.success("Lançamento realizado!")

        with t2:
            st.subheader("Configurar Meta")
            n_m = st.text_input("Objetivo")
            v_m = st.number_input("Valor Alvo", 0.0)
            if st.button("Definir Meta"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('meta_nome', :v)", {"v": n_m})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('meta_valor', :v)", {"v": str(v_m)})
                st.success("Meta atualizada!")

    # --- MURAL ---
    elif escolha == "📢 Mural Ágape":
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f'<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p>"{p["versiculo"]}"</p><strong>— {p["referencia"]}</strong><br><br>{p["devocional"]}</div>', unsafe_allow_html=True)
        
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if not df_a.empty:
            for _, r in df_a.iterrows():
                img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
                st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    # --- RÁDIO / BÍBLIA ---
    elif escolha == "📻 Rádio Gospel":
        conf = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        url = conf.iloc[0]['valor'] if not conf.empty else "https://zeno.fm"
        st.audio(url)

    elif escolha == "📖 Bíblia":
        livs = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livs.empty:
            l = st.selectbox("Livro", livs['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap}).iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")
