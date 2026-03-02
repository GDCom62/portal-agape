from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import uuid
import os

# 1. INICIALIZAÇÃO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave_sagrada_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal_r.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. CONFIGURAÇÃO DO BANCO (O segredo para remover o erro)
db = SQLAlchemy(app)

# 3. MODELOS (Com as correções de tabela)
class Membro(UserMixin, db.Model):
    __tablename__ = 'membro'
    __table_args__ = {'extend_existing': True} # Isso força a aceitação
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    senha = db.Column(db.String(100))
    codigo_membro = db.Column(db.String(20), unique=True, default=lambda: str(uuid.uuid4().hex[:6]).upper())

class Biblia(db.Model):
    __tablename__ = 'biblia'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    livro = db.Column(db.String(50))
    capitulo = db.Column(db.Integer)
    versiculo = db.Column(db.Integer)
    texto = db.Column(db.Text)
    explicacao = db.Column(db.Text)
    audio_url = db.Column(db.String(200))

class MensagemChat(db.Model):
    __tablename__ = 'mensagem_chat'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    usuario_nome = db.Column(db.String(100))
    texto = db.Column(db.String(500))
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)

class PrestacaoContas(db.Model):
    __tablename__ = 'prestacao_contas'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    codigo_referencia = db.Column(db.String(20))
    descricao = db.Column(db.String(200))
    valor = db.Column(db.Float)
    data = db.Column(db.DateTime, default=datetime.utcnow)

class Harpa(db.Model):
    __tablename__ = 'harpa'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True)
    titulo = db.Column(db.String(150))
    letra = db.Column(db.Text)

# 4. RESTANTE DAS CONFIGURAÇÕES
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Membro.query.get(int(user_id))

# ROTA INICIAL PARA TESTE
@app.route('/')
def index():
    return "Portal R no ar! Vá para /cadastro para começar."

# ... (Mantenha as outras rotas que você já tem abaixo desta linha)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)


