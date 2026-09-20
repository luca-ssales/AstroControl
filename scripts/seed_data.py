import os
import sys
import sqlite3
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Garante a resolução correta dos diretórios da aplicação
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "database", "loja.db")

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🚀 Iniciando população/restauração da base de dados...")

    # Garante usuário Master
    senha_hash = generate_password_hash("123456")
    cursor.execute("SELECT id FROM usuarios WHERE email = 'master@loja.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha, cargo, comissao_percentual, primeiro_login, ativo, loja_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("Master", "master@loja.com", senha_hash, "master", 0.0, 0, 1, 1)
        )

    # Garante Loja Matriz
    cursor.execute("SELECT id FROM lojas WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO lojas (id, nome, cnpj, email, ativo) VALUES (1, 'AstroControl Matriz', '12.345.678/0001-90', 'contato@astromatriz.com.br', 1)")

    conn.commit()
    conn.close()
    print("✨ Base de dados verificada e pronta!")

if __name__ == "__main__":
    seed()
