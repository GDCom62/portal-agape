import streamlit as st
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
import hashlib

# 1. INICIALIZAÇÃO DO APP E DB (Sempre no topo)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal_r.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 2. DEFINIÇÃO DOS MODELOS (Fora de qualquer 'if')
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

# 3. CRIAÇÃO DAS TABELAS (Apenas uma vez)
if 'db_created' not in st.session_state:
    with app.app_context():
        db.create_all()
    st.session_state.db_created = True

# 4. FUNÇÕES DE APOIO
def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# --- DAQUI PARA BAIXO SEGUE O RESTANTE DO SEU CÓDIGO (LOGIN / INTERFACE) ---

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("⛪ Portal Ágape")
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Conta"])

    with aba_login:
        email_l = st.text_input("Email", key="login_email")
        senha_l = st.text_input("Senha", type="password", key="login_senha")
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

# (Continue com a Área Logada abaixo...)
else:
    st.sidebar.title(f"Olá, {st.session_state.usuario_nome}")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()
    # ... Resto do menu (Bíblia, Harpa, etc)
