from app import app, db, Harpa, Biblia

with app.app_context():
    # Adicionando mais hinos
    h2 = Harpa(numero=2, titulo="Deixai Entrar o Rei da Glória", letra="Tu que estais em pecado...")
    h15 = Harpa(numero=15, titulo="Foi na Cruz", letra="Aliviado nos dias de dor...")
    
    # Adicionando versículos da Bíblia
    v1 = Biblia(livro="Salmos", capitulo=23, versiculo=1, texto="O Senhor é o meu pastor...", explicacao="Deus como guia supremo.")
    
    db.session.add_all([h2, h15, v1]) # Adiciona todos de uma vez
    db.session.commit()
    print("Dados extras inseridos com sucesso!")
