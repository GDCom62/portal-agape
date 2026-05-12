import sqlite3
import pandas as pd
import requests

def popular_biblia():
    conn = sqlite3.connect('agape_v60.db')
    cursor = conn.cursor()

    print("⏳ Baixando base de dados bíblica...")
    # URL de uma base Almeida simplificada em JSON/CSV
    url = "https://githubusercontent.com"
    
    try:
        df = pd.read_csv(url)
        # Ajustamos os nomes das colunas para bater com sua tabela: livro, cap, ver, texto
        df = df[['livro', 'capitulo', 'versiculo', 'texto']]
        df.columns = ['livro', 'cap', 'ver', 'texto']

        print(f"📖 Importando {len(df)} versículos para o Banco Ágape...")
        df.to_sql('biblia', conn, if_exists='append', index=False)
        
        conn.commit()
        print("✅ Bíblia importada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    popular_biblia()
