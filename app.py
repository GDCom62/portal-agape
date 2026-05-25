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
                            st.success("Senha atualizada! Vá para a aba 'Entrar'.")
                    else:
                        st.error("E-mail não encontrado.")
                else:
                    st.warning("Preencha todos os campos.")

# --- 6. PAINEL PRINCIPAL (APÓS AUTENTICAÇÃO) ---
else:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_atual}")
    st.sidebar.info(f"Nível: {st.session_state.nivel_atual}")
    
    if st.sidebar.button("⚙️ Logout / Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.session_state.nivel_atual = "Membro"
        st.rerun()

    menu = ["Início & Versículos", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu)

    # --- ABA 1: HOME ---
    if escolha == "Início & Versículos":
        st.title("⛪ Bem-vindo ao Portal Ágape")
        st.markdown("""
            <div class="versiculo-box">
                <div class="texto-sagrado-grande">
                    <span class="numero-versiculo">João 3:16</span> 
                    "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        df_m_total = consultar_db("SELECT id FROM membros")
        total_m = len(df_m_total)
        st.metric("Total de Membros Cadastrados", f"{total_m} Irmãos")
        st.info("💡 Use o menu superior para realizar novos cadastros, lançamentos ou verificar escalas.")

    # --- ABA 2: MEMBROS ---
    elif escolha == "Membros":
        st.title("👥 Gestão e Cadastro de Membros")
        
        aba_ver, aba_cadastrar = st.tabs(["Ver Membros", "Cadastrar Novo Membro"])
        
        with aba_cadastrar:
            with st.form("cad_membro"):
                nome = st.text_input("Nome do Membro")
                telefone = st.text_input("Telefone / WhatsApp")
                cargo = st.selectbox("Cargo / Função", ["Membro", "Diácono", "Presbítero", "Evangelista", "Pastor", "Missionária", "Líder de Louvor"])
                mes_aniv = st.selectbox("Mês de Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
                obs = st.text_area("Observações")
                
                if st.form_submit_button("Salvar Membro"):
                    if nome:
                        data_atual = datetime.date.today().strftime('%d/%m/%Y')
                        executar_query("""
                            INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario, observacoes)
                            VALUES (:nome, :tel, :cargo, :dt, :mes, :obs)
                        """, {"nome": nome, "tel": telefone, "cargo": cargo, "dt": data_atual, "mes": mes_aniv, "obs": obs})
                        st.success(f"{nome} cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("O campo 'Nome' é obrigatório.")
                        
        with aba_ver:
            busca = st.text_input("Buscar membro por nome:")
            if busca:
                df_membros = consultar_db("SELECT * FROM membros WHERE nome LIKE :b", {"b": f"%{busca}%"})
            else:
                df_membros = consultar_db("SELECT * FROM membros")
                
            if not df_membros.empty:
                for idx, row in df_membros.iterrows():
                    st.markdown(f"""
                    <div class="cartao-membro" style="margin-bottom:10px;">
                        <h4>👤 {row['nome']}</h4>
                        <p><b>Cargo:</b> {row['cargo']} | <b>Contato:</b> {row['telefone']} | <b>Aniversário:</b> {row['mes_aniversario']}</p>
                        <p style='font-size:13px; color:#555;'><i>Obs: {row['observacoes']}</i></p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Excluir {row['nome']}", key=f"del_m_{row['id']}"):
                        executar_query("DELETE FROM membros WHERE id = :id", {"id": row['id']})
                        st.rerun()
            else:
                st.info("Nenhum membro encontrado.")

    # --- ABA 3: FINANCEIRO ---
    elif escolha == "Financeiro":
        st.title("💰 Controle Financeiro da Igreja")
        
        if st.session_state.nivel_atual != "Pastor":
            st.error("🔒 Acesso Restrito. Apenas a liderança pastoral possui permissão para visualizar e gerenciar o livro caixa.")
            st.markdown("""
                <div class="pix-card">
                    <h3>Chave PIX da Igreja</h3>
                    <p style="font-size:20px; font-weight:bold; color:#008080;">pix@igrejaagape.com.br</p>
                    <p>Contribua com seus dízimos e ofertas voluntárias diretamente da sua conta.</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            aba_lancar, aba_caixa = st.tabs(["Lançar Movimentação", "Livro Caixa"])
            
            with aba_lancar:
                with st.form("cad_financeiro"):
                    tipo = st.radio("Tipo de Entrada", ["Entrada (Dízimo/Oferta)", "Saída (Despesa)"])
                    desc = st.text_input("Descrição / Finalidade")
                    val = st.number_input("Valor (R\$)", min_value=0.0, step=10.0)
                    
                    df_m_lista = consultar_db("SELECT id, nome FROM membros")
                    membros_opcoes = {row['nome']: row['id'] for idx, row in df_m_lista.iterrows()}
                    membros_opcoes["Nenhum / Não Atribuído"] = None
                    membro_sel = st.selectbox("Associar a um Membro (Se dízimo)", list(membros_opcoes.keys()))
                    
                    if st.form_submit_button("Registrar Lançamento"):
                        if desc and val > 0:
                            hj = datetime.date.today()
                            dt_str = hj.strftime('%d/%m/%Y')
                            mes_ano_str = hj.strftime('%m/%Y')
                            m_id = membros_opcoes[membro_sel]
                            
                            executar_query("""
                                INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano, membro_id)
                                VALUES (:tipo, :desc, :val, :dt, :ma, :mid)
                            """, {"tipo": tipo, "desc": desc, "val": val, "dt": dt_str, "ma": mes_ano_str, "mid": m_id})
                            st.success("Movimentação registrada!")
                            st.rerun()
                        else:
                            st.error("Preencha a descrição e defina um valor válido.")
                            
            with aba_caixa:
                df_fin = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
                if not df_fin.empty:
                    ent = df_fin[df_fin['tipo'].str.contains("Entrada")]['valor'].sum()
                    sai = df_fin[df_fin['tipo'].str.contains("Saída")]['valor'].sum()
                    saldo = ent - sai
                    
                    st.metric("Total Entradas", f"R\$ {ent:,.2f}")
                    st.metric("Total Saídas", f"R\$ {sai:,.2f}")
                    st.metric("Saldo Atual", f"R\$ {saldo:,.2f}")
                    
                    st.subheader("Histórico de Transações")
                    st.dataframe(df_fin, use_container_width=True)
                else:
                    st.info("Nenhuma movimentação registrada.")

    # --- ABA 4: AVISOS ---
    elif escolha == "Avisos":
        st.title("📢 Mural de Avisos")
        
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("➕ Publicar Novo Aviso"):
                with st.form("cad_aviso"):
                    t_aviso = st.text_input("Título do Aviso")
                    c_aviso = st.text_area("Conteúdo do Comunicado")
                    if st.form_submit_button("Postar no Mural"):
                        if t_aviso and c_aviso:
                            dt_aviso = datetime.date.today().strftime('%d/%m/%Y')
                            executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                           {"t": t_aviso, "c": c_aviso, "d": dt_aviso})
                            st.success("Aviso postado!")
                            st.rerun()
                            
        df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if not df_avisos.empty:
            for idx, row in df_avisos.iterrows():
                st.subheader(row['titulo'])
                st.caption(f"📅 Postado em: {row['data']}")
                st.write(row['conteudo'])
                if st.session_state.nivel_atual == "Pastor":
