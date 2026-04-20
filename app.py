# --- CONTINUAÇÃO DO app.py ---

elif menu == "Bíblia":
    st.header("📖 Bíblia Sagrada")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        livro_busca = st.selectbox("Selecione o Livro", ["Gênesis", "Êxodo", "Salmos", "Mateus", "João"]) # Exemplo
    with col2:
        cap_busca = st.number_input("Capítulo", min_value=1, value=1)
    with col3:
        st.button("Buscar")

    # Exemplo de como exibir o texto (Simulando busca no banco)
    st.info("Aqui aparecerá o texto bíblico e a explicação cadastrada no banco.")
    # Exemplo de Áudio (substituindo o audio_url do seu modelo)
    # st.audio("link_do_audio.mp3")

elif menu == "Harpa Cristã":
    st.header("🎵 Harpa Cristã")
    num_hino = st.number_input("Número do Hino", min_value=1, step=1)
    
    if st.button("Abrir Hino"):
        with app.app_context():
            from sqlalchemy import select
            # Busca no banco de dados que você já tem
            hino = db.session.execute(select(Harpa).filter_by(numero=num_hino)).scalar()
            if hino:
                st.subheader(f"Hino {hino.number}: {hino.titulo}")
                st.text(hino.letra)
            else:
                st.error("Hino não encontrado.")

elif menu == "Prestação de Contas":
    st.header("💰 Prestação de Contas")
    
    # Formulário para nova entrada
    with st.expander("Registrar Nova Movimentação"):
        desc = st.text_input("Descrição")
        valor = st.number_input("Valor (R$)", format="%.2f")
        if st.button("Salvar Registro"):
            with app.app_context():
                nova_conta = PrestacaoContas(descricao=desc, valor=valor)
                db.session.add(nova_conta)
                db.session.commit()
                st.success("Registrado!")

    # Exibição em Tabela (O forte do Streamlit)
    st.subheader("Histórico Recente")
    with app.app_context():
        contas = PrestacaoContas.query.all()
        if contas:
            # Transforma os dados do banco em uma lista para o Streamlit exibir
            dados = [{"Data": c.data.strftime("%d/%m/%Y"), "Descrição": c.descricao, "Valor": f"R$ {c.valor:.2f}"} for c in contas]
            st.table(dados) # Ou st.dataframe(dados) para tabelas interativas
