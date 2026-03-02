from app import app, db, Biblia

def inserir_dados():
    with app.app_context():
        # Versículo 1
        v1 = Biblia(
            livro="Salmos",
            capitulo=23,
            versiculo=1,
            texto="O Senhor é o meu pastor; nada me faltará.",
            explicacao="Davi usa a metáfora do pastor para mostrar que Deus provê descanso, proteção e direção constante.",
            audio_url="/static/audios/salmo23_1.mp3"
        )

        # Versículo 2
        v2 = Biblia(
            livro="Salmos",
            capitulo=23,
            versiculo=2,
            texto="Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.",
            explicacao="Refere-se ao descanso espiritual. As 'águas tranquilas' simbolizam a paz que só o Espírito Santo traz.",
            audio_url="/static/audios/salmo23_2.mp3"
        )

        # Adiciona e salva no banco portal_r.db
        db.session.add(v1)
        db.session.add(v2)
        db.session.commit()
        print("Salmo 23 inserido com sucesso!")

if __name__ == "__main__":
    inserir_dados()
