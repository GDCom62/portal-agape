    elif menu == "💬 Chat Online":
        st.title("💬 Chat Comunitário Ágape")
        
        # Link que passa o usuário logado no portal para o chat
        link_final = f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=Geral"
        
        st.markdown(f"""
            <div style="
                background: white; 
                padding: 40px; 
                border-radius: 20px; 
                text-align: center; 
                box-shadow: 0 10px 25px rgba(0,0,0,0.05);
                border: 1px solid #e1e4e8;
                margin-top: 20px;
            ">
                <div style="font-size: 50px; margin-bottom: 20px;">💬</div>
                <h2 style="color: #1877f2; margin-bottom: 10px;">Ambiente de Conversa Seguro</h2>
                <p style="color: #65676b; margin-bottom: 30px;">
                    Bem-vindo, <b>{u['nome']}</b>!<br>
                    Clique no botão abaixo para abrir o chat em uma aba exclusiva com vídeo e anexos.
                </p>
                <a href="{link_final}" target="_blank" style="
                    background: linear-gradient(135deg, #1877f2, #0054ca);
                    color: white !important;
                    padding: 16px 40px;
                    text-decoration: none;
                    border-radius: 30px;
                    font-weight: bold;
                    font-size: 18px;
                    box-shadow: 0 4px 15px rgba(24, 119, 242, 0.4);
                    display: inline-block;
                    transition: transform 0.2s;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    ABRIR CHAT AGORA
                </a>
                <p style="margin-top: 25px; font-size: 14px; color: #8a8d91;">
                    <i class="fas fa-lock"></i> Conexão criptografada e segura
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 Dica: Ao abrir o chat, você pode alternar entre as abas do navegador para continuar navegando no portal.")
