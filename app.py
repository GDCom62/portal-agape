    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada ACF (Módulo Nativo)")
        
        # Filtros de navegação da Bíblia
        col_livro, col_cap = st.columns(2)
        with col_livro:
            livro_sel = st.selectbox("Selecione o Livro:", list(BIBLIA_ESTAVEL.keys()))
        with col_cap:
            capitulos_disponiveis = list(BIBLIA_ESTAVEL[livro_sel].keys())
            cap_sel = st.selectbox("Selecione o Capítulo:", capitulos_disponiveis)
        
        st.write(f"### {livro_sel} - Capítulo {cap_sel}")
        
        # Exibição dos versículos estilizados
        versiculos = BIBLIA_ESTAVEL[livro_sel][cap_sel]
        for num_ver, texto_ver in versiculos.items():
            st.markdown(f'<div class="leitura-box"><b>{num_ver}.</b> {texto_ver}</div>', unsafe_allow_html=True)

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros da Igreja")
        
        # Permissão especial para edição
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("➕ Cadastrar Novo Membro", expanded=False):
                with st.form("form_membro"):
                    nome = st.text_input("Nome Completo")
                    tel = st.text_input("Telefone / WhatsApp")
                    cargo = st.selectbox("Cargo / Função", ["Membro", "Diácono", "Presbítero", "Evangelista", "Pastor", "Líder de Louvor"])
                    mes_aniv = st.selectbox("Mês de Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
                    obs = st.text_area("Observações Internas")
                    
                    if st.form_submit_button("Salvar Registro"):
                        if nome:
                            executar_query(
                                "INSERT INTO membros (nome, telephone, cargo, data_cadastro, mes_aniversario, observacoes) VALUES (:n, :t, :c, :d, :m, :o)",
                                {"n": nome, "t": tel, "c": cargo, "d": str(datetime.date.today()), "m": mes_aniv, "o": obs}
                            )
                            st.success("Membro cadastrado com sucesso!")
                            st.rerun()
                        else:
                            st.error("O campo Nome é obrigatório.")

        # Listagem de Membros
        df_membros = consultar_db("SELECT id, nome, telephone as Telefone, cargo as Cargo, mes_aniversario as Aniversário, data_cadastro as Cadastro FROM membros ORDER BY nome ASC")
        if not df_membros.empty:
            st.dataframe(df_membros, use_container_width=True, hide_index=True)
            
            # Remoção de membros por administradores
            if st.session_state.nivel_atual == "Pastor":
                id_remover = st.number_input("Digite o ID do membro para remover:", min_value=1, step=1)
                if st.button("Remover Membro permanentemente", type="primary"):
                    executar_query("DELETE FROM membros WHERE id = :id", {"id": id_remover})
                    st.success("Registro removido.")
                    st.rerun()
        else:
            st.info("Nenhum membro cadastrado até o momento.")

    elif escolha == "Cadastro de Visitantes":
        st.subheader("🤝 Recepção e Cadastro de Visitantes")
        
        with st.form("form_visitante"):
            v_nome = st.text_input("Nome do Visitante")
            v_tel = st.text_input("Telefone de Contato")
            v_visita = st.selectbox("Solicita visita pastoral/equipe?", ["Não", "Sim"])
            v_obs = st.text_area("Pedidos de oração ou observações")
            
            if st.form_submit_button("Registrar Visita"):
                if v_nome:
                    executar_query(
                        "INSERT INTO visitantes (nome, telephone, data_visita, observacoes, precisa_visita) VALUES (:n, :t, :d, :o, :p)",
                        {"n": v_nome, "t": v_tel, "d": str(datetime.date.today()), "o": v_obs, "p": v_visita}
                    )
                    st.success("Visitante registrado! Seja bem-vindo!")
                    st.rerun()
                else:
                    st.error("Por favor, preencha o nome do visitante.")

        df_visitantes = consultar_db("SELECT nome as Nome, telephone as Telefone, data_visita as [Data da Visita], precisa_visita as [Pede Visita], observacoes as Observações FROM visitantes ORDER BY id DESC")
        st.write("### Histórico de Visitas recentes")
        st.dataframe(df_visitantes, use_container_width=True, hide_index=True)

    elif escolha == "Escala de Cultos":
        st.subheader("📅 Escala de Ministérios e Voluntários")
        
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("🗓️ Agendar Nova Escala"):
                with st.form("form_escala"):
                    e_data = st.date_input("Data do Culto", datetime.date.today())
                    e_min = st.selectbox("Ministério / Equipe", ["Louvor", "Sonoplastia", "Mídia / Projeção", "Infantil / Crianças", "Recepção / Acolhimento", "Pregação"])
                    e_vol = st.text_input("Nome do Voluntário / Responsável")
                    e_per = st.selectbox("Período", ["Manhã", "Noite", "Culto Especial"])
                    
                    if st.form_submit_button("Confirmar Escala"):
                        executar_query(
                            "INSERT INTO escalas (data, ministerio, voluntario, periodo) VALUES (:d, :m, :v, :p)",
                            {"d": str(e_data), "m": e_min, "v": e_vol, "p": e_per}
                        )
                        st.success("Escala salva!")
                        st.rerun()

        df_escalas = consultar_db("SELECT data as Data, ministerio as Ministério, voluntario as Voluntário, periodo as Período FROM escalas ORDER BY data ASC")
        st.dataframe(df_escalas, use_container_width=True, hide_index=True)

    elif escolha == "Escala de Visitas":
        st.subheader("🚗 Cronograma de Visitações nos Lares")
        
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("📍 Agendar Nova Visita"):
                with st.form("form_visita_lar"):
                    vi_data = st.date_input("Data Programada", datetime.date.today())
                    vi_irmao = st.text_input("Irmão / Família a ser visitada")
                    vi_end = st.text_input("Endereço Residencial")
                    vi_resp = st.text_input("Responsável pela comitiva de visita")
                    
                    if st.form_submit_button("Agendar Visitação"):
                        executar_query(
                            "INSERT INTO escalas_visitas (data, irmao_visitado, endereço, responsavel) VALUES (:d, :i, :e, :r)",
                            {"d": str(vi_data), "i": vi_irmao, "e": vi_end, "r": vi_resp}
                        )
                        st.success("Visita agendada com sucesso!")
                        st.rerun()

        df_visitas = consultar_db("SELECT data as Data, irmao_visitado as [Família Visitada], endereço as Endereço, responsavel as Responsável FROM escalas_visitas ORDER BY data ASC")
        st.dataframe(df_visitas, use_container_width=True, hide_index=True)

    elif escolha == "Financeiro & Dízimos":
        st.subheader("💰 Gestão Financeira Transparente")
        
        # Apenas liderança sênior acessa os lançamentos
        if st.session_state.nivel_atual == "Pastor":
            col_lan1, col_lan2 = st.columns(2)
            with col_lan1:
                st.markdown("### 📥 Lançar Dízimo / Entrada")
                with st.form("form_entrada"):
                    en_membro = st.text_input("Nome do Contribuinte (Opcional/Anônimo)")
                    en_val = st.number_input("Valor Recebido (R\$)", min_value=0.0, format="%.2f")
                    en_desc = st.selectbox("Categoria", ["Dízimo", "Oferta Voluntária", "Oferta de Missões", "Doação Específica"])
                    
                    if st.form_submit_button("Registrar Entrada"):
                        mes_ano_atual = datetime.date.today().strftime("%m/%Y")
                        executar_query(
                            "INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano, membro_id) VALUES ('Entrada', :d, :v, :dat, :ma, 0)",
                            {"d": f"{en_desc} - {en_membro}", "v": en_val, "dat": str(datetime.date.today()), "ma": mes_ano_atual}
                        )
                        st.success("Entrada registrada financeiramente!")
                        st.rerun()
                        
            with col_lan2:
                st.markdown("### 📤 Lançar Despesa / Saída")
                with st.form("form_saida"):
                    sa_desc = st.text_input("Descrição da Despesa (ex: Água, Luz, Aluguel)")
                    sa_val = st.number_input("Valor Pago (R\$)", min_value=0.0, format="%.2f")
                    
                    if st.form_submit_button("Registrar Saída", type="primary"):
                        mes_ano_atual = datetime.date.today().strftime("%m/%Y")
                        executar_query(
                            "INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano, membro_id) VALUES ('Saída', :d, :v, :dat, :ma, 0)",
                            {"d": sa_desc, "v": sa_val, "dat": str(datetime.date.today()), "ma": mes_ano_atual}
                        )
                        st.success("Saída registrada financeiramente!")
                        st.rerun()

        # Balanço Geral Visível a todos os autenticados para transparência
        df_fin = consultar_db("SELECT tipo, valor FROM financeiro")
        total_entradas = df_fin[df_fin['tipo'] == 'Entrada']['valor'].sum() if not df_fin.empty else 0.0
        total_saidas = df_fin[df_fin['tipo'] == 'Saída']['valor'].sum() if not df_fin.empty else 0.0
        saldo_geral = total_entradas - total_saidas

