    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada (ACF)")
        
        # Busca livros carregados
        res_livros = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not res_livros.empty:
            livros = res_livros['livro'].tolist()
            col_l, col_c = st.columns(2)
            
            with col_l:
                l_sel = st.selectbox("Selecione o Livro", livros)
            
            # Busca capítulos do livro selecionado
            caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap", {"l": l_sel})['cap'].tolist()
            with col_c:
                c_sel = st.selectbox("Capítulo", caps)
            
            # Exibe os versículos estilo Facebook (em um card branco)
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver", {"l": l_sel, "c": c_sel})
            for _, v in versos.iterrows():
                st.markdown(f"**{v['ver']}** {v['texto']}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("A base da Bíblia está vazia. Vá em 'Modo Admin' e clique em 'Importar acf.json'.")
