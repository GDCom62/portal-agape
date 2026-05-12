import streamlit as st
import random

def carregar_louvor_flutuante():
    # Lista de frases para o sorteio
    frases = [
        {"texto": "Grandes coisas fez o Senhor por nós, por isso estamos alegres.", "ref": "Salmos 126:3"},
        {"texto": "Tudo quanto tem fôlego louve ao Senhor.", "ref": "Salmos 150:6"},
        {"texto": "O Senhor é a minha força e o meu escudo.", "ref": "Salmos 28:7"},
        {"texto": "Agradeçam ao Senhor, porque ele é bom.", "ref": "1 Crônicas 16:34"}
    ]

    # Sorteia uma frase nova cada vez que o app rodar ou o botão for clicado
    if 'frase_atual' not in st.session_state:
        st.session_state.frase_atual = random.choice(frases)

    def trocar_frase():
        st.session_state.frase_atual = random.choice(frases)

    # Injeção de CSS e HTML
    st.markdown(
        f"""
        <style>
        .floating-louvor {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 280px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            z-index: 9999;
        }}
        .ref-style {{ font-size: 0.8rem; font-weight: bold; color: #7101FF; }}
        </style>
        
        <div class="floating-louvor">
            <div class="ref-style">{st.session_state.frase_atual['ref']}</div>
            <div style="font-style: italic; margin-bottom: 10px;">
                "{st.session_state.frase_atual['texto']}"
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Botão do Streamlit posicionado na sidebar ou fixo para trocar
    if st.sidebar.button("🙏 Renovar Louvor"):
        trocar_frase()
        st.rerun()
