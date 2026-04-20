import streamlit as st
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
import hashlib

# 1. CONFIGURAÇÃO DO AMBIENTE E BANCO DE DADOS
if 'app_initialized' not in st.session_state:
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal_r.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    
    # Modelos de Tabela
    class Membro(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        nome = db.Column(db.String(100))
        email = db.Column(db.String(100), unique=True)
        senha = db.Column(db.String(100))
        codigo_membro = db.Column(db.String(20), unique=True, default=lambda: str(uuid.uuid4().hex[:6]).upper())

    class PrestacaoContas(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        descricao = db.Column(db.String(200))
        valor = db.Column(db.Float)
        data = db.Column(db.DateTime, default=datetime.utcnow)

    with app.app_context():
        db.create_all()
    
    st.session_state.db = db
    st.session_state.app = app
    st.session_state.app_initialized = True

db = st.session_state.db
app = st.session_state.app

# 2. FUNÇÕES DE APOIO
def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# 3. INTERFACE DE AUTENTICAÇÃO (LOGIN / CADASTRO)
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("⛪ Portal Ágape")
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Conta"])

    with aba_login:
        email_l = st.text_input("Email")
        senha_l = st.text_input("Senha", type="password")
        if st.button("Acessar"):
            with app.app_context():
                user = Membro.query.filter_by(email=email_l).first()
                if user and user.senha == gerar_hash(senha_l):
                    st.session_state.autenticado = True
                    st.session_state.usuario_nome = user.nome
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

    with aba_cadastro:
        nome_c = st.text_input("Nome Completo")
        email_c = st.text_input("Email para Cadastro")
        senha_c = st.text_input("Crie uma Senha", type="password")
        if st.button("Cadastrar"):
            with app.app_context():
                if Membro.query.filter_by(email=email_c).first():
                    st.error("Este email já existe!")
                else:
                    novo = Membro(nome=nome_c, email=email_c, senha=gerar_hash(senha_c))
                    db.session.add(novo)
                    db.session.commit()
                    st.success("Conta criada! Vá para a aba 'Entrar'.")

# 4. ÁREA LOGADA
else:
    st.sidebar.title(f"Olá, {st.session_state.usuario_nome}")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    menu = st.sidebar.selectbox("Navegação", ["Home", "Bíblia", "Harpa Cristã", "Financeiro"])

    if menu == "Home":
        st.title("⛪ Bem-vindo ao Portal")
        st.write("Selecione uma opção no menu lateral para começar.")

    elif menu == "Bíblia":
        st.header("📖 Bíblia Sagrada")
        pesquisa = st.text_input("Buscar versículo...")
        st.info("Funcionalidade de busca em desenvolvimento.")

    elif menu == "Harpa Cristã":
        st.header("🎵 Harpa Cristã")
        st.number_input("Número do Hino", min_value=1)
        st.button("Buscar Hino")

    elif menu == "Financeiro":
        st.header("💰 Prestação de Contas")
        with st.form("lancamento"):
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor R$", min_value=0.0)
            if st.form_submit_button("Lançar"):
                with app.app_context():
                    novo_lanca = PrestacaoContas(descricao=desc, valor=valor)
                    db.session.add(novo_lanca)
                    db.session.commit()
                st.success("Lançado com sucesso!")

        st.subheader("Histórico")
        with app.app_context():
            dados = PrestacaoContas.query.all()
            if dados:
                st.table([{"Data": d.data.strftime("%d/%m/%Y"), "Descrição": d.descricao, "Valor": f"R$ {d.valor:.2f}"} for d in dados])
