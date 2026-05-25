    with aba_side_esqueci:
        with st.form(key="form_reset_senha"):
            reset_user = st.text_input("E-mail Cadastrado").strip()
            nova_senha_pura = st.text_input("Nova Senha Desejada", type="password")
            botao_resetar = st.form_submit_button("Atualizar Senha", use_container_width=True)
            
            if botao_resetar:
                if reset_user and nova_senha_pura:
                    check_user = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reset_user})
                    if not check_user.empty:
                        if len(nova_senha_pura) < 4:
                            st.error("A nova senha precisa ter no mínimo 4 caracteres.")
                        else:
                            hash_reset = generate_password_hash(nova_senha_pura, method="scrypt")
                            executar_query("UPDATE usuarios SET senha = :s WHERE usuario = :u", {"s": hash_reset, "u": reset_user})
                            st.success("Senha atualizada! Faça login na aba 'Entrar'.")
                    else:
                        st.error("E-mail não encontrado no sistema.")
                else:
                    st.warning("Preencha todos os campos.")

# --- 6. PAINEL PRINCIPAL (APÓS AUTENTICAÇÃO BEM-SUCEDIDA) ---
else:
    st.sidebar.success(f"Conectado como: {st.session_state.usuario_atual}")
    st.sidebar.info(f"Nível de Acesso: {st.session_state.nivel_atual}")
    
    if st.sidebar.button("⚙️ Desconectar / Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.session_state.nivel_atual = "Membro"
        st.rerun()

    # Menu principal do Portal
    menu = ["Início & Versículos", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu)

    # --- ABA: HOME ---
    if escolha == "Início & Versículos":
        st.title("⛪ Bem-vindo ao Portal Ágape")
        
        # Bloco utilizando o CSS customizado (Fundo escuro e letras Amarelo Ouro)
        st.markdown("""
            <div class="versiculo-box">
                <div class="texto-sagrado-grande">
                    <span class="numero-versiculo">João 3:16</span> 
                    "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    # --- ABA: MEMBROS ---
    elif escolha == "Membros":
        st.title("👥 Gestão de Membros")
        df_membros = consultar_db("SELECT * FROM membros")
        if not df_membros.empty:
            st.dataframe(df_membros, use_container_width=True)
        else:
            st.info("Nenhum membro cadastrado ainda.")

    # --- ABA: FINANCEIRO ---
    elif escolha == "Financeiro":
        st.title("💰 Painel Financeiro")
        if st.session_state.nivel_atual == "Pastor":
            df_fin = consultar_db("SELECT * FROM financeiro")
            if not df_fin.empty:
                st.dataframe(df_fin, use_container_width=True)
            else:
                st.info("Nenhum lançamento financeiro registrado.")
        else:
            st.error("Apenas a liderança/pastores possuem acesso visual aos dados financeiros.")

    # --- ABA: AVISOS ---
    elif escolha == "Avisos":
        st.title("📢 Mural de Avisos")
        df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if not df_avisos.empty:
            for idx, row in df_avisos.iterrows():
                st.subheader(row['titulo'])
                st.caption(f"Postado em: {row['data']}")
                st.write(row['conteudo'])
                st.divider()
        else:
            st.info("Não há avisos recentes no mural.")

    # --- ABA: LOUVORES ---
    elif escolha == "Louvores":
        st.title("🎵 Repertório de Louvores")
        df_louvores = consultar_db("SELECT id, titulo, artista, letra FROM louvores")
        if not df_louvores.empty:
            st.dataframe(df_louvores, use_container_width=True)
        else:
            st.info("Nenhum louvor catalogado no repertório.")
