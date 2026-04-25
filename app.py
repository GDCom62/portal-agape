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

    # --- 📊 TRANSPARÊNCIA COM META ---
    if escolha == "📊 Transparência":
        st.title("📊 Prestação de Contas")
        
        # Meta de Arrecadação
        meta_nome = consultar_db("SELECT valor FROM configuracoes WHERE chave='meta_nome'")
        meta_valor = consultar_db("SELECT valor FROM configuracoes WHERE chave='meta_valor'")
        
        df_fin = consultar_db("SELECT valor FROM financas")
        saldo_atual = df_fin['valor'].sum() if not df_fin.empty else 0.0

        if not meta_nome.empty and not meta_valor.empty:
            nome_m = meta_nome.iloc[0]['valor']
            valor_m = float(meta_valor.iloc[0]['valor'])
            if valor_m > 0:
                st.subheader(f"🎯 Meta Atual: {nome_m}")
                progresso = min(saldo_atual / valor_m, 1.0)
                st.progress(progresso)
                st.write(f"Arrecadado: R$ {saldo_atual:,.2f} de R$ {valor_m:,.2f} ({progresso*100:.1f}%)")
        
        st.divider()
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Saldo Total em Caixa", f"R$ {saldo_atual:,.2f}")
        
        df_lista = consultar_db("SELECT data as Data, codigo_membro as Identificador, valor as Valor, tipo as Categoria FROM financas ORDER BY id DESC")
        if not df_lista.empty:
            receitas = df_lista[df_lista['Valor'] > 0]['Valor'].sum()
            despesas = abs(df_lista[df_lista['Valor'] < 0]['Valor'].sum())
            st.bar_chart(pd.DataFrame({'Valores': [receitas, despesas]}, index=['Entradas', 'Saídas']))
            st.dataframe(df_lista, use_container_width=True, hide_index=True)
        else: st.info("Sem lançamentos.")

    # --- ⚙️ ADMIN COM CONFIG DE META ---
    elif escolha == "⚙️ Admin":
        st.title("⚙️ Administração")
        t1, t2, t3, t4, t5 = st.tabs(["💰 Finanças", "🎯 Definir Meta", "👥 Membros", "📻 Rádio/Live", "🛠 Limpeza"])
        
        with t1:
            membros_list = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0 ORDER BY nome ASC")
            with st.form("f_fin", clear_on_submit=True):
                nome_sel = st.selectbox("Selecione o Membro:", membros_list['nome'].tolist()) if not membros_list.empty else "Nenhum"
                codigo_sel = membros_list[membros_list['nome'] == nome_sel]['codigo'].values[0] if not membros_list.empty else ""
                val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
                tipo = st.selectbox("Tipo:", ["Dízimo", "Oferta", "Doação", "Despesa (Débito)"])
                if st.form_submit_button("Lançar"):
                    v_final = val if "Despesa" not in tipo else -val
                    executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d, :c, :v, :t)",
                                   {"d": datetime.now().strftime("%d/%m/%Y"), "c": codigo_sel, "v": v_final, "t": tipo})
                    st.success("Lançamento concluído!")

        with t2:
            st.subheader("Configurar Meta da Igreja")
            m_n = st.text_input("Nome da Meta (Ex: Reforma do Telhado)")
            m_v = st.number_input("Valor Alvo (R$)", min_value=0.0)
            if st.button("Salvar Meta"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('meta_nome', :v)", {"v": m_n})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('meta_valor', :v)", {"v": str(m_v)})
                st.success("Meta atualizada!")

        with t3:
            st.dataframe(consultar_db("SELECT nome, codigo, email FROM membros WHERE is_admin=0"))
        
        with t4:
            r_link = st.text_input("Link Rádio (MP3)")
            if st.button("Salvar Rádio"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :v)", {"v": r_link})
                st.success("Rádio salva!")
        
        with t5:
            if st.button("🗑 Limpar Chat"): executar_query("DELETE FROM chat_live"); st.rerun()

    # --- PÁGINAS RESTANTES ---
    elif escolha == "📢 Mural Ágape":
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f'<div class="palavra-dia-card"><h2>📖 Palavra do Dia</h2><p>"{p["versiculo"]}"</p><strong>— {p["referencia"]}</strong><br><br>{p["devocional"]}</div>', unsafe_allow_html=True)
        for _, r in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    elif escolha == "📻 Rádio Gospel":
        conf = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        url = conf.iloc[0]['valor'] if not conf.empty else "https://zeno.fm"
        st.title("📻 Rádio Ágape Online")
        st.audio(url)

    elif escolha == "📖 Bíblia":
        livros = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap}).iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")

    elif escolha == "🙏 Orações":
        with st.form("ora"):
            msg = st.text_area("Seu pedido")
            if st.form_submit_button("Pedir"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data) VALUES (:n, :p, :d)", {"n":u['nome'],"p":msg,"d":datetime.now().strftime("%d/%m/%Y")})
                st.success("Pedido enviado!")

    elif escolha == "📣 Ouvidoria":
        with st.form("ouv"):
            m = st.text_area("Elogio ou Sugestão")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO ouvidoria (data, mensagem, autor) VALUES (:d, :m, :a)", {"d":datetime.now().strftime("%d/%m/%Y"),"m":m,"a":u['nome']})
                st.success("Obrigado!")
