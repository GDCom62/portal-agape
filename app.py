import streamlit as st
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

# 1. CONFIGURAÇÃO DO AMBIENTE (Simulando o Flask para o SQLAlchemy)
if 'app_initialized' not in st.session_state:
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal_r.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    
    # Criando as tabelas dentro do contexto do Flask
    class Membro(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        nome = db.Column(db.String(100))
        email = db.Column(db.String(100), unique=True)
        senha = db.Column(db.String(100)) # No Streamlit usaremos simples

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

# 2. SISTEMA DE LOGIN SIMPLES (Substituindo Flask-Login)
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

def login():
    st.sidebar.title("🔐 Acesso Restrito")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        if usuario == "admin" and senha == "123": # Altere para sua lógica
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha inválidos")

# 3. INTERFACE PRINCIPAL
if not st.session_state.autenticado:
    st.title("⛪ Bem-vindo ao Portal Ágape")
    st.warning("Por favor, faça login no menu lateral para acessar o conteúdo.")
    login()
else:
    st.sidebar.success("Conectado como Administrador")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    menu = st.sidebar.selectbox("Navegação", ["Home", "Bíblia", "Harpa Cristã", "Prestação de Contas"])

    if menu == "Home":
        st.title("🏠 Início")
        st.write("Portal de membros e gestão da igreja.")
        
    elif menu == "Prestação de Contas":
        st.title("💰 Financeiro")
        with st.form("nova_conta"):
            desc = st.text_input("Descrição da Despesa/Dízimo")
            val = st.number_input("Valor R$", min_value=0.0)
            if st.form_submit_button("Salvar"):
                with app.app_context():
                    nova = PrestacaoContas(descricao=desc, valor=val)
                    db.session.add(nova)
                    db.session.commit()
                st.success("Lançamento realizado!")

        # Mostrar Tabela
        with app.app_context():
            dados = PrestacaoContas.query.all()
            if dados:
                st.table([{"Descrição": d.descricao, "Valor": f"R$ {d.valor:.2f}", "Data": d.data.strftime("%d/%m/%Y")} for d in dados])
