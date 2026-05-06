import os
import redis
import json
import datetime
from flask import Flask, Response, render_template, request

app = Flask(__name__)
app.secret_key = 'agape_secret_key'

# CONFIGURAÇÃO REDIS (Pegue estes dados no Upstash)
REDIS_HOST = 'seu-endpoint-aqui.upstash.io'
REDIS_PORT = 6379 # Geralmente é 6379
REDIS_PASS = 'sua-senha-aqui'

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    ssl=True, # Upstash exige SSL
    decode_responses=True
)

@app.route('/')
def index():
    # Recebe o nome do usuário e sala via link do Portal Ágape
    user = request.args.get('user', 'Irmão')
    room = request.args.get('room', 'Geral')
    
    # Busca histórico das últimas 50 mensagens
    history_raw = r.lrange(f"chat:{room}", 0, -1)
    history = [json.loads(m) for m in history_raw]
    
    return render_template('chat_externo.html', user=user, room=room, history=history)

@app.route('/post', methods=['POST'])
def post():
    msg = request.form.get('message')
    user = request.form.get('user')
    room = request.form.get('room')
    
    if msg:
        payload = json.dumps({
            "user": user, 
            "text": msg, 
            "time": datetime.datetime.now().strftime("%H:%M")
        })
        # Salva e Publica
        r.rpush(f"chat:{room}", payload)
        r.ltrim(f"chat:{room}", -50, -1)
        r.publish(f"canal:{room}", payload)
        
    return Response(status=204)

@app.route('/stream/<room>')
def stream(room):
    def event_stream():
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(f"canal:{room}")
        # Envia um ping para manter conexão
        yield "data: {\"status\": \"connected\"}\n\n"
        for message in pubsub.listen():
            yield f"data: {message['data']}\n\n"
            
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    # Porta dinâmica para o Render/Heroku
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
