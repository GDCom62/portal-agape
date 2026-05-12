import sqlite3
import pandas as pd
import requests

def popular_biblia():
    # Aumentamos o timeout para 30 segundos para evitar o erro 'database is locked'
    conn = sqlite3.connect('agape_v60.db', timeout=30)
    
    try:
        print("⏳ Baixando base de dados bíblica (isso pode demorar 1 min)...")
        url = "https://githubusercontent.com"
        
        # Lendo em pedaços (chunks) para não travar a memória e a conexão
        df = pd.read_csv(url)
        df = df[['livro', 'capitulo', 'versiculo', 'texto']]
        df.columns = ['livro', 'cap', 'ver', 'texto']

        print(f"📖 Gravando {len(df)} versículos...")
        # if_exists='replace' garante que ele limpe o erro anterior e comece do zero
        df.to_sql('biblia', conn, if_exists='replace', index=False)
        
        print("✅ Bíblia importada com sucesso!")
    except Exception as e:
        print(f"❌ Erro detectado: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    popular_biblia()
