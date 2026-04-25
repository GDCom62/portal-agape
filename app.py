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
    .radio-btn-play { padding: 15px 35px; border-radius: 50px; border: none; background-color: #1e3a8a; color: white; cursor: pointer; font-weight: bold; margin-right: 10px; font-size: 16px; }
    .radio-btn-pause { padding: 15px 35px; border-radius: 50px; border: none; background-color: #f1f5f9; color: #1e3a8a; cursor: pointer; font-weight: bold; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v8.db", pool_pre_ping=True)

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
    executar_query('CREATE TABLE IF NOT EXISTS ouvidoria (id INTEGER PRIMARY KEY, data TEXT, mensagem TEXT, autor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
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

    # --- TRANSPARÊNCIA (PÚBLICA - SÓ CÓDIGOS) ---
    if escolha == "📊 Transparência":
        st.title("📊 Transparência Financeira")
        st.info("Os nomes dos membros são preservados. Identifique sua contribuição pelo seu código individual.")
        df_fin = consultar_db("SELECT data as Data, codigo_membro as 'Código Membro', valor as Valor, tipo as Tipo FROM financas ORDER BY id DESC")
        if not df_fin.empty:
            st.metric("Total Acumulado", f"R$ {df_fin['Valor'].sum():,.2f}")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
        else: st.info("Nenhum lançamento registrado até o momento.")

    # --- ADMIN (VISÃO GERAL COMPLETA) ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Administração")
        t1, t2, t3, t4, t5 = st.tabs(["💰 Lançar Finanças", "👥 Membros & Nomes", "📢 Mural", "📻 Rádio", "📖 Bíblia"])
        
        with t1: # Lançamento
            with st.form("fin"):
                c, v, t = st.text_input("Código do Membro (AG-XXXX)"), st.number_input("Valor", 0.0), st.selectbox("Tipo", ["Dízimo", "Oferta", "Doação"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d, :c, :v, :t)", {"d": datetime.now().strftime("%d/%m/%Y"), "c": c, "v": v, "t": t})
                    st.success("Lançado com sucesso!")

        with t2: # VISÃO GERAL SÓ ADMIN
            st.subheader("📋 Relação Nome x Código")
            st.write("Somente o administrador tem acesso a esta lista.")
            df_membros = consultar_db("SELECT nome as Nome, email as Email, codigo as Código, ativo as Ativo FROM membros WHERE is_admin=0 ORDER BY nome ASC")
            st.dataframe(df_membros, use_container_width=True, hide_index=True)
            
            # Exportação
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_membros.to_excel(wr, index=False)
            st.download_button("📥 Baixar Lista Mestra (Excel)", buf.getvalue(), "lista_mestra_agape.xlsx")

        with t3: # Mural
            with st.form("av"):
                ti, co, f = st.text_input("Título"), st.text_area("Mensagem"), st.file_uploader("Foto", type=['jpg', 'png'])
                if st.form_submit_button("Postar"):
                    img_b = f"data:image/png;base64,{base64.b64encode(f.getvalue()).decode()}" if f else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_url) VALUES (:t, :c, :d, :i)", {"t":ti, "c":co, "d":datetime.now().strftime("%d/%m/%Y %H:%M"), "i":img_b})
                    st.success("Postado!")

        with t4: # Rádio
            res_r = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
            novo_r = st.text_input("URL da Rádio:", value=res_r.iloc[0]['valor'] if not res_r.empty else "")
            if st.button("💾 Salvar Rádio"):
                executar_query("DELETE FROM configuracoes WHERE chave='radio_url'")
                executar_query("INSERT INTO configuracoes (chave, valor) VALUES ('radio_url', :v)", {"v": novo_r})
                st.success("Link atualizado!"); st.rerun()

        with t5: # Bíblia
            f_bib = st.file_uploader("Importar acf.json", type=['json'])
            if f_bib and st.button("🚀 Processar"):
                dados = json.load(f_bib)
                for idx, liv in enumerate(dados):
                    nm = liv.get('name') or liv.get('nome')
                    for ic, cl in enumerate(liv.get('chapters', [])):
                        for iv, tv in enumerate(cl):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l": str(nm), "c": ic+1, "v": iv+1, "t": str(tv)})
                st.success("Importado!")

    # --- PÁGINAS RESTANTES (Mural, Rádio, Live, Bíblia, Orações, Ouvidoria) ---
    elif escolha == "📢 Mural Ágape":
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f'<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p>"{p["versiculo"]}"</p><strong>— {p["referencia"]}</strong><br><br><div>{p["devocional"]}</div></div>', unsafe_allow_html=True)
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p><small>{r["data"]}</small></div>', unsafe_allow_html=True)

    elif escolha == "📻 Rádio Gospel":
        st.title("📻 Rádio Ágape Online")
        conf = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        url_radio = conf.iloc[0]['valor'] if not conf.empty else "https://zeno.fm"
        st.markdown(f"""<div style='background:white; padding:40px; border-radius:20px; text-align:center; border:1px solid #eee;'>
            <h2 style='color:#1e3a8a;'>Sintonizando a Benção</h2>
            <audio id="player"><source src="{url_radio}" type="audio/mpeg"></audio>
            <div><button class="radio-btn-play" onclick="document.getElementById('player').play()">▶️ OUVIR</button>
            <button class="radio-btn-pause" onclick="document.getElementById('player').pause()">⏸️ PARAR</button></div>
        </div>""", unsafe_allow_html=True)

    elif escolha == "📺 Ao Vivo":
        l_stat = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_ativa'")
        l_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
        if not l_stat.empty and l_stat.iloc[0]['valor'] == 'Sim':
            embed = l_url.iloc[0]['valor'].replace("watch?v=", "embed/")
            st.markdown(f'<iframe width="100%" height="500" src="{embed}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
            with st.form("chat"):
                mc = st.text_input("Mensagem")
                if st.form_submit_button("Enviar"):
                    executar_query("INSERT INTO chat_live (nome, mensagem, hora) VALUES (:n, :m, :h)", {"n": u['nome'], "m": mc, "h": datetime.now().strftime("%H:%M")})
                    st.rerun()
            for _, m in consultar_db("SELECT * FROM chat_live ORDER BY id DESC LIMIT 10").iterrows():
                st.markdown(f"**{m['nome']}**: {m['mensagem']}")
        else: st.info("Sem live ativa.")

    elif escolha == "📖 Bíblia":
        livros = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap}).iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")

    elif escolha == "🙏 Orações":
        with st.form("ora"):
            ped = st.text_area("Seu pedido")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data) VALUES (:n, :p, :d)", {"n": u['nome'], "p": ped, "d": datetime.now().strftime("%d/%m/%Y")})
                st.success("Registrado!")

    elif escolha == "📣 Ouvidoria":
        with st.form("ouv"):
            msg = st.text_area("Elogio ou Sugestão")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO ouvidoria (data, mensagem, autor) VALUES (:d, :m, :a)", {"d": datetime.now().strftime("%d/%m/%Y"), "m": msg, "a": u['nome']})
                st.success("Enviado!")
