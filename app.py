import os
import json
import sqlite3
from functools import wraps
from flask import Flask, redirect, render_template, request, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# 🚀 Inicialização do aplicativo Flask
app = Flask(__name__)

# Configuração da pasta onde as imagens dos produtos serão salvas
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.secret_key = "sistema_loja_123"


# 🔧 CRIAR BANCO DE DADOS E TABELAS
def criar_banco():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    # Tabela de USUÁRIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            cargo TEXT NOT NULL,
            comissao_percentual REAL DEFAULT 0.0,
            primeiro_login INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de CLIENTES
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tel TEXT,
            cpf TEXT UNIQUE NOT NULL,
            email TEXT,
            ativo INTEGER DEFAULT 1
        )
    """)

    # Tabela de CATEGORIAS DE PRODUTOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            criado_por TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pai_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL
        )
    """)

    # Tabela de PRODUTOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            codigo_barras TEXT UNIQUE NOT NULL,
            marca TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            preco_custo REAL DEFAULT 0.0,
            estoque INTEGER NOT NULL,
            estoque_minimo INTEGER NOT NULL,
            imagem TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cadastrado_por TEXT,
            categoria_id INTEGER REFERENCES categorias(id),
            ativo INTEGER DEFAULT 1
        )
    """)

    # Migrações seguras (colunas novas em bancos existentes)
    for migration in [
        "ALTER TABLE produtos ADD COLUMN cadastrado_por TEXT",
        "ALTER TABLE produtos ADD COLUMN categoria_id INTEGER REFERENCES categorias(id)",
        "ALTER TABLE usuarios ADD COLUMN permissoes TEXT",
    ]:
        try:
            cursor.execute(migration)
        except Exception:
            pass

    # Tabela de VENDAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            cliente_nome TEXT,
            cliente_cpf TEXT,
            total REAL,
            forma_pagamento TEXT,
            vendedor_id INTEGER,
            caixa_id INTEGER,
            comissao_paga REAL DEFAULT 0.0,
            status TEXT DEFAULT 'aberta',
            entrega INTEGER DEFAULT 0,
            entrega_rua TEXT,
            entrega_bairro TEXT,
            entrega_cep TEXT,
            entrega_complemento TEXT,
            entrega_numero TEXT,
            entrega_recebedor TEXT,
            entrega_telefone TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id),
            FOREIGN KEY(vendedor_id) REFERENCES usuarios(id),
            FOREIGN KEY(caixa_id) REFERENCES usuarios(id)
        )
    """)

    # Tabela de ITENS DA VENDA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_venda(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id INTEGER,
            produto_id INTEGER,
            nome_produto TEXT,
            quantidade INTEGER,
            preco_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(venda_id) REFERENCES vendas(id),
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    """)

    # Tabela de MOVIMENTAÇÕES DE ESTOQUE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            tipo TEXT,
            quantidade INTEGER,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    """)

    # Tabela de CONFIGURAÇÃO DA EMPRESA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresa(
            id INTEGER PRIMARY KEY,
            nome TEXT,
            razao_social TEXT,
            cnpj TEXT,
            tel TEXT,
            email TEXT,
            dominio TEXT,
            endereco_rua TEXT,
            endereco_numero TEXT,
            endereco_bairro TEXT,
            endereco_cep TEXT,
            endereco_cidade TEXT,
            endereco_estado TEXT,
            logo TEXT
        )
    """)

    # Tabela de DESPESAS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS despesas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT NOT NULL,
            data DATE NOT NULL
        )
    """)

    # Tabela de IMAGENS DO PRODUTO (GALERIA MULTI-ÂNGULOS)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imagens_produto(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            caminho_imagem TEXT NOT NULL,
            ordem INTEGER DEFAULT 0,
            FOREIGN KEY(produto_id) REFERENCES produtos(id) ON DELETE CASCADE
        )
    """)

    # Tabela de LOJAS (Multi-Loja / SaaS)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lojas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            email TEXT,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Garante a existência da Loja Administradora Principal (Loja ID = 1)
    cursor.execute("SELECT COUNT(*) FROM lojas WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO lojas (id, nome, cnpj, email) VALUES (1, 'AstroControl Master', '00.000.000/0001-00', 'master@loja.com')"
        )
        conn.commit()

    # Migração segura para adicionar pai_id na tabela categorias caso ela não exista
    try:
        cursor.execute("ALTER TABLE categorias ADD COLUMN pai_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Cria a tabela de cupons promocionais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cupons(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            validade TEXT,
            limite_usos INTEGER,
            usos_atuais INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            loja_id INTEGER REFERENCES lojas(id) DEFAULT 1
        )
    """)
    conn.commit()

    # Migração segura para adicionar colunas de cupons na tabela vendas
    try:
        cursor.execute("ALTER TABLE vendas ADD COLUMN cupom_codigo TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE vendas ADD COLUMN desconto_cupom REAL DEFAULT 0.0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Migrações seguras para adicionar a coluna loja_id em todas as tabelas transacionais
    tabelas_loja = ["usuarios", "clientes", "categorias", "produtos", "vendas", "despesas", "empresa", "cupons"]
    for tab in tabelas_loja:
        try:
            cursor.execute(f"ALTER TABLE {tab} ADD COLUMN loja_id INTEGER REFERENCES lojas(id) DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        
        # Garante o isolamento dos dados antigos definindo a loja principal
        cursor.execute(f"UPDATE {tab} SET loja_id = 1 WHERE loja_id IS NULL")
        conn.commit()

    conn.close()

# Inicializa o banco ao rodar o projeto
criar_banco()


# 👑 CRIAR USUÁRIO MASTER AUTOMATICAMENTE
def criar_master():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE email = ?", ("master@loja.com",))
    master = cursor.fetchone()

    if not master:
        senha_hash = generate_password_hash("master@123")
        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha, cargo, primeiro_login, loja_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("Master", "master@loja.com", senha_hash, "master", 1, 1),
        )
        conn.commit()
    else:
        # Garante que o master principal pertence a loja 1
        cursor.execute("UPDATE usuarios SET loja_id = 1 WHERE email = ?", ("master@loja.com",))
        conn.commit()

    conn.close()

criar_master()


# 🔐 DECORADORES DE SEGURANÇA
def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def super_master_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect("/login")
        if session.get("cargo") != "master" or session.get("loja_id") != 1:
            flash("Acesso Negado: Apenas o administrador central do sistema pode acessar esta tela!", "danger")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return decorated_function

# Lista de todos os módulos disponíveis para permissões personalizadas
MODULOS_SISTEMA = {
    "dashboard": "Dashboard",
    "produtos": "Produtos (Catálogo)",
    "clientes": "Clientes",
    "vendas": "Vendas (Nova Venda)",
    "pdv": "PDV / Caixa",
    "usuarios": "Colaboradores",
    "despesas": "Despesas",
    "configuracao": "Configurações",
    "historico": "Histórico / Relatórios",
    "categorias": "Categorias de Produtos",
}

# Permissões fixas por cargo
PERMISSOES_CARGO = {
    "master": list(MODULOS_SISTEMA.keys()),
    "admin": ["dashboard", "produtos", "clientes", "vendas", "pdv", "usuarios", "historico", "categorias"],
    "vendedor": ["dashboard", "clientes", "vendas"],
    "caixa": ["dashboard", "vendas", "pdv"],
}

def tem_permissao(modulo):
    """Verifica se o usuário logado tem permissão para acessar um módulo."""
    cargo = session.get("cargo", "")
    if cargo == "personalizado":
        permissoes = session.get("permissoes", [])
        if isinstance(permissoes, str):
            try:
                permissoes = json.loads(permissoes)
            except Exception:
                permissoes = []
        return modulo in permissoes
    return modulo in PERMISSOES_CARGO.get(cargo, [])

def cargo_requerido(modulo):
    """Decorator que verifica permissão por módulo (aceita string ou lista para compatibilidade)."""
    # Suporte legado: se passado lista, converte para o primeiro módulo
    if isinstance(modulo, list):
        modulos = modulo
    else:
        modulos = [modulo]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect("/login")
            cargo = session.get("cargo", "")
            # Master tem acesso total sempre
            if cargo == "master":
                return f(*args, **kwargs)
            # Verifica se tem permissão em algum dos módulos requeridos
            has_access = False
            for m in modulos:
                if tem_permissao(m):
                    has_access = True
                    break
            if not has_access:
                flash("Acesso negado! Seu cargo não tem permissão para esta funcionalidade.", "danger")
                return redirect("/dashboard")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 🛡️ INTERCEPTOR PARA OBRIGAR ALTERAÇÃO DE SENHA NO PRIMEIRO LOGIN
@app.before_request
def verificar_primeiro_login():
    if request.endpoint in ["login", "logout", "static"] or not request.endpoint:
        return
    
    if session.get("usuario_id") and session.get("primeiro_login") == 1:
        if request.endpoint != "alterar_senha":
            flash("Você deve alterar sua senha temporária para acessar o sistema.", "warning")
            return redirect("/alterar-senha")


# 🔐 ROTA DE LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = sqlite3.connect("database/loja.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.id, u.nome, u.email, u.senha, u.cargo, u.primeiro_login, u.permissoes, u.loja_id
            FROM usuarios u
            JOIN lojas l ON u.loja_id = l.id
            WHERE u.email = ? AND u.ativo = 1 AND l.ativo = 1
            """,
            (email,),
        )
        usuario = cursor.fetchone()
        conn.close()

        if usuario and check_password_hash(usuario[3], senha):
            session["usuario_id"] = usuario[0]
            session["nome"] = usuario[1]
            session["cargo"] = usuario[4]
            session["primeiro_login"] = usuario[5]
            session["loja_id"] = usuario[7] or 1
            # Carrega permissões personalizadas (para cargo 'personalizado')
            if usuario[4] == "personalizado" and usuario[6]:
                session["permissoes"] = usuario[6]

            flash(f"Bem-vindo, {usuario[1]}!", "success")
            if usuario[5] == 1:
                return redirect("/alterar-senha")

            return redirect("/dashboard")

        flash("E-mail ou senha incorretos!", "danger")
        return redirect("/login")

    return render_template("login.html")


# 🔓 ROTA DE LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# 🔑 ROTAS DE RECUPERAÇÃO DE SENHA (ESQUECI A SENHA)
import random

@app.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        conn = sqlite3.connect("database/loja.db")
        cursor = conn.cursor()
        
        # Busca o usuário e a loja associada
        cursor.execute(
            """
            SELECT u.id, u.nome, u.cargo, u.loja_id, l.nome
            FROM usuarios u
            JOIN lojas l ON u.loja_id = l.id
            WHERE u.email = ? AND u.ativo = 1 AND l.ativo = 1
            """,
            (email,)
        )
        user = cursor.fetchone()
        conn.close()

        if not user:
            flash("Erro: E-mail não encontrado ou conta inativa!", "danger")
            return redirect("/esqueci-senha")

        u_id, u_nome, cargo, loja_id, loja_nome = user

        # Caso seja o Super Master (master@loja.com ou pertencente à loja administradora)
        if cargo == "master" and loja_id == 1:
            # Gera código de recuperação
            codigo = str(random.randint(100000, 999999))
            session["codigo_recuperacao"] = codigo
            session["email_recuperacao"] = email
            
            # Imprime no terminal de forma bem visível
            print("\n" + "="*80)
            print(f" [RECUPERAÇÃO SUPER MASTER] ".center(80, "*"))
            print(f"E-mail: {email}")
            print(f"Código de Redefinição: {codigo}")
            print("Insira este código de 6 dígitos no navegador para redefinir a sua senha.")
            print("="*80 + "\n")
            
            flash("Código de redefinição gerado com sucesso! Verifique o console/terminal onde o servidor Python está rodando para obter o código.", "success")
            return redirect("/esqueci-senha/confirmar")

        # Caso seja um Master de outra loja
        elif cargo == "master":
            msg = f"Acesso Master detectado para a loja '{loja_nome}'. Por favor, entre em contato com o Administrador Geral da plataforma (Super Master) para redefinir a sua senha."
            return render_template("esqueci_senha_msg.html", mensagem=msg, email=email)

        # Caso seja um colaborador comum de qualquer loja
        else:
            msg = f"Acesso de Colaborador detectado para a loja '{loja_nome}'. Por favor, entre em contato com o Master (Gerente/Dono) da sua loja para redefinir a sua senha no painel de colaboradores."
            return render_template("esqueci_senha_msg.html", mensagem=msg, email=email)

    return render_template("esqueci_senha.html")


@app.route("/esqueci-senha/confirmar", methods=["GET", "POST"])
def confirmar_recuperacao():
    email = session.get("email_recuperacao")
    codigo_salvo = session.get("codigo_recuperacao")

    if not email or not codigo_salvo:
        flash("Acesso inválido! Solicite a recuperação novamente.", "danger")
        return redirect("/esqueci-senha")

    if request.method == "POST":
        codigo_digitado = request.form.get("codigo", "").strip()

        if codigo_digitado == codigo_salvo:
            session["autorizado_nova_senha"] = True
            return redirect("/esqueci-senha/nova-senha")
        
        flash("Código de redefinição incorreto! Verifique o console do terminal.", "danger")

    return render_template("confirmar_recuperacao.html", email=email)


@app.route("/esqueci-senha/nova-senha", methods=["GET", "POST"])
def nova_senha_recuperacao():
    email = session.get("email_recuperacao")
    autorizado = session.get("autorizado_nova_senha")

    if not email or not autorizado:
        flash("Acesso não autorizado!", "danger")
        return redirect("/esqueci-senha")

    if request.method == "POST":
        nova_senha = request.form.get("senha")
        confirmar_senha = request.form.get("confirmar_senha")

        if nova_senha != confirmar_senha:
            flash("Erro: As senhas não conferem!", "danger")
            return redirect("/esqueci-senha/nova-senha")

        senha_hash = generate_password_hash(nova_senha)

        conn = sqlite3.connect("database/loja.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET senha = ?, primeiro_login = 0 WHERE email = ?", (senha_hash, email))
        conn.commit()
        conn.close()

        # Limpa sessão de recuperação
        session.pop("codigo_recuperacao", None)
        session.pop("email_recuperacao", None)
        session.pop("autorizado_nova_senha", None)

        flash("Senha redefinida com sucesso! Acesse sua conta com as novas credenciais.", "success")
        return redirect("/login")

    return render_template("nova_senha_recuperacao.html", email=email)


# 🏠 ROTA RAIZ
@app.route("/")
def home():
    if "usuario_id" in session:
        return redirect("/dashboard")
    return render_template("landing.html")


# 🚀 ROTA DE CADASTRO DE NOVA LOJA (SAAS AUTO-CADASTRO)
@app.route("/assinar", methods=["GET", "POST"])
def assinar():
    if "usuario_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":
        loja_nome = request.form.get("loja_nome", "").strip()
        loja_cnpj = request.form.get("loja_cnpj", "").strip()
        admin_nome = request.form.get("admin_nome", "").strip()
        admin_email = request.form.get("admin_email", "").strip().lower()
        admin_senha = request.form.get("admin_senha", "")

        if not (loja_nome and admin_nome and admin_email and admin_senha):
            flash("Por favor, preencha todos os campos obrigatórios.", "danger")
            return redirect("/assinar")

        conn = sqlite3.connect("database/loja.db")
        cursor = conn.cursor()

        # Verifica se o e-mail de admin já existe
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (admin_email,))
        if cursor.fetchone():
            conn.close()
            flash("Erro: Este e-mail de administrador já está cadastrado no sistema!", "danger")
            return redirect("/assinar")

        try:
            # 1. Cria a nova loja
            cursor.execute(
                "INSERT INTO lojas (nome, cnpj, email, ativo) VALUES (?, ?, ?, 1)",
                (loja_nome, loja_cnpj, admin_email)
            )
            loja_id = cursor.lastrowid

            # 2. Cria o usuário master administrador da nova loja
            from werkzeug.security import generate_password_hash
            senha_hash = generate_password_hash(admin_senha)
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha, cargo, primeiro_login, loja_id, permissoes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (admin_nome, admin_email, senha_hash, "master", 0, loja_id, "produtos,vendas,historico,clientes,despesas,configuracoes,pdv,usuarios")
            )
            usuario_id = cursor.lastrowid

            # 3. Cria as configurações padrão de empresa para a nova loja
            cursor.execute(
                """
                INSERT INTO empresa (id, nome, cnpj, email, loja_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (loja_id, loja_nome, loja_cnpj, admin_email, loja_id)
            )

            # 4. Cria categoria padrão 'DIVERSOS' para a nova loja
            cursor.execute(
                "INSERT INTO categorias (nome, criado_por, loja_id) VALUES (?, ?, ?)",
                ("DIVERSOS", "Sistema", loja_id)
            )

            conn.commit()

            # Efetua login automático na sessão
            session["usuario_id"] = usuario_id
            session["nome"] = admin_nome
            session["email"] = admin_email
            session["cargo"] = "master"
            session["loja_id"] = loja_id
            session["permissoes"] = "produtos,vendas,historico,clientes,despesas,configuracoes,pdv,usuarios"

            flash(f"Seja bem-vindo ao AstroControl! Sua loja '{loja_nome}' foi criada com sucesso.", "success")
            conn.close()
            return redirect("/dashboard")

        except Exception as e:
            conn.rollback()
            conn.close()
            flash(f"Erro ao criar conta: {str(e)}", "danger")
            return redirect("/assinar")

    return render_template("assinar.html")


# 📊 ROTA DO DASHBOARD (COM ALERTAS DE ESTOQUE E NOVAS MÉTRICAS)
@app.route("/dashboard")
@login_requerido
def dashboard():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    cursor.execute("SELECT COUNT(*) FROM produtos WHERE ativo = 1 AND loja_id = ?", (loja_id,))
    total_produtos = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT COUNT(*)
        FROM produtos
        WHERE estoque <= estoque_minimo AND ativo = 1 AND loja_id = ?
    """, (loja_id,))
    estoque_baixo = cursor.fetchone()[0] or 0

    valor_estoque = 0.0
    if session.get("cargo") == "master":
        cursor.execute("SELECT SUM(preco * estoque) FROM produtos WHERE ativo = 1 AND loja_id = ?", (loja_id,))
        valor_estoque = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COUNT(*) FROM vendas WHERE status = 'finalizada' AND loja_id = ?", (loja_id,))
    total_vendas = cursor.fetchone()[0] or 0

    # Busca a lista de produtos com estoque baixo para alertas
    cursor.execute("""
        SELECT id, nome, sku, marca, preco, estoque, estoque_minimo
        FROM produtos
        WHERE estoque <= estoque_minimo AND ativo = 1 AND loja_id = ?
        ORDER BY estoque ASC
    """, (loja_id,))
    produtos_estoque_baixo = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_produtos=total_produtos,
        estoque_baixo=estoque_baixo,
        valor_estoque=valor_estoque,
        total_vendas=total_vendas,
        produtos_estoque_baixo=produtos_estoque_baixo
    )

# 📦 ROTA DE LISTAGEM DE PRODUTOS
@app.route("/produtos")
@cargo_requerido(["produtos"])
def produtos():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    cursor.execute("""
        SELECT p.id, p.nome, p.sku, p.marca, p.preco, p.estoque, p.estoque_minimo,
               p.imagem, p.preco_custo, p.cadastrado_por,
               strftime('%d/%m/%Y %H:%M', p.data_criacao, 'localtime') as data_fmt,
               c.nome as categoria_nome, p.codigo_barras, c.pai_id, p_parent.nome as categoria_pai_nome
        FROM produtos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN categorias p_parent ON c.pai_id = p_parent.id
        WHERE p.ativo = 1 AND p.loja_id = ?
        ORDER BY p.id DESC
    """, (loja_id,))
    produtos_lista = cursor.fetchall()

    cursor.execute("""
        SELECT id, nome, pai_id FROM categorias 
        WHERE loja_id = ? 
        ORDER BY COALESCE(pai_id, id) ASC, pai_id IS NOT NULL ASC, nome ASC
    """, (loja_id,))
    categorias_lista = cursor.fetchall()

    conn.close()
    return render_template("produtos.html", produtos=produtos_lista, categorias=categorias_lista)


# ➕ ROTA DE CADASTRO DE PRODUTOS
@app.route("/cadastrar-produto", methods=["GET", "POST"])
@cargo_requerido(["produtos"])
def cadastrar_produto():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    
    cursor.execute("""
        SELECT id, nome, pai_id FROM categorias 
        WHERE loja_id = ? 
        ORDER BY COALESCE(pai_id, id) ASC, pai_id IS NOT NULL ASC, nome ASC
    """, (loja_id,))
    categorias_lista = cursor.fetchall()

    if request.method == "POST":
        nome = request.form["nome"]
        sku = request.form["sku"]
        codigo_barras = request.form["codigo_barras"]
        marca = request.form["marca"]
        descricao = request.form["descricao"]
        preco = float(request.form["preco"])
        preco_custo = float(request.form.get("preco_custo", 0.0) or 0.0)
        estoque = int(request.form["estoque"])
        estoque_minimo = int(request.form["estoque_minimo"])
        categoria_id = request.form.get("categoria_id") or None
        cadastrado_por = session.get("nome", "Sistema")

        # Valida se a categoria enviada realmente pertence à loja
        if categoria_id:
            cursor.execute("SELECT id FROM categorias WHERE id = ? AND loja_id = ?", (categoria_id, loja_id))
            if not cursor.fetchone():
                conn.close()
                flash("Erro: Categoria inválida!", "danger")
                return redirect("/produtos")

        imagens = request.files.getlist("imagens")
        nomes_imagens = []
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        for idx, img_file in enumerate(imagens):
            if img_file and img_file.filename != "":
                ext = os.path.splitext(img_file.filename)[1]
                safe_name = f"{sku}_{idx}_{secure_filename(img_file.filename)}"
                if len(safe_name) > 100:
                    safe_name = f"{sku}_{idx}{ext}"
                caminho = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                img_file.save(caminho)
                nomes_imagens.append(safe_name)

        capa_imagem = nomes_imagens[0] if nomes_imagens else None

        try:
            cursor.execute(
                """
                INSERT INTO produtos (
                    nome, sku, codigo_barras, marca,
                    descricao, preco, preco_custo, estoque, estoque_minimo, imagem,
                    cadastrado_por, categoria_id, loja_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (nome, sku, codigo_barras, marca, descricao, preco, preco_custo,
                 estoque, estoque_minimo, capa_imagem, cadastrado_por, categoria_id, loja_id),
            )
            prod_id = cursor.lastrowid
            for ordem, nome_img in enumerate(nomes_imagens):
                cursor.execute(
                    "INSERT INTO imagens_produto (produto_id, caminho_imagem, ordem) VALUES (?, ?, ?)",
                    (prod_id, nome_img, ordem)
                )
            cursor.execute(
                "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                (prod_id, "entrada", estoque)
            )
            conn.commit()
            flash("Produto cadastrado com sucesso!", "success")
        except sqlite3.IntegrityError:
            conn.close()
            flash("Erro: SKU ou Código de Barras já cadastrado!", "danger")
            return redirect("/produtos")

        conn.close()
        return redirect("/produtos")

    conn.close()
    return render_template("cadastrar_produto.html", categorias=categorias_lista)


# ✏️ ROTA DE EDIÇÃO DE PRODUTO
@app.route("/editar-produto/<int:id>", methods=["GET", "POST"])
@cargo_requerido(["produtos"])
def editar_produto(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Verifica se o produto pertence à loja logada
    cursor.execute("SELECT id FROM produtos WHERE id = ? AND loja_id = ?", (id, loja_id))
    if not cursor.fetchone():
        conn.close()
        flash("Erro: Acesso não autorizado!", "danger")
        return redirect("/produtos")

    if request.method == "POST":
        nome = request.form["nome"]
        sku = request.form["sku"]
        codigo_barras = request.form["codigo_barras"]
        marca = request.form["marca"]
        descricao = request.form["descricao"]
        preco = float(request.form["preco"])
        preco_custo = float(request.form.get("preco_custo", 0.0) or 0.0)
        estoque = int(request.form["estoque"])
        estoque_minimo = int(request.form["estoque_minimo"])
        categoria_id = request.form.get("categoria_id") or None

        # Valida categoria
        if categoria_id:
            cursor.execute("SELECT id FROM categorias WHERE id = ? AND loja_id = ?", (categoria_id, loja_id))
            if not cursor.fetchone():
                conn.close()
                flash("Erro: Categoria inválida!", "danger")
                return redirect("/produtos")

        # Identifica variação no estoque para log de movimentação
        cursor.execute("SELECT estoque FROM produtos WHERE id = ? AND loja_id = ?", (id, loja_id))
        estoque_anterior = cursor.fetchone()[0]

        # Salva novas imagens se houver
        novas_imagens = request.files.getlist("novas_imagens")
        
        # Conta imagens atuais
        cursor.execute("SELECT COUNT(*) FROM imagens_produto WHERE produto_id = ?", (id,))
        imagens_atuais_count = cursor.fetchone()[0] or 0

        # Filtra imagens válidas enviadas
        novas_imagens_validas = [f for f in novas_imagens if f and f.filename != ""]
        
        if imagens_atuais_count + len(novas_imagens_validas) > 10:
            conn.close()
            flash(f"Erro: O produto já possui {imagens_atuais_count} imagens. Limite máximo é de 10!", "danger")
            return redirect(f"/editar-produto/{id}")

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        nomes_novas_imagens = []
        for idx, img_file in enumerate(novas_imagens_validas):
            ext = os.path.splitext(img_file.filename)[1]
            safe_name = f"{sku}_add_{imagens_atuais_count + idx}_{secure_filename(img_file.filename)}"
            if len(safe_name) > 100:
                safe_name = f"{sku}_add_{imagens_atuais_count + idx}{ext}"
            
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
            img_file.save(caminho)
            nomes_novas_imagens.append(safe_name)

        # Insere novas imagens na tabela imagens_produto
        for idx, nome_img in enumerate(nomes_novas_imagens):
            ordem = imagens_atuais_count + idx
            cursor.execute(
                "INSERT INTO imagens_produto (produto_id, caminho_imagem, ordem) VALUES (?, ?, ?)",
                (id, nome_img, ordem)
            )

        # Atualiza a tabela produtos com a primeira imagem da galeria se ela estiver nula
        cursor.execute("SELECT caminho_imagem FROM imagens_produto WHERE produto_id = ? ORDER BY ordem LIMIT 1", (id,))
        row_capa = cursor.fetchone()
        capa_imagem = row_capa[0] if row_capa else None

        cursor.execute(
            """
            UPDATE produtos
            SET nome = ?, sku = ?, codigo_barras = ?,
                marca = ?, descricao = ?, preco = ?, preco_custo = ?,
                estoque = ?, estoque_minimo = ?, imagem = ?, categoria_id = ?
            WHERE id = ? AND loja_id = ?
            """,
            (nome, sku, codigo_barras, marca, descricao, preco, preco_custo, estoque, estoque_minimo, capa_imagem, categoria_id, id, loja_id),
        )
        
        diferenca_estoque = estoque - estoque_anterior
        if diferenca_estoque != 0:
            tipo_mov = "entrada" if diferenca_estoque > 0 else "saida"
            cursor.execute(
                "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                (id, tipo_mov, abs(diferenca_estoque))
            )
            
        conn.commit()
        conn.close()
        flash("Produto atualizado com sucesso!", "success")
        return redirect("/produtos")

    # GET Handler: Carrega informações do produto
    cursor.execute(
        """
        SELECT id, nome, sku, codigo_barras, marca,
               descricao, preco, preco_custo, estoque, estoque_minimo, categoria_id
        FROM produtos WHERE id = ? AND loja_id = ?
        """,
        (id, loja_id),
    )
    produto = cursor.fetchone()

    cursor.execute("SELECT id, caminho_imagem FROM imagens_produto WHERE produto_id = ? ORDER BY ordem", (id,))
    imagens = cursor.fetchall()

    cursor.execute("SELECT id, nome, pai_id FROM categorias WHERE loja_id = ? ORDER BY COALESCE(pai_id, id) ASC, pai_id IS NOT NULL ASC, nome ASC", (loja_id,))
    categorias_lista = cursor.fetchall()
    
    conn.close()
    return render_template("editar_produto.html", produto=produto, imagens=imagens, categorias=categorias_lista)


# ❌ DELETAR IMAGEM INDIVIDUAL DO PRODUTO (GALERIA)
@app.route("/deletar-imagem-produto/<int:img_id>")
@cargo_requerido(["produtos"])
def deletar_imagem_produto(img_id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Busca detalhes da imagem a ser deletada e confere se o produto pertence à loja
    cursor.execute(
        """
        SELECT ip.produto_id, ip.caminho_imagem 
        FROM imagens_produto ip
        JOIN produtos p ON ip.produto_id = p.id
        WHERE ip.id = ? AND p.loja_id = ?
        """, 
        (img_id, loja_id)
    )
    img_row = cursor.fetchone()
    
    if img_row:
        produto_id = img_row[0]
        caminho_imagem = img_row[1]

        # Deleta o registro do banco
        cursor.execute("DELETE FROM imagens_produto WHERE id = ?", (img_id,))
        
        # Apaga o arquivo físico do disco
        caminho_fisico = os.path.join(app.config["UPLOAD_FOLDER"], caminho_imagem)
        if os.path.exists(caminho_fisico):
            try:
                os.remove(caminho_fisico)
            except Exception as e:
                print(f"Erro ao deletar arquivo físico: {e}")

        # Busca a próxima imagem disponível para ser a nova capa
        cursor.execute("SELECT caminho_imagem FROM imagens_produto WHERE produto_id = ? ORDER BY ordem LIMIT 1", (produto_id,))
        row_capa = cursor.fetchone()
        nova_capa = row_capa[0] if row_capa else None

        # Atualiza a tabela produtos com a nova imagem de capa
        cursor.execute("UPDATE produtos SET imagem = ? WHERE id = ? AND loja_id = ?", (nova_capa, produto_id, loja_id))
        conn.commit()
        
        flash("Imagem removida da galeria com sucesso!", "success")
        conn.close()
        return redirect(f"/editar-produto/{produto_id}")

    conn.close()
    flash("Imagem não localizada ou sem permissão de acesso.", "danger")
    return redirect("/produtos")


# ❌ ROTA PARA EXCLUSÃO LÓGICA DE PRODUTO
@app.route("/excluir-produto/<int:id>")
@cargo_requerido(["produtos"])
def excluir_produto(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    cursor.execute("UPDATE produtos SET ativo = 0 WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()

    flash("Produto excluído do catálogo!", "success")
    return redirect("/produtos")


# 📦 ROTA PARA AÇÕES EM MASSA EM PRODUTOS
@app.route("/produtos/acoes-em-massa", methods=["POST"])
@cargo_requerido(["produtos"])
def acoes_em_massa_produtos():
    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao", "")
    
    if not ids_raw or not acao:
        flash("Nenhum produto selecionado ou ação inválida!", "warning")
        return redirect("/produtos")
        
    try:
        ids_lista = [int(x) for x in ids_raw.split(",") if x.strip()]
    except ValueError:
        flash("Lista de produtos inválida!", "danger")
        return redirect("/produtos")
        
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    
    try:
        loja_id = session.get("loja_id", 1)
        if acao == "excluir":
            # Exclusão lógica (ativo = 0) em massa
            # Adiciona loja_id na lista de parâmetros
            params = ids_lista + [loja_id]
            placeholders = ','.join(['?']*len(ids_lista))
            cursor.execute(
                f"UPDATE produtos SET ativo = 0 WHERE id IN ({placeholders}) AND loja_id = ?",
                params
            )
            flash(f"{len(ids_lista)} produto(s) excluído(s) com sucesso!", "success")
            
        elif acao == "preco":
            operacao = request.form.get("operacao_preco")
            valor = float(request.form.get("valor_preco", 0.0) or 0.0)
            
            for pid in ids_lista:
                if operacao == "somar_reais":
                    cursor.execute("UPDATE produtos SET preco = preco + ? WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
                elif operacao == "subtrair_reais":
                    cursor.execute("UPDATE produtos SET preco = MAX(0.0, preco - ?) WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
                elif operacao == "somar_porcentagem":
                    cursor.execute("UPDATE produtos SET preco = preco * (1.0 + ? / 100.0) WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
                elif operacao == "subtrair_porcentagem":
                    cursor.execute("UPDATE produtos SET preco = MAX(0.0, preco * (1.0 - ? / 100.0)) WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
                elif operacao == "definir_preco":
                    cursor.execute("UPDATE produtos SET preco = ? WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
            flash(f"Preço de {len(ids_lista)} produto(s) atualizado com sucesso!", "success")
            
        elif acao == "estoque":
            operacao = request.form.get("operacao_estoque")
            valor = int(request.form.get("valor_estoque", 0) or 0)
            
            for pid in ids_lista:
                # Busca estoque atual
                cursor.execute("SELECT estoque FROM produtos WHERE id = ? AND loja_id = ?", (pid, loja_id))
                row = cursor.fetchone()
                estoque_anterior = row[0] if row else 0
                
                if operacao == "adicionar_estoque":
                    if valor != 0:
                        tipo_mov = "entrada" if valor > 0 else "saida"
                        cursor.execute(
                            "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                            (pid, tipo_mov, abs(valor))
                        )
                        cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
                elif operacao == "definir_estoque":
                    diferenca = valor - estoque_anterior
                    if diferenca != 0:
                        tipo_mov = "entrada" if diferenca > 0 else "saida"
                        cursor.execute(
                            "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                            (pid, tipo_mov, abs(diferenca))
                        )
                        cursor.execute("UPDATE produtos SET estoque = ? WHERE id = ? AND loja_id = ?", (valor, pid, loja_id))
            flash(f"Estoque de {len(ids_lista)} produto(s) atualizado com sucesso!", "success")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"Erro ao processar alterações em massa: {str(e)}", "danger")
    finally:
        conn.close()
        
    return redirect("/produtos")


# 👥 CRUD DE CLIENTES

# Listar e Cadastrar Clientes
@app.route("/clientes", methods=["GET", "POST"])
@login_requerido
def clientes():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    if request.method == "POST":
        nome = request.form["nome"]
        tel = request.form["tel"]
        cpf = request.form["cpf"]
        email = request.form["email"]

        try:
            cursor.execute(
                """
                INSERT INTO clientes (nome, tel, cpf, email, loja_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nome, tel, cpf, email, loja_id),
            )
            conn.commit()
            flash("Cliente cadastrado com sucesso!", "success")
        except sqlite3.IntegrityError:
            flash("Erro: CPF já cadastrado!", "danger")

    # Filtra por busca caso haja parâmetro 'q'
    busca = request.args.get("q", "").strip()
    if busca:
        termo = f"%{busca}%"
        cursor.execute(
            """
            SELECT id, nome, tel, cpf, email 
            FROM clientes 
            WHERE ativo = 1 AND (nome LIKE ? OR cpf LIKE ? OR email LIKE ?) AND loja_id = ?
            ORDER BY nome
            """,
            (termo, termo, termo, loja_id)
        )
    else:
        cursor.execute("SELECT id, nome, tel, cpf, email FROM clientes WHERE ativo = 1 AND loja_id = ? ORDER BY nome", (loja_id,))
        
    clientes_lista = cursor.fetchall()
    conn.close()

    return render_template("clientes.html", clientes=clientes_lista, busca=busca)


# Editar Cliente
@app.route("/editar-cliente/<int:id>", methods=["GET", "POST"])
@login_requerido
def editar_cliente(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Verifica se o cliente pertence à loja logada
    cursor.execute("SELECT id FROM clientes WHERE id = ? AND loja_id = ?", (id, loja_id))
    if not cursor.fetchone():
        conn.close()
        flash("Erro: Acesso não autorizado!", "danger")
        return redirect("/clientes")

    if request.method == "POST":
        nome = request.form["nome"]
        tel = request.form["tel"]
        cpf = request.form["cpf"]
        email = request.form["email"]

        try:
            cursor.execute(
                """
                UPDATE clientes
                SET nome = ?, tel = ?, cpf = ?, email = ?
                WHERE id = ? AND loja_id = ?
                """,
                (nome, tel, cpf, email, id, loja_id),
            )
            conn.commit()
            flash("Dados do cliente atualizados!", "success")
            conn.close()
            return redirect("/clientes")
        except sqlite3.IntegrityError:
            flash("Erro: Este CPF pertence a outro cliente cadastrado!", "danger")

    cursor.execute("SELECT id, nome, tel, cpf, email FROM clientes WHERE id = ? AND loja_id = ?", (id, loja_id))
    cliente = cursor.fetchone()
    conn.close()

    return render_template("editar_cliente.html", cliente=cliente)


# Exclusão Lógica de Cliente
@app.route("/deletar-cliente/<int:id>")
@login_requerido
def deletar_cliente(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Verifica se o cliente pertence à loja logada
    cursor.execute("SELECT id FROM clientes WHERE id = ? AND loja_id = ?", (id, loja_id))
    if not cursor.fetchone():
        conn.close()
        flash("Erro: Acesso não autorizado!", "danger")
        return redirect("/clientes")

    cursor.execute("UPDATE clientes SET ativo = 0 WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()
    flash("Cliente arquivado com sucesso!", "success")
    return redirect("/clientes")


# 📦 AÇÕES EM MASSA PARA CLIENTES
@app.route("/clientes/acoes-em-massa", methods=["POST"])
@login_requerido
def acoes_em_massa_clientes():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao")

    if not ids_raw or not acao:
        conn.close()
        flash("Erro: Nenhum cliente selecionado ou ação inválida!", "danger")
        return redirect("/clientes")

    ids_lista = [int(x) for x in ids_raw.split(",") if x.isdigit()]

    if acao == "excluir":
        placeholders = ','.join(['?'] * len(ids_lista))
        params = ids_lista + [loja_id]
        cursor.execute(
            f"UPDATE clientes SET ativo = 0 WHERE id IN ({placeholders}) AND loja_id = ?",
            params
        )
        conn.commit()
        flash(f"{len(ids_lista)} cliente(s) arquivado(s) com sucesso!", "success")

    elif acao == "excluir_definitivo":
        placeholders = ','.join(['?'] * len(ids_lista))
        params = ids_lista + [loja_id]
        cursor.execute(
            f"DELETE FROM clientes WHERE id IN ({placeholders}) AND loja_id = ?",
            params
        )
        conn.commit()
        flash(f"{len(ids_lista)} cliente(s) excluído(s) definitivamente!", "success")

    conn.close()
    return redirect("/clientes")


# 🗑️ EXCLUSÃO FÍSICA INDIVIDUAL DE CLIENTE (DEFINITIVO)
@app.route("/clientes/excluir-definitivo/<int:id>")
@login_requerido
def excluir_cliente_definitivo(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Verifica se o cliente pertence à loja logada
    cursor.execute("SELECT id FROM clientes WHERE id = ? AND loja_id = ?", (id, loja_id))
    if not cursor.fetchone():
        conn.close()
        flash("Erro: Acesso não autorizado!", "danger")
        return redirect("/clientes")

    cursor.execute("DELETE FROM clientes WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()
    
    flash("Cliente excluído definitivamente do banco de dados!", "success")
    return redirect("/clientes")


# 💰 TELA DE VENDAS (REGISTRO DO VENDEDOR)
@app.route("/vendas")
@login_requerido
def vendas():
    return render_template("vendas.html")


# 💾 ROTA PARA PROCESSAR E FINALIZAR A VENDA (VENDEDOR & CAIXA)
@app.route("/finalizar-venda", methods=["POST"])
@login_requerido
def finalizar_venda():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    try:
        # Recebendo os dados comuns
        cliente_nome = request.form.get("cliente_nome")
        cliente_cpf = request.form.get("cliente_cpf")
        cliente_id = request.form.get("cliente_id")
        status = request.form.get("status", "aberta") # 'aberta' (vendedor) ou 'finalizada' (caixa) ou 'orcamento'
        
        # Dados de cupons promocionais
        cupom_codigo = request.form.get("cupom_codigo", "").strip().upper() or None
        desconto_cupom = float(request.form.get("desconto_cupom", 0.0) or 0.0)

        # Dados específicos do fechamento (caixa)
        venda_id_existente = request.form.get("venda_id") # Presente quando o caixa importa uma venda aberta
        forma_pagamento = request.form.get("forma_pagamento")
        vendedor_id = request.form.get("vendedor_id")
        
        # Produtos enviados
        produtos_ids = request.form.getlist("produto_id")
        quantidades = request.form.getlist("quantidade")

        # Dados de entrega
        entrega = int(request.form.get("entrega", 0))
        entrega_rua = request.form.get("entrega_rua") if entrega else None
        entrega_bairro = request.form.get("entrega_bairro") if entrega else None
        entrega_cep = request.form.get("entrega_cep") if entrega else None
        entrega_complemento = request.form.get("entrega_complemento") if entrega else None
        entrega_numero = request.form.get("entrega_numero") if entrega else None
        entrega_recebedor = request.form.get("entrega_recebedor") if entrega else None
        entrega_telefone = request.form.get("entrega_telefone") if entrega else None

        # Validação de CPF/Cliente no banco de dados (garantindo isolamento por loja_id)
        c_id = None
        if cliente_id and cliente_id.isdigit():
            cursor.execute("SELECT id FROM clientes WHERE id = ? AND loja_id = ? AND ativo = 1", (int(cliente_id), loja_id))
            row = cursor.fetchone()
            if row:
                c_id = row[0]
        elif cliente_cpf:
            cursor.execute("SELECT id FROM clientes WHERE cpf = ? AND loja_id = ? AND ativo = 1", (cliente_cpf, loja_id))
            row = cursor.fetchone()
            if row:
                c_id = row[0]

        total = 0.0
        comissao = 0.0

        # Se for fechamento de venda aberta/orçamento já existente no banco
        if venda_id_existente and venda_id_existente.isdigit():
            v_id = int(venda_id_existente)
            
            # Valida se a venda pertence à loja logada antes de processar
            cursor.execute("SELECT id, status FROM vendas WHERE id = ? AND loja_id = ?", (v_id, loja_id))
            venda_atual = cursor.fetchone()
            if not venda_atual:
                conn.close()
                flash("Erro: Venda não encontrada ou acesso não autorizado!", "danger")
                return redirect("/pdv")
            
            # Recupera os itens da venda aberta
            cursor.execute("SELECT produto_id, quantidade, preco_unitario FROM itens_venda WHERE venda_id = ?", (v_id,))
            itens = cursor.fetchall()
            
            # Valida estoque para todos os itens se estiver finalizando
            if status == "finalizada":
                for item in itens:
                    p_id, qtd, preco_unit = item
                    cursor.execute("SELECT nome, estoque FROM produtos WHERE id = ? AND loja_id = ?", (p_id, loja_id))
                    prod = cursor.fetchone()
                    
                    if not prod or prod[1] < qtd:
                        flash(f"Estoque insuficiente para o produto: {prod[0] if prod else 'Desconhecido'}", "danger")
                        conn.close()
                        return redirect("/pdv")
                        
                    total += (preco_unit * qtd)
            else:
                for item in itens:
                    p_id, qtd, preco_unit = item
                    total += (preco_unit * qtd)

            # Calcula comissão se houver vendedor selecionado (não nulo)
            if not vendedor_id:
                vendedor_id = None
            if vendedor_id:
                cursor.execute("SELECT comissao_percentual FROM usuarios WHERE id = ? AND loja_id = ? AND ativo = 1", (vendedor_id, loja_id))
                vendedor = cursor.fetchone()
                if vendedor and vendedor[0]:
                    comissao = total * (vendedor[0] / 100.0)

            # Aplica desconto do cupom
            total_liquido = max(0.0, total - desconto_cupom)

            # Atualiza a tabela vendas (atualiza status de aberta para finalizada, comissão e entrega)
            cursor.execute(
                """
                UPDATE vendas
                SET status = ?, total = ?, forma_pagamento = ?, vendedor_id = ?, caixa_id = ?,
                    comissao_paga = ?, entrega = ?, entrega_rua = ?, entrega_bairro = ?, entrega_cep = ?,
                    entrega_complemento = ?, entrega_numero = ?, entrega_recebedor = ?, entrega_telefone = ?,
                    cliente_id = ?, cupom_codigo = ?, desconto_cupom = ?
                WHERE id = ? AND loja_id = ?
                """,
                (
                    status, total_liquido, forma_pagamento, vendedor_id, session["usuario_id"], comissao,
                    entrega, entrega_rua, entrega_bairro, entrega_cep, entrega_complemento,
                    entrega_numero, entrega_recebedor, entrega_telefone, c_id, cupom_codigo, desconto_cupom,
                    v_id, loja_id
                )
            )

            # Se estiver de fato finalizando a venda agora, efetua a baixa do estoque
            if status == "finalizada":
                for item in itens:
                    p_id, qtd, _ = item
                    cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND loja_id = ?", (qtd, p_id, loja_id))
                    cursor.execute(
                        "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                        (p_id, "saida", qtd)
                    )
                # Registra o uso do cupom se houver
                if cupom_codigo:
                    cursor.execute("UPDATE cupons SET usos_atuais = usos_atuais + 1 WHERE codigo = ? AND loja_id = ?", (cupom_codigo, loja_id))

            conn.commit()
            
            if status == "orcamento":
                flash(f"Orçamento #{v_id} atualizado com sucesso!", "success")
                conn.close()
                return redirect("/vendas")
            else:
                flash(f"Venda #{v_id} finalizada com sucesso!", "success")
                conn.close()
                return redirect("/pdv")

        # Caso seja uma VENDA NOVA (Aberta pelo Vendedor ou Finalizada direto no PDV pelo Caixa)
        else:
            vid_final = vendedor_id if vendedor_id and str(vendedor_id).strip() else None
            
            # Valida vendedor
            if vid_final:
                cursor.execute("SELECT id FROM usuarios WHERE id = ? AND loja_id = ? AND ativo = 1", (vid_final, loja_id))
                if not cursor.fetchone():
                    conn.close()
                    flash("Erro: Vendedor inválido!", "danger")
                    return redirect("/pdv" if session["cargo"] == "caixa" else "/vendas")

            # 1. Cria a venda inicial com o cupom aplicado
            cursor.execute(
                """
                INSERT INTO vendas (
                    cliente_id, cliente_nome, cliente_cpf, total, forma_pagamento, 
                    vendedor_id, caixa_id, status, entrega, entrega_rua, entrega_bairro, 
                    entrega_cep, entrega_complemento, entrega_numero, entrega_recebedor, entrega_telefone,
                    loja_id, cupom_codigo, desconto_cupom
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c_id, cliente_nome, cliente_cpf, 0.0, forma_pagamento,
                    vid_final,
                    session["usuario_id"] if status == "finalizada" else None,
                    status, entrega, entrega_rua, entrega_bairro, entrega_cep,
                    entrega_complemento, entrega_numero, entrega_recebedor, entrega_telefone,
                    loja_id, cupom_codigo, desconto_cupom
                )
            )
            v_id = cursor.lastrowid

            # 2. Insere os itens
            for i in range(len(produtos_ids)):
                p_id = int(produtos_ids[i])
                qtd = int(quantidades[i])

                cursor.execute("SELECT nome, preco, estoque FROM produtos WHERE id = ? AND loja_id = ?", (p_id, loja_id))
                prod = cursor.fetchone()
                
                if not prod:
                    conn.rollback()
                    flash("Erro: Produto inválido!", "danger")
                    conn.close()
                    return redirect("/pdv" if session["cargo"] == "caixa" else "/vendas")
                
                nome_p = prod[0]
                preco_u = prod[1]
                estoque_atual = prod[2]

                # Se a venda está sendo finalizada de imediato, valida e decrementa o estoque
                if status == "finalizada":
                    if qtd > estoque_atual:
                        conn.rollback()
                        flash(f"Estoque insuficiente para o produto: {nome_p}", "danger")
                        conn.close()
                        return redirect("/pdv" if session["cargo"] == "caixa" else "/vendas")
                    
                    # Baixa do estoque
                    cursor.execute("UPDATE produtos SET estoque = ? WHERE id = ? AND loja_id = ?", (estoque_atual - qtd, p_id, loja_id))
                    cursor.execute(
                        "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                        (p_id, "saida", qtd)
                    )

                subtotal = preco_u * qtd
                total += subtotal

                # Salva os itens
                cursor.execute(
                    """
                    INSERT INTO itens_venda (venda_id, product_id, nome_produto, quantidade, preco_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """ if "product_id" in [c[1] for c in cursor.execute("PRAGMA table_info(itens_venda)").fetchall()] else
                    """
                    INSERT INTO itens_venda (venda_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (v_id, p_id, nome_p, qtd, preco_u, subtotal)
                )

            # 3. Calcula comissão (se houver vendedor selecionado)
            vendedor_id_real = vid_final
            if status == "finalizada" and vendedor_id_real:
                cursor.execute("SELECT comissao_percentual FROM usuarios WHERE id = ? AND loja_id = ? AND ativo = 1", (vendedor_id_real, loja_id))
                vendedor_row = cursor.fetchone()
                if vendedor_row and vendedor_row[0]:
                    comissao = total * (vendedor_row[0] / 100.0)

            # Aplica desconto do cupom no total final
            total_liquido = max(0.0, total - desconto_cupom)

            # 4. Atualiza o total e comissão da venda
            cursor.execute(
                "UPDATE vendas SET total = ?, comissao_paga = ? WHERE id = ? AND loja_id = ?",
                (total_liquido, comissao, v_id, loja_id)
            )

            # Se houver cupom e a venda foi de fato finalizada, incrementa usos
            if status == "finalizada" and cupom_codigo:
                cursor.execute("UPDATE cupons SET usos_atuais = usos_atuais + 1 WHERE codigo = ? AND loja_id = ?", (cupom_codigo, loja_id))

            conn.commit()
            
            if status == "aberta":
                flash(f"Venda registrada em aberto! ID: #{v_id}. Encaminhe o cliente ao caixa.", "success")
                conn.close()
                return redirect("/vendas")
            elif status == "orcamento":
                flash(f"Orçamento #{v_id} registrado com sucesso!", "success")
                conn.close()
                return redirect("/vendas")
            else:
                flash(f"Venda #{v_id} registrada e finalizada!", "success")
                conn.close()
                return redirect("/pdv")

    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f"Erro ao processar venda: {str(e)}", "danger")
        return redirect("/dashboard")


# 🖥️ ROTA DA TELA DO PONTO DE VENDA (PDV)
@app.route("/pdv")
@cargo_requerido(["pdv"])
def pdv():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    # Puxa apenas os colaboradores ativos que são vendedores
    cursor.execute("""
        SELECT id, nome FROM usuarios
        WHERE cargo = 'vendedor' AND ativo = 1 AND loja_id = ?
        ORDER BY nome
    """, (loja_id,))
    vendedores = cursor.fetchall()
    conn.close()
    return render_template("pdv.html", vendedores=vendedores)


# 🔍 ROTA API PARA BUSCAR PRODUTOS DINAMICAMENTE NO PDV E NO CARRINHO
@app.route("/buscar-produto/<codigo>")
@login_requerido
def buscar_produto(codigo):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    # Retorna todos os produtos (wildcard ou busca por texto parcial no nome)
    if codigo == "*" or len(codigo) >= 2:
        termo = f"%{codigo}%" if codigo != "*" else "%"
        loja_id = session.get("loja_id", 1)
        cursor.execute("""
            SELECT id, nome, sku, preco, estoque, codigo_barras, imagem
            FROM produtos
            WHERE (nome LIKE ? OR sku LIKE ? OR codigo_barras LIKE ?) AND ativo = 1 AND loja_id = ?
            ORDER BY nome
            LIMIT 20
        """, (termo, termo, termo, loja_id))
        produtos = cursor.fetchall()
        conn.close()
        lista_retorno = []
        for p in produtos:
            lista_retorno.append({
                "id": p[0],
                "nome": p[1],
                "sku": p[2],
                "preco": p[3],
                "estoque": p[4],
                "codigo_barras": p[5],
                "imagem": p[6]
            })
        return jsonify(lista_retorno)

    # Busca exata por código único (SKU, barras ou ID)
    loja_id = session.get("loja_id", 1)
    cursor.execute(
        """
        SELECT id, nome, preco, estoque, sku, codigo_barras, imagem
        FROM produtos
        WHERE (sku = ? OR codigo_barras = ? OR CAST(id AS TEXT) = ?) AND ativo = 1 AND loja_id = ?
        """,
        (codigo, codigo, codigo, loja_id),
    )
    produto = cursor.fetchone()
    conn.close()

    if produto:
        return jsonify([
            {
                "id": produto[0],
                "nome": produto[1],
                "preco": produto[2],
                "estoque": produto[3],
                "sku": produto[4],
                "codigo_barras": produto[5],
                "imagem": produto[6]
            }
        ])

    return jsonify([])


# 🔍 ROTA API PARA BUSCAR CLIENTE POR CPF
@app.route("/buscar-cliente/<cpf>")
@login_requerido
def buscar_cliente(cpf):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    cursor.execute("SELECT id, nome, tel, cpf, email FROM clientes WHERE cpf = ? AND ativo = 1 AND loja_id = ?", (cpf, loja_id))
    cliente = cursor.fetchone()
    conn.close()

    if cliente:
        return {
            "id": cliente[0],
            "nome": cliente[1],
            "tel": cliente[2],
            "cpf": cliente[3],
            "email": cliente[4]
        }
    return {"erro": "Cliente não cadastrado"}


# 🔍 ROTA API PARA LISTAR VENDAS EM ABERTO
@app.route("/vendas-abertas")
@cargo_requerido(["pdv"])
def vendas_abertas():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    cursor.execute(
        """
        SELECT id, cliente_nome, cliente_cpf, total, status
        FROM vendas
        WHERE status IN ('aberta', 'orcamento') AND loja_id = ?
        ORDER BY id DESC
        """,
        (loja_id,)
    )
    abertas = cursor.fetchall()
    conn.close()

    resultado = []
    for v in abertas:
        resultado.append({
            "id": v[0],
            "cliente_nome": v[1] or "Consumidor",
            "cliente_cpf": v[2] or "",
            "total": v[3],
            "status": v[4]
        })
    return jsonify(resultado)


# 🔍 API PARA CARREGAR OS ITENS DE UMA VENDA EM ABERTO ESPECÍFICA
@app.route("/carregar-venda-aberta/<int:id>")
@cargo_requerido(["pdv"])
def carregar_venda_aberta(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    
    # 1. Detalhes da venda
    cursor.execute(
        """
        SELECT id, cliente_id, cliente_nome, cliente_cpf, vendedor_id, total
        FROM vendas WHERE id = ? AND status = 'aberta' AND loja_id = ?
        """,
        (id, loja_id)
    )
    venda = cursor.fetchone()
    
    if not venda:
        conn.close()
        return {"erro": "Venda em aberto não localizada."}
        
    # 2. Itens da venda
    cursor.execute(
        """
        SELECT iv.produto_id, iv.nome_produto, iv.quantidade, iv.preco_unitario, p.sku, p.estoque
        FROM itens_venda iv
        JOIN produtos p ON iv.produto_id = p.id
        WHERE iv.venda_id = ? AND p.loja_id = ?
        """,
        (id, loja_id)
    )
    itens = cursor.fetchall()
    conn.close()
    
    lista_itens = []
    for item in itens:
        lista_itens.append({
            "produto_id": item[0],
            "nome_produto": item[1],
            "quantidade": item[2],
            "preco_unitario": item[3],
            "sku": item[4],
            "estoque": item[5]
        })
        
    return {
        "venda_id": venda[0],
        "cliente_id": venda[1],
        "cliente_nome": venda[2] or "Consumidor",
        "cliente_cpf": venda[3] or "",
        "vendedor_id": venda[4],
        "total": venda[5],
        "itens": lista_itens
    }


# 👥 GERENCIAMENTO DE USUÁRIOS
@app.route("/usuarios", methods=["GET", "POST"])
@cargo_requerido(["usuarios"])
def usuarios():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha_criptografada = generate_password_hash(request.form["senha"])
        cargo = request.form["cargo"]
        comissao = float(request.form.get("comissao_percentual", 0.0) or 0.0)
        # Para cargo personalizado, salva as permissões como JSON
        permissoes = None
        if cargo == "personalizado":
            modulos_selecionados = request.form.getlist("permissoes")
            permissoes = json.dumps(modulos_selecionados)

        try:
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha, cargo, comissao_percentual, primeiro_login, permissoes, loja_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (nome, email, senha_criptografada, cargo, comissao, 1, permissoes, session.get("loja_id", 1)),
            )
            conn.commit()
            flash("Colaborador cadastrado!", "success")
        except sqlite3.IntegrityError:
            flash("Erro: E-mail já cadastrado!", "danger")

    cargo_atual = session.get("cargo")
    loja_id = session.get("loja_id", 1)
    cursor.execute(
        """
        SELECT id, nome, email, cargo, ativo, comissao_percentual 
        FROM usuarios 
        WHERE ativo = 1 AND (cargo != 'master' OR ? = 'master') AND loja_id = ?
        ORDER BY nome
        """,
        (cargo_atual, loja_id),
    )
    usuarios_ativos = cursor.fetchall()
    
    cursor.execute(
        """
        SELECT id, nome, email, cargo, ativo, comissao_percentual 
        FROM usuarios 
        WHERE ativo = 0 AND (cargo != 'master' OR ? = 'master') AND loja_id = ?
        ORDER BY nome
        """,
        (cargo_atual, loja_id),
    )
    usuarios_inativos = cursor.fetchall()
    
    cursor.execute("SELECT dominio FROM empresa WHERE id = 1")
    row_dom = cursor.fetchone()
    dominio_empresa = row_dom[0] if (row_dom and row_dom[0]) else "loja.com"
    
    conn.close()
    return render_template(
        "usuarios.html",
        usuarios=usuarios_ativos,
        usuarios_inativos=usuarios_inativos,
        dominio_empresa=dominio_empresa,
        modulos=MODULOS_SISTEMA
    )


# ✏️ EDITAR COLABORADOR
@app.route("/editar-usuario/<int:id>", methods=["GET", "POST"])
@cargo_requerido(["usuarios"])
def editar_usuario(id):
    # Proteção da conta Master contra edições por outros cargos e segurança multi-loja
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (id,))
    row_user = cursor.fetchone()
    conn.close()
    
    loja_id = session.get("loja_id", 1)
    if row_user:
        # Se tentar gerenciar usuário de outra loja, bloqueia
        if row_user[1] != loja_id:
            flash("Erro de Seguranca: Operacao nao permitida!", "danger")
            return redirect("/usuarios")
        if row_user[0] == "master" and session.get("cargo") != "master":
            flash("Erro de Permissao: Apenas administradores Master podem gerenciar a conta Master!", "danger")
            return redirect("/usuarios")

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        cargo = request.form["cargo"]
        comissao = float(request.form.get("comissao_percentual", 0.0) or 0.0)
        permissoes = None
        if cargo == "personalizado":
            modulos_selecionados = request.form.getlist("permissoes")
            permissoes = json.dumps(modulos_selecionados)

        cursor.execute(
            """
            UPDATE usuarios 
            SET nome = ?, email = ?, cargo = ?, comissao_percentual = ?, permissoes = ?
            WHERE id = ? AND loja_id = ?
            """,
            (nome, email, cargo, comissao, permissoes, id, session.get("loja_id", 1)),
        )
        conn.commit()
        conn.close()
        flash("Colaborador atualizado com sucesso!", "success")
        return redirect("/usuarios")

    cursor.execute("SELECT id, nome, email, cargo, comissao_percentual, permissoes FROM usuarios WHERE id = ? AND loja_id = ?", (id, session.get("loja_id", 1)))
    usuario = cursor.fetchone()
    conn.close()

    # Parse das permissões para exibir checkboxes marcados
    permissoes_usuario = []
    if usuario and usuario[5]:
        try:
            permissoes_usuario = json.loads(usuario[5])
        except Exception:
            permissoes_usuario = []

    return render_template("editar_usuario.html", usuario=usuario, modulos=MODULOS_SISTEMA, permissoes_usuario=permissoes_usuario)


# ❌ DESATIVAR COLABORADOR
@app.route("/desativar-usuario/<int:id>")
@cargo_requerido(["usuarios"])
def desativar_usuario(id):
    # Proteção da conta Master contra edições por outros cargos e segurança multi-loja
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (id,))
    row_user = cursor.fetchone()
    conn.close()
    
    loja_id = session.get("loja_id", 1)
    if row_user:
        # Se tentar gerenciar usuário de outra loja, bloqueia
        if row_user[1] != loja_id:
            flash("Erro de Seguranca: Operacao nao permitida!", "danger")
            return redirect("/usuarios")
        if row_user[0] == "master" and session.get("cargo") != "master":
            flash("Erro de Permissao: Apenas administradores Master podem gerenciar a conta Master!", "danger")
            return redirect("/usuarios")

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET ativo = 0 WHERE id = ? AND loja_id = ?", (id, session.get("loja_id", 1)))
    conn.commit()
    conn.close()
    
    flash("Colaborador desativado no sistema!", "success")
    return redirect("/usuarios")


# 🔄 REATIVAR COLABORADOR
@app.route("/reativar-usuario/<int:id>")
@cargo_requerido(["usuarios"])
def reativar_usuario(id):
    # Proteção da conta Master contra edições por outros cargos e segurança multi-loja
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (id,))
    row_user = cursor.fetchone()
    conn.close()
    
    loja_id = session.get("loja_id", 1)
    if row_user:
        # Se tentar gerenciar usuário de outra loja, bloqueia
        if row_user[1] != loja_id:
            flash("Erro de Seguranca: Operacao nao permitida!", "danger")
            return redirect("/usuarios")
        if row_user[0] == "master" and session.get("cargo") != "master":
            flash("Erro de Permissao: Apenas administradores Master podem gerenciar a conta Master!", "danger")
            return redirect("/usuarios")

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET ativo = 1 WHERE id = ? AND loja_id = ?", (id, session.get("loja_id", 1)))
    conn.commit()
    conn.close()
    
    flash("Colaborador reativado no sistema!", "success")
    return redirect("/usuarios")


# 🗑️ EXCLUIR COLABORADOR DE VEZ (DEFINITIVO)
@app.route("/excluir-usuario/<int:id>")
@cargo_requerido(["usuarios"])
def excluir_usuario(id):
    loja_id = session.get("loja_id", 1)
    usuario_logado_id = session.get("usuario_id")
    cargo_atual = session.get("cargo")

    if id == usuario_logado_id:
        flash("Erro: Você não pode excluir a sua própria conta!", "danger")
        return redirect("/usuarios")

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (id,))
    row_user = cursor.fetchone()

    if row_user:
        u_cargo, u_loja = row_user
        if u_loja != loja_id:
            conn.close()
            flash("Erro de Segurança: Operação não permitida!", "danger")
            return redirect("/usuarios")
        if u_cargo == "master" and cargo_atual != "master":
            conn.close()
            flash("Erro de Permissão: Apenas administradores Master podem gerenciar a conta Master!", "danger")
            return redirect("/usuarios")

        cursor.execute("DELETE FROM usuarios WHERE id = ? AND loja_id = ?", (id, loja_id))
        conn.commit()
        flash("Colaborador excluído definitivamente do sistema!", "success")
    else:
        flash("Erro: Colaborador não encontrado!", "danger")
        
    conn.close()
    return redirect("/usuarios")


# 📦 AÇÕES EM MASSA PARA COLABORADORES
@app.route("/usuarios/acoes-em-massa", methods=["POST"])
@cargo_requerido(["usuarios"])
def acoes_em_massa_usuarios():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    usuario_logado_id = session.get("usuario_id")
    cargo_atual = session.get("cargo")

    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao")

    if not ids_raw or not acao:
        conn.close()
        flash("Erro: Nenhum colaborador selecionado ou ação inválida!", "danger")
        return redirect("/usuarios")

    ids_lista = [int(x) for x in ids_raw.split(",") if x.isdigit()]

    if acao == "excluir_definitivo":
        excluidos_cont = 0
        for uid in ids_lista:
            if uid == usuario_logado_id:
                continue
            cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (uid,))
            row = cursor.fetchone()
            if row:
                u_cargo, u_loja = row
                if u_loja == loja_id:
                    if u_cargo == "master" and cargo_atual != "master":
                        continue
                    cursor.execute("DELETE FROM usuarios WHERE id = ? AND loja_id = ?", (uid, loja_id))
                    excluidos_cont += 1
        conn.commit()
        flash(f"{excluidos_cont} colaborador(es) excluído(s) permanentemente!", "success")

    elif acao == "desativar":
        alterados_cont = 0
        for uid in ids_lista:
            if uid == usuario_logado_id:
                continue
            cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (uid,))
            row = cursor.fetchone()
            if row:
                u_cargo, u_loja = row
                if u_loja == loja_id:
                    if u_cargo == "master" and cargo_atual != "master":
                        continue
                    cursor.execute("UPDATE usuarios SET ativo = 0 WHERE id = ? AND loja_id = ?", (uid, loja_id))
                    alterados_cont += 1
        conn.commit()
        flash(f"{alterados_cont} colaborador(es) desativado(s) com sucesso!", "success")

    elif acao == "restaurar":
        alterados_cont = 0
        for uid in ids_lista:
            cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (uid,))
            row = cursor.fetchone()
            if row:
                u_cargo, u_loja = row
                if u_loja == loja_id:
                    if u_cargo == "master" and cargo_atual != "master":
                        continue
                    cursor.execute("UPDATE usuarios SET ativo = 1 WHERE id = ? AND loja_id = ?", (uid, loja_id))
                    alterados_cont += 1
        conn.commit()
        flash(f"{alterados_cont} colaborador(es) reativado(s) com sucesso!", "success")

    elif acao == "cargo":
        novo_cargo = request.form.get("operacao_cargo")
        nova_comissao = float(request.form.get("valor_comissao", 0.0) or 0.0)
        
        alterados_cont = 0
        for uid in ids_lista:
            if uid == usuario_logado_id:
                continue
            cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (uid,))
            row = cursor.fetchone()
            if row:
                u_cargo, u_loja = row
                if u_loja == loja_id:
                    if u_cargo == "master" and cargo_atual != "master":
                        continue
                    if u_cargo == "master":
                        continue
                    
                    comissao_final = nova_comissao if novo_cargo == "vendedor" else 0.0
                    cursor.execute("UPDATE usuarios SET cargo = ?, comissao_percentual = ? WHERE id = ? AND loja_id = ?", (novo_cargo, comissao_final, uid, loja_id))
                    alterados_cont += 1
        conn.commit()
        flash(f"Cargo e comissão de {alterados_cont} colaborador(es) atualizado(s) em lote!", "success")

    conn.close()
    return redirect("/usuarios")


# 🔑 RESETAR SENHA DO COLABORADOR (FORÇADO POR MASTER/ADMIN)
@app.route("/resetar-senha-colaborador/<int:id>", methods=["POST"])
@cargo_requerido(["usuarios"])
def resetar_senha_colaborador(id):
    # Proteção da conta Master contra edições por outros cargos e segurança multi-loja
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cargo, loja_id FROM usuarios WHERE id = ?", (id,))
    row_user = cursor.fetchone()
    conn.close()
    
    loja_id = session.get("loja_id", 1)
    if row_user:
        # Se tentar gerenciar usuário de outra loja, bloqueia
        if row_user[1] != loja_id:
            flash("Erro de Seguranca: Operacao nao permitida!", "danger")
            return redirect("/usuarios")
        if row_user[0] == "master" and session.get("cargo") != "master":
            flash("Erro de Permissao: Apenas administradores Master podem gerenciar a conta Master!", "danger")
            return redirect("/usuarios")

    nova_senha_crua = request.form.get("nova_senha")
    if not nova_senha_crua:
        flash("Erro: Informe a nova senha temporária!", "danger")
        return redirect("/usuarios")
        
    senha_criptografada = generate_password_hash(nova_senha_crua)
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    # Seta primeiro_login = 1 para que ele seja obrigado a trocar a senha ao entrar!
    cursor.execute(
        "UPDATE usuarios SET senha = ?, primeiro_login = 1 WHERE id = ? AND loja_id = ?",
        (senha_criptografada, id, session.get("loja_id", 1)),
    )
    conn.commit()
    conn.close()
    
    flash("Senha redefinida com sucesso! O colaborador deverá alterá-la no próximo acesso.", "success")
    return redirect("/usuarios")


# 🔄 ALTERAÇÃO DE SENHA OBRIGATÓRIA
@app.route("/alterar-senha", methods=["GET", "POST"])
@login_requerido
def alterar_senha():
    if request.method == "POST":
        nova_senha = generate_password_hash(request.form["senha"])

        conn = sqlite3.connect("database/loja.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET senha = ?, primeiro_login = 0 WHERE id = ?",
            (nova_senha, session["usuario_id"]),
        )
        conn.commit()
        conn.close()

        # Atualiza a sessão
        session["primeiro_login"] = 0
        flash("Senha alterada com sucesso! Bem-vindo.", "success")
        return redirect("/dashboard")

    return render_template("alterar_senha.html")


# 📈 ROTA DE HISTÓRICO DE VENDAS E RELATÓRIOS
@app.route("/historico")
@cargo_requerido(["historico"])
def historico():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    loja_id = session.get("loja_id", 1)
    # 1. Métricas de faturamento (usando date/time local do SQLite)
    cursor.execute("""
        SELECT SUM(total) FROM vendas 
        WHERE status = 'finalizada' AND date(data, 'localtime') = date('now', 'localtime') AND loja_id = ?
    """, (loja_id,))
    faturamento_dia = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT SUM(total) FROM vendas 
        WHERE status = 'finalizada' AND date(data, 'localtime') >= date('now', '-7 days', 'localtime') AND loja_id = ?
    """, (loja_id,))
    faturamento_semana = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT SUM(total) FROM vendas 
        WHERE status = 'finalizada' AND strftime('%Y-%m', data, 'localtime') = strftime('%Y-%m', 'now', 'localtime') AND loja_id = ?
    """, (loja_id,))
    faturamento_mes = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT SUM(total) FROM vendas 
        WHERE status = 'finalizada' AND strftime('%Y', data, 'localtime') = strftime('%Y', 'now', 'localtime') AND loja_id = ?
    """, (loja_id,))
    faturamento_ano = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(total) FROM vendas WHERE status = 'finalizada' AND loja_id = ?", (loja_id,))
    faturamento_total = cursor.fetchone()[0] or 0.0

    # 2. Custo de Mercadorias (CMV)
    # Soma de (itens_venda.quantidade * produtos.preco_custo) de todas as vendas finalizadas
    cursor.execute("""
        SELECT SUM(iv.quantidade * p.preco_custo)
        FROM itens_venda iv
        JOIN vendas v ON iv.venda_id = v.id
        JOIN produtos p ON iv.produto_id = p.id
        WHERE v.status = 'finalizada' AND v.loja_id = ?
    """, (loja_id,))
    custo_mercadorias = cursor.fetchone()[0] or 0.0

    # 3. Despesas Operacionais Totais
    cursor.execute("SELECT SUM(valor) FROM despesas WHERE loja_id = ?", (loja_id,))
    despesas_totais = cursor.fetchone()[0] or 0.0

    # 4. Lucro Líquido Real
    lucro_liquido = faturamento_total - custo_mercadorias - despesas_totais

    # 5. Dados para o gráfico de Faturamento Diário (últimos 15 dias)
    cursor.execute("""
        SELECT date(data, 'localtime') as dia, SUM(total)
        FROM vendas
        WHERE status = 'finalizada' AND date(data, 'localtime') >= date('now', '-15 days', 'localtime') AND loja_id = ?
        GROUP BY dia
        ORDER BY dia ASC
    """, (loja_id,))
    grafico_dia_cru = cursor.fetchall()
    faturamento_grafico = []
    for dia, valor in grafico_dia_cru:
        partes = dia.split("-")
        dia_formatado = f"{partes[2]}/{partes[1]}"
        faturamento_grafico.append({"dia": dia_formatado, "total": valor})

    # 6. Dados para o gráfico de Meios de Pagamento
    cursor.execute("""
        SELECT forma_pagamento, SUM(total)
        FROM vendas
        WHERE status = 'finalizada' AND loja_id = ?
        GROUP BY forma_pagamento
    """, (loja_id,))
    grafico_pag_cru = cursor.fetchall()
    pagamento_grafico = []
    for forma, valor in grafico_pag_cru:
        pagamento_grafico.append({"forma": forma or "Indefinido", "total": valor})

    # 7. Ranking de Vendedores
    cursor.execute("""
        SELECT u.nome, SUM(v.total) as total_vendas, COUNT(v.id) as qtd_vendas, SUM(v.comissao_paga) as comissao_total
        FROM vendas v
        JOIN usuarios u ON v.vendedor_id = u.id
        WHERE v.status = 'finalizada' AND v.loja_id = ?
        GROUP BY u.id
        ORDER BY total_vendas DESC
    """, (loja_id,))
    ranking_cru = cursor.fetchall()
    
    max_faturamento_vendedor = max([v[1] for v in ranking_cru]) if ranking_cru else 1.0
    ranking_vendedores = []
    for r in ranking_cru:
        perc = (r[1] / max_faturamento_vendedor) * 100.0
        ranking_vendedores.append((r[0], r[1], r[2], r[3], perc))

    # 8. Ranking de Produtos mais vendidos
    cursor.execute("""
        SELECT iv.nome_produto, SUM(iv.quantidade) as total_qtd, SUM(iv.subtotal) as total_revenue
        FROM itens_venda iv
        JOIN vendas v ON iv.venda_id = v.id
        WHERE v.status = 'finalizada' AND v.loja_id = ?
        GROUP BY iv.produto_id
        ORDER BY total_qtd DESC
        LIMIT 10
    """, (loja_id,))
    produtos_cru = cursor.fetchall()
    max_qtd_prod = max([p[1] for p in produtos_cru]) if produtos_cru else 1
    produtos_mais_vendidos = []
    for p in produtos_cru:
        perc = (p[1] / max_qtd_prod) * 100.0
        produtos_mais_vendidos.append((p[0], p[1], p[2], perc))

    # 9. Histórico detalhado de vendas finalizadas
    cursor.execute("""
        SELECT 
            v.id, v.cliente_nome, v.cliente_cpf, 
            u.nome as vendedor_nome, c.nome as caixa_nome,
            v.forma_pagamento, v.entrega, v.total, 
            strftime('%d/%m/%Y %H:%M', v.data, 'localtime') as data_formatada,
            v.entrega_recebedor, v.entrega_telefone,
            v.entrega_rua, v.entrega_numero, v.entrega_bairro,
            v.entrega_cep, v.entrega_complemento, v.comissao_paga, v.vendedor_id
        FROM vendas v
        LEFT JOIN usuarios u ON v.vendedor_id = u.id
        LEFT JOIN usuarios c ON v.caixa_id = c.id
        WHERE v.status = 'finalizada' AND v.loja_id = ?
        ORDER BY v.id DESC
    """, (loja_id,))
    vendas_lista = cursor.fetchall()

    vendas_com_itens = []
    for v in vendas_lista:
        cursor.execute("""
            SELECT iv.nome_produto, iv.quantidade, iv.preco_unitario, iv.subtotal, p.imagem 
            FROM itens_venda iv
            LEFT JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = ?
        """, (v[0],))
        itens = cursor.fetchall()
        
        v_lista = list(v)
        v_lista.append(itens)
        vendas_com_itens.append(v_lista)

    # 9.1. Histórico de Orçamentos
    cursor.execute("""
        SELECT 
            v.id, v.cliente_nome, v.cliente_cpf, 
            u.nome as vendedor_nome, c.nome as caixa_nome,
            v.forma_pagamento, v.entrega, v.total, 
            strftime('%d/%m/%Y %H:%M', v.data, 'localtime') as data_formatada,
            v.entrega_recebedor, v.entrega_telefone,
            v.entrega_rua, v.entrega_numero, v.entrega_bairro,
            v.entrega_cep, v.entrega_complemento, v.comissao_paga, v.vendedor_id
        FROM vendas v
        LEFT JOIN usuarios u ON v.vendedor_id = u.id
        LEFT JOIN usuarios c ON v.caixa_id = c.id
        WHERE v.status = 'orcamento' AND v.loja_id = ?
        ORDER BY v.id DESC
    """, (loja_id,))
    orcamentos_lista = cursor.fetchall()

    orcamentos_com_itens = []
    for v in orcamentos_lista:
        cursor.execute("""
            SELECT iv.nome_produto, iv.quantidade, iv.preco_unitario, iv.subtotal, p.imagem 
            FROM itens_venda iv
            LEFT JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = ?
        """, (v[0],))
        itens = cursor.fetchall()
        
        v_lista = list(v)
        v_lista.append(itens)
        orcamentos_com_itens.append(v_lista)

    cursor.execute("SELECT id, nome FROM usuarios WHERE cargo = 'vendedor' AND ativo = 1 AND loja_id = ?", (loja_id,))
    vendedores_ativos = cursor.fetchall()
    conn.close()

    return render_template(
        "historico.html",
        faturamento_dia=faturamento_dia,
        faturamento_semana=faturamento_semana,
        faturamento_mes=faturamento_mes,
        faturamento_ano=faturamento_ano,
        faturamento_total=faturamento_total,
        custo_mercadorias=custo_mercadorias,
        despesas_totais=despesas_totais,
        lucro_liquido=lucro_liquido,
        faturamento_grafico=faturamento_grafico,
        pagamento_grafico=pagamento_grafico,
        ranking_vendedores=ranking_vendedores,
        produtos_mais_vendidos=produtos_mais_vendidos,
        lista_vendas=vendas_com_itens,
        lista_orcamentos=orcamentos_com_itens,
        vendedores=vendedores_ativos
    )


# 🗑️ ROTA PARA EXCLUIR VENDA (DEVOLVENDO PRODUTOS AO ESTOQUE)
@app.route("/vendas/excluir/<int:id>")
@login_requerido
def excluir_venda(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Busca a venda para verificar se pertence à mesma loja
    cursor.execute("SELECT status, total FROM vendas WHERE id = ? AND loja_id = ?", (id, loja_id))
    venda = cursor.fetchone()
    
    if not venda:
        conn.close()
        flash("Erro: Venda não encontrada ou acesso não autorizado!", "danger")
        return redirect("/historico")

    # Se a venda estiver finalizada, devolvemos os produtos ao estoque
    if venda[0] == 'finalizada':
        cursor.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id = ?", (id,))
        itens = cursor.fetchall()
        for item in itens:
            p_id, qtd = item
            cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ? AND loja_id = ?", (qtd, p_id, loja_id))
            cursor.execute(
                "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                (p_id, "entrada", qtd)
            )
    
    # Deleta os itens da venda e a venda
    cursor.execute("DELETE FROM itens_venda WHERE venda_id = ?", (id,))
    cursor.execute("DELETE FROM vendas WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()
    
    flash(f"Venda #{id} excluída com sucesso! Os produtos correspondentes foram devolvidos ao estoque.", "success")
    return redirect("/historico")


# ✏️ ROTA PARA EDITAR VENDEDOR, CLIENTE E PAGAMENTO DA VENDA
@app.route("/vendas/editar/<int:id>", methods=["POST"])
@login_requerido
def editar_venda(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Busca a venda para validar permissão
    cursor.execute("SELECT total FROM vendas WHERE id = ? AND loja_id = ?", (id, loja_id))
    venda = cursor.fetchone()
    if not venda:
        conn.close()
        flash("Erro: Venda não localizada!", "danger")
        return redirect("/historico")

    total_venda = venda[0]
    cliente_nome = request.form.get("cliente_nome", "").strip()
    cliente_cpf = request.form.get("cliente_cpf", "").strip()
    vendedor_id = request.form.get("vendedor_id")
    forma_pagamento = request.form.get("forma_pagamento")

    # Resolve vendedor_id nulo
    vendedor_id = int(vendedor_id) if vendedor_id and vendedor_id.isdigit() else None
    
    # Recalcula comissão
    comissao = 0.0
    if vendedor_id:
        cursor.execute("SELECT comissao_percentual FROM usuarios WHERE id = ? AND ativo = 1 AND loja_id = ?", (vendedor_id, loja_id))
        vendedor = cursor.fetchone()
        if vendedor and vendedor[0]:
            comissao = total_venda * (vendedor[0] / 100.0)

    # Resolve cliente_id
    cliente_id = None
    if cliente_cpf:
        cursor.execute("SELECT id FROM clientes WHERE cpf = ? AND ativo = 1 AND loja_id = ?", (cliente_cpf, loja_id))
        row_cli = cursor.fetchone()
        if row_cli:
            cliente_id = row_cli[0]

    cursor.execute(
        """
        UPDATE vendas 
        SET cliente_nome = ?, cliente_cpf = ?, cliente_id = ?, vendedor_id = ?, 
            forma_pagamento = ?, comissao_paga = ?
        WHERE id = ? AND loja_id = ?
        """,
        (cliente_nome, cliente_cpf, cliente_id, vendedor_id, forma_pagamento, comissao, id, loja_id)
    )
    conn.commit()
    conn.close()

    flash(f"Venda #{id} atualizada com sucesso!", "success")
    return redirect("/historico")


# 📦 ROTA PARA AÇÕES EM MASSA DE VENDAS (EXCLUIR E ALTERAR EM LOTE)
@app.route("/vendas/acoes-em-massa", methods=["POST"])
@login_requerido
def acoes_em_massa_vendas():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao")

    if not ids_raw or not acao:
        conn.close()
        flash("Erro: Nenhuma venda selecionada ou ação inválida!", "danger")
        return redirect("/historico")

    ids_lista = [int(x) for x in ids_raw.split(",") if x.isdigit()]

    if acao == "excluir":
        for vid in ids_lista:
            cursor.execute("SELECT status, total FROM vendas WHERE id = ? AND loja_id = ?", (vid, loja_id))
            venda = cursor.fetchone()
            if venda:
                if venda[0] == 'finalizada':
                    # Devolve estoque
                    cursor.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id = ?", (vid,))
                    itens = cursor.fetchall()
                    for item in itens:
                        p_id, qtd = item
                        cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ? AND loja_id = ?", (qtd, p_id, loja_id))
                        cursor.execute(
                            "INSERT INTO movimentacoes (produto_id, tipo, quantidade) VALUES (?, ?, ?)",
                            (p_id, "entrada", qtd)
                        )
                cursor.execute("DELETE FROM itens_venda WHERE venda_id = ?", (vid,))
                cursor.execute("DELETE FROM vendas WHERE id = ? AND loja_id = ?", (vid, loja_id))
        conn.commit()
        flash(f"{len(ids_lista)} venda(s) excluída(s) e produtos devolvidos ao estoque!", "success")

    elif acao == "pagamento":
        nova_forma = request.form.get("operacao_pagamento")
        if nova_forma:
            params = ids_lista + [loja_id]
            placeholders = ','.join(['?'] * len(ids_lista))
            cursor.execute(
                f"UPDATE vendas SET forma_pagamento = ? WHERE id IN ({placeholders}) AND loja_id = ?",
                [nova_forma] + params
            )
            conn.commit()
            flash(f"Forma de pagamento de {len(ids_lista)} venda(s) atualizada para '{nova_forma}'!", "success")

    elif acao == "vendedor":
        novo_vendedor_id = request.form.get("operacao_vendedor")
        vendedor_id = int(novo_vendedor_id) if novo_vendedor_id and novo_vendedor_id.isdigit() else None

        for vid in ids_lista:
            cursor.execute("SELECT total FROM vendas WHERE id = ? AND loja_id = ?", (vid, loja_id))
            venda = cursor.fetchone()
            if venda:
                total_venda = venda[0]
                comissao = 0.0
                if vendedor_id:
                    cursor.execute("SELECT comissao_percentual FROM usuarios WHERE id = ? AND ativo = 1 AND loja_id = ?", (vendedor_id, loja_id))
                    vendedor = cursor.fetchone()
                    if vendedor and vendedor[0]:
                        comissao = total_venda * (vendedor[0] / 100.0)
                
                cursor.execute(
                    "UPDATE vendas SET vendedor_id = ?, comissao_paga = ? WHERE id = ? AND loja_id = ?",
                    (vendedor_id, comissao, vid, loja_id)
                )
        conn.commit()
        flash(f"Vendedor de {len(ids_lista)} venda(s) atualizado com sucesso!", "success")

    conn.close()
    return redirect("/historico")


# ⚙️ CONFIGURAÇÕES DA EMPRESA
@app.route("/configuracao", methods=["GET", "POST"])
@cargo_requerido(["configuracao"])
def configuracao():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        razao_social = request.form["razao_social"]
        cnpj = request.form["cnpj"]
        tel = request.form["tel"]
        email = request.form["email"]
        dominio = request.form["dominio"]
        endereco_rua = request.form["endereco_rua"]
        endereco_numero = request.form["endereco_numero"]
        endereco_bairro = request.form["endereco_bairro"]
        endereco_cep = request.form["endereco_cep"]
        endereco_cidade = request.form["endereco_cidade"]
        endereco_estado = request.form["endereco_estado"]

        logo_file = request.files.get("logo")
        nome_logo = None

        # Pega a logo anterior caso não tenha subido uma nova
        cursor.execute("SELECT logo FROM empresa WHERE id = 1")
        empresa_anterior = cursor.fetchone()

        if logo_file and logo_file.filename != "":
            nome_logo = secure_filename(logo_file.filename)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_logo)
            logo_file.save(caminho)
        elif empresa_anterior:
            nome_logo = empresa_anterior[0]

        # UPSERT simples (já que sempre existirá apenas a empresa ID = 1)
        cursor.execute("SELECT id FROM empresa WHERE id = 1")
        if cursor.fetchone():
            cursor.execute(
                """
                UPDATE empresa
                SET nome = ?, razao_social = ?, cnpj = ?, tel = ?, email = ?, dominio = ?,
                    endereco_rua = ?, endereco_numero = ?, endereco_bairro = ?, endereco_cep = ?,
                    endereco_cidade = ?, endereco_estado = ?, logo = ?
                WHERE id = 1
                """,
                (
                    nome, razao_social, cnpj, tel, email, dominio,
                    endereco_rua, endereco_numero, endereco_bairro, endereco_cep,
                    endereco_cidade, endereco_estado, nome_logo
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO empresa (
                    id, nome, razao_social, cnpj, tel, email, dominio,
                    endereco_rua, endereco_numero, endereco_bairro, endereco_cep,
                    endereco_cidade, endereco_estado, logo
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nome, razao_social, cnpj, tel, email, dominio,
                    endereco_rua, endereco_numero, endereco_bairro, endereco_cep,
                    endereco_cidade, endereco_estado, nome_logo
                )
            )
        
        conn.commit()
        flash("Configurações da empresa salvas com sucesso!", "success")
        return redirect("/configuracao")

    # Carrega dados atuais
    cursor.execute("SELECT * FROM empresa WHERE id = 1")
    empresa = cursor.fetchone()
    if not empresa:
        # Cria uma tupla vazia fictícia para evitar erros de renderização
        empresa = (1, "", "", "", "", "", "loja.com", "", "", "", "", "", "", "")

    conn.close()
    return render_template("configuracao.html", empresa=empresa)


# 💸 CONTROLE DE DESPESAS (CRUD)
@app.route("/despesas", methods=["GET", "POST"])
@cargo_requerido(["despesas"])
def despesas():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    if request.method == "POST":
        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        categoria = request.form["categoria"]
        data = request.form["data"]

        cursor.execute(
            """
            INSERT INTO despesas (descricao, valor, categoria, data, loja_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (descricao, valor, categoria, data, loja_id)
        )
        conn.commit()
        flash("Despesa registrada com sucesso!", "success")

    cursor.execute("SELECT id, descricao, valor, categoria, strftime('%d/%m/%Y', data) FROM despesas WHERE loja_id = ? ORDER BY data DESC", (loja_id,))
    lista_despesas = cursor.fetchall()
    conn.close()

    return render_template("despesas.html", despesas=lista_despesas)


@app.route("/despesas/excluir/<int:id>")
@cargo_requerido(["despesas"])
def excluir_despesa(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    
    cursor.execute("SELECT id FROM despesas WHERE id = ? AND loja_id = ?", (id, loja_id))
    if not cursor.fetchone():
        conn.close()
        flash("Erro: Acesso não autorizado!", "danger")
        return redirect("/despesas")
        
    cursor.execute("DELETE FROM despesas WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()
    flash("Despesa excluída com sucesso!", "success")
    return redirect("/despesas")


# 📦 AÇÕES EM MASSA PARA DESPESAS
@app.route("/despesas/acoes-em-massa", methods=["POST"])
@cargo_requerido(["despesas"])
def acoes_em_massa_despesas():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao")

    if not ids_raw or not acao:
        conn.close()
        flash("Erro: Nenhuma despesa selecionada ou ação inválida!", "danger")
        return redirect("/despesas")

    ids_lista = [int(x) for x in ids_raw.split(",") if x.isdigit()]

    if acao == "excluir":
        placeholders = ','.join(['?'] * len(ids_lista))
        params = ids_lista + [loja_id]
        cursor.execute(
            f"DELETE FROM despesas WHERE id IN ({placeholders}) AND loja_id = ?",
            params
        )
        conn.commit()
        flash(f"{len(ids_lista)} despesa(s) excluída(s) com sucesso!", "success")

    conn.close()
    return redirect("/despesas")


# 📄 EMISSÃO DE RECIBO / COMPROVANTE DE VENDA
@app.route("/venda/recibo/<int:id>")
@login_requerido
def recibo_venda(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # 1. Carrega dados da venda (suporta finalizadas e orçamentos)
    cursor.execute(
        """
        SELECT 
            id, cliente_nome, cliente_cpf, vendedor_id, caixa_id,
            forma_pagamento, entrega, total, strftime('%d/%m/%Y %H:%M', data, 'localtime'),
            entrega_recebedor, entrega_telefone, entrega_rua, entrega_numero,
            entrega_bairro, entrega_cep, entrega_complemento, status, cupom_codigo, desconto_cupom
        FROM vendas WHERE id = ? AND loja_id = ?
        """,
        (id, loja_id)
    )
    venda = cursor.fetchone()
    if not venda:
        conn.close()
        flash("Comprovante não localizado ou acesso não autorizado.", "danger")
        return redirect("/dashboard")

    # 2. Carrega itens da venda
    cursor.execute(
        """
        SELECT nome_produto, quantidade, preco_unitario, subtotal
        FROM itens_venda WHERE venda_id = ?
        """,
        (id,)
    )
    itens = cursor.fetchall()

    # 3. Busca nomes do vendedor e do caixa
    vendedor_nome = None
    if venda[3]:
        cursor.execute("SELECT nome FROM usuarios WHERE id = ?", (venda[3],))
        row = cursor.fetchone()
        if row:
            vendedor_nome = row[0]

    caixa_nome = "Não registrado"
    if venda[4]:
        cursor.execute("SELECT nome FROM usuarios WHERE id = ?", (venda[4],))
        row = cursor.fetchone()
        if row:
            caixa_nome = row[0]

    # 4. Busca dados da empresa
    cursor.execute("SELECT * FROM empresa WHERE id = 1")
    empresa = cursor.fetchone()

    conn.close()

    return render_template(
        "recibo.html",
        venda=venda,
        itens=itens,
        vendedor_nome=vendedor_nome,
        caixa_nome=caixa_nome,
        empresa=empresa,
        data_formatada=venda[8],
        status=venda[15]
    )


# 🏷️ CRUD DE CATEGORIAS DE PRODUTOS
@app.route("/categorias", methods=["GET", "POST"])
@cargo_requerido(["categorias"])
def categorias():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    if request.method == "POST":
        nome = request.form["nome"].strip()
        pai_id = request.form.get("pai_id")
        if pai_id == "":
            pai_id = None
        criado_por = session.get("nome", "Sistema")
        try:
            cursor.execute(
                "INSERT INTO categorias (nome, criado_por, pai_id, loja_id) VALUES (?, ?, ?, ?)",
                (nome, criado_por, pai_id, loja_id)
            )
            conn.commit()
            flash(f"Categoria '{nome}' criada com sucesso!", "success")
        except sqlite3.IntegrityError:
            flash("Erro: Já existe uma categoria com esse nome!", "danger")

    # Busca categorias com seus respectivos pais
    cursor.execute("""
        SELECT c.id, c.nome, c.criado_por, strftime('%d/%m/%Y', c.data_criacao), c.pai_id, p.nome as pai_nome
        FROM categorias c
        LEFT JOIN categorias p ON c.pai_id = p.id
        WHERE c.loja_id = ?
        ORDER BY COALESCE(c.pai_id, c.id) ASC, c.pai_id IS NOT NULL ASC, c.nome ASC
    """, (loja_id,))
    lista = cursor.fetchall()

    # Busca apenas categorias que podem ser pais (que não possuem pai_id, para evitar aninhamento infinito e confuso)
    cursor.execute("SELECT id, nome FROM categorias WHERE pai_id IS NULL AND loja_id = ? ORDER BY nome", (loja_id,))
    pais_disponiveis = cursor.fetchall()

    conn.close()
    return render_template("categorias.html", categorias=lista, pais_disponiveis=pais_disponiveis)


@app.route("/categorias/excluir/<int:id>")
@cargo_requerido(["categorias"])
def excluir_categoria(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    # Seta pai_id das filhas para NULL para não deletar em cascata
    cursor.execute("UPDATE categorias SET pai_id = NULL WHERE pai_id = ? AND loja_id = ?", (id, loja_id))
    # Desvincula produtos que usavam essa categoria
    cursor.execute("UPDATE produtos SET categoria_id = NULL WHERE categoria_id = ? AND loja_id = ?", (id, loja_id))
    cursor.execute("DELETE FROM categorias WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()
    flash("Categoria excluída com sucesso!", "success")
    return redirect("/categorias")


@app.route("/categorias/editar/<int:id>", methods=["POST"])
@cargo_requerido(["categorias"])
def editar_categoria(id):
    nome = request.form["nome"].strip()
    pai_id = request.form.get("pai_id")
    if pai_id == "" or pai_id == str(id): # Evita que a categoria seja pai dela mesma
        pai_id = None
        
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)
    try:
        cursor.execute(
            "UPDATE categorias SET nome = ?, pai_id = ? WHERE id = ? AND loja_id = ?",
            (nome, pai_id, id, loja_id)
        )
        conn.commit()
        flash("Categoria atualizada com sucesso!", "success")
    except sqlite3.IntegrityError:
        flash("Erro: Já existe uma categoria com esse nome!", "danger")
    conn.close()
    return redirect("/categorias")


# 📦 AÇÕES EM MASSA PARA CATEGORIAS
@app.route("/categorias/acoes-em-massa", methods=["POST"])
@cargo_requerido(["categorias"])
def acoes_em_massa_categorias():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao")

    if not ids_raw or not acao:
        conn.close()
        flash("Erro: Nenhuma categoria selecionada ou ação inválida!", "danger")
        return redirect("/categorias")

    ids_lista = [int(x) for x in ids_raw.split(",") if x.isdigit()]

    if acao == "excluir":
        for cid in ids_lista:
            # Seta pai_id das filhas para NULL para não deletar em cascata
            cursor.execute("UPDATE categorias SET pai_id = NULL WHERE pai_id = ? AND loja_id = ?", (cid, loja_id))
            # Desvincula produtos que usavam essa categoria
            cursor.execute("UPDATE produtos SET categoria_id = NULL WHERE categoria_id = ? AND loja_id = ?", (cid, loja_id))
            cursor.execute("DELETE FROM categorias WHERE id = ? AND loja_id = ?", (cid, loja_id))
        conn.commit()
        flash(f"{len(ids_lista)} categoria(s) excluída(s) com sucesso!", "success")

    elif acao == "definir_pai":
        novo_pai_id = request.form.get("operacao_pai")
        pai_id = int(novo_pai_id) if novo_pai_id and novo_pai_id.isdigit() else None
        
        if pai_id:
            cursor.execute("SELECT id FROM categorias WHERE id = ? AND loja_id = ?", (pai_id, loja_id))
            if not cursor.fetchone():
                conn.close()
                flash("Erro: Categoria pai inválida!", "danger")
                return redirect("/categorias")

        alterados_cont = 0
        for cid in ids_lista:
            if cid == pai_id:
                continue
            cursor.execute("UPDATE categorias SET pai_id = ? WHERE id = ? AND loja_id = ?", (pai_id, cid, loja_id))
            alterados_cont += 1
            
        conn.commit()
        if pai_id:
            flash(f"Hierarquia de {alterados_cont} categoria(s) atualizada com sucesso!", "success")
        else:
            flash(f"{alterados_cont} categoria(s) convertida(s) em categoria pai principal!", "success")

    conn.close()
    return redirect("/categorias")


# Atualiza a sessão com permissões ao logar
@app.route("/atualizar-sessao")
@login_requerido
def atualizar_sessao():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT permissoes FROM usuarios WHERE id = ?", (session["usuario_id"],))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        session["permissoes"] = row[0]
    return redirect("/dashboard")


@app.context_processor
def inject_empresa_nome():
    if "loja_id" in session:
        try:
            conn = sqlite3.connect("database/loja.db")
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM empresa WHERE id = ?", (session["loja_id"],))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"nome_empresa_sessao": row[0]}
        except Exception:
            pass
    return {"nome_empresa_sessao": None}


# 🏢 GERENCIAMENTO DE LOJAS (SUPER MASTER CENTRAL)
@app.route("/lojas", methods=["GET", "POST"])
@super_master_requerido
def lojas():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        cnpj = request.form["cnpj"].strip()
        email = request.form["email"].strip()
        admin_email = request.form["admin_email"].strip()
        admin_senha = request.form["admin_senha"].strip()

        if not nome or not email or not admin_email or not admin_senha:
            flash("Erro: Preencha todos os campos obrigatórios!", "danger")
            return redirect("/lojas")

        try:
            # 1. Insere a nova loja
            cursor.execute(
                "INSERT INTO lojas (nome, cnpj, email) VALUES (?, ?, ?)",
                (nome, cnpj, email)
            )
            loja_id = cursor.lastrowid

            # 2. Cria o usuário administrador Master para esta nova loja
            senha_hash = generate_password_hash(admin_senha)
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha, cargo, primeiro_login, loja_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("Administrador Loja", admin_email, senha_hash, "master", 1, loja_id)
            )

            # 3. Cria as configurações padrão de empresa para a nova loja
            cursor.execute(
                """
                INSERT INTO empresa (id, nome, cnpj, email, logo, loja_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (loja_id, nome, cnpj, email, None, loja_id) # Usamos o próprio loja_id como ID único da empresa
            )

            conn.commit()
            flash(f"Loja '{nome}' cadastrada e ativada com sucesso!", "success")
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Erro: O e-mail do administrador já está cadastrado no sistema!", "danger")
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao cadastrar loja: {str(e)}", "danger")
            
        conn.close()
        return redirect("/lojas")

    # Listagem de todas as lojas
    cursor.execute("SELECT id, nome, cnpj, email, ativo, strftime('%d/%m/%Y', data_criacao) FROM lojas ORDER BY id DESC")
    lista_lojas = cursor.fetchall()
    conn.close()

    return render_template("lojas.html", lojas=lista_lojas)


@app.route("/lojas/status/<int:id>")
@super_master_requerido
def alterar_status_loja(id):
    if id == 1:
        flash("Erro: Não é possível desativar a loja administradora principal!", "danger")
        return redirect("/lojas")

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ativo, nome FROM lojas WHERE id = ?", (id,))
    row = cursor.fetchone()
    
    if row:
        novo_status = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE lojas SET ativo = ? WHERE id = ?", (novo_status, id))
        conn.commit()
        status_txt = "ativada" if novo_status == 1 else "desativada"
        flash(f"Loja '{row[1]}' foi {status_txt}!", "success")
    
    conn.close()
    return redirect("/lojas")


# 🗑️ EXCLUSÃO DEFINITIVA INDIVIDUAL DE LOJA
@app.route("/lojas/excluir/<int:id>")
@super_master_requerido
def excluir_loja_individual(id):
    if id == 1:
        flash("Erro: A loja administradora principal não pode ser excluída!", "danger")
        return redirect("/lojas")

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    
    # Deleta tudo referente a essa loja
    cursor.execute("DELETE FROM lojas WHERE id = ?", (id,))
    cursor.execute("DELETE FROM empresa WHERE id = ?", (id,))
    cursor.execute("DELETE FROM usuarios WHERE loja_id = ?", (id,))
    cursor.execute("DELETE FROM produtos WHERE loja_id = ?", (id,))
    cursor.execute("DELETE FROM categorias WHERE loja_id = ?", (id,))
    cursor.execute("DELETE FROM clientes WHERE loja_id = ?", (id,))
    cursor.execute("DELETE FROM vendas WHERE loja_id = ?", (id,))
    cursor.execute("DELETE FROM despesas WHERE loja_id = ?", (id,))
    
    conn.commit()
    conn.close()
    
    flash(f"Loja #{id} e todos os seus dados correspondentes foram excluídos definitivamente!", "success")
    return redirect("/lojas")


# 📦 AÇÕES EM MASSA PARA LOJAS (EXCLUSIVO SUPER MASTER)
@app.route("/lojas/acoes-em-massa", methods=["POST"])
@super_master_requerido
def acoes_em_massa_lojas():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    ids_raw = request.form.get("ids", "")
    acao = request.form.get("acao")

    if not ids_raw or not acao:
        conn.close()
        flash("Erro: Nenhuma loja selecionada ou ação inválida!", "danger")
        return redirect("/lojas")

    ids_lista = [int(x) for x in ids_raw.split(",") if x.isdigit()]

    # Filtra os IDs para remover a loja administradora principal (1)
    ids_validos = [x for x in ids_lista if x != 1]

    if not ids_validos:
        conn.close()
        flash("Erro: A loja administradora principal não pode ser alterada em massa!", "danger")
        return redirect("/lojas")

    if acao == "ativar":
        placeholders = ','.join(['?'] * len(ids_validos))
        cursor.execute(
            f"UPDATE lojas SET ativo = 1 WHERE id IN ({placeholders})",
            ids_validos
        )
        conn.commit()
        flash(f"{len(ids_validos)} loja(s) ativada(s) com sucesso!", "success")

    elif acao == "desativar":
        placeholders = ','.join(['?'] * len(ids_validos))
        cursor.execute(
            f"UPDATE lojas SET ativo = 0 WHERE id IN ({placeholders})",
            ids_validos
        )
        conn.commit()
        flash(f"{len(ids_validos)} loja(s) desativada(s) com sucesso!", "success")

    elif acao == "excluir":
        for lid in ids_validos:
            cursor.execute("DELETE FROM lojas WHERE id = ?", (lid,))
            cursor.execute("DELETE FROM empresa WHERE id = ?", (lid,))
            cursor.execute("DELETE FROM usuarios WHERE loja_id = ?", (lid,))
            cursor.execute("DELETE FROM produtos WHERE loja_id = ?", (lid,))
            cursor.execute("DELETE FROM categorias WHERE loja_id = ?", (lid,))
            cursor.execute("DELETE FROM clientes WHERE loja_id = ?", (lid,))
            cursor.execute("DELETE FROM vendas WHERE loja_id = ?", (lid,))
            cursor.execute("DELETE FROM despesas WHERE loja_id = ?", (lid,))
            
        conn.commit()
        flash(f"{len(ids_validos)} loja(s) e todos os seus dados correspondentes foram excluídos do sistema!", "success")

    conn.close()
    return redirect("/lojas")


# 🧹 ROTA PARA LIMPEZA DE DADOS (EXCLUSIVO SUPER MASTER)
@app.route("/limpeza", methods=["GET", "POST"])
@super_master_requerido
def limpeza_dados():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    if request.method == "POST":
        loja_id_limpar = int(request.form.get("loja_id", 0))
        tabelas_limpar = request.form.getlist("tabelas")
        senha_confirmacao = request.form.get("senha_confirmacao", "")

        # 1. Validações de Segurança
        # Confirma a senha do Super Master logado
        cursor.execute("SELECT senha FROM usuarios WHERE id = ?", (session["usuario_id"],))
        senha_hash = cursor.fetchone()[0]
        
        if not check_password_hash(senha_hash, senha_confirmacao):
            conn.close()
            flash("Erro: Senha de confirmação incorreta!", "danger")
            return redirect("/limpeza")

        # Verifica se a loja selecionada existe
        cursor.execute("SELECT nome FROM lojas WHERE id = ?", (loja_id_limpar,))
        loja_row = cursor.fetchone()
        if not loja_row:
            conn.close()
            flash("Erro: Loja selecionada inválida!", "danger")
            return redirect("/limpeza")
        
        nome_loja = loja_row[0]
        limpos = []

        try:
            # 2. Executa a limpeza com base nas opções marcadas
            if "produtos" in tabelas_limpar:
                # Busca as imagens para apagar fisicamente do disco
                cursor.execute("""
                    SELECT ip.caminho_imagem 
                    FROM imagens_produto ip
                    JOIN produtos p ON ip.produto_id = p.id
                    WHERE p.loja_id = ?
                """, (loja_id_limpar,))
                imagens = cursor.fetchall()
                for img in imagens:
                    caminho_fisico = os.path.join(app.config["UPLOAD_FOLDER"], img[0])
                    if os.path.exists(caminho_fisico):
                        try:
                            os.remove(caminho_fisico)
                        except Exception as e:
                            print(f"Erro ao remover arquivo físico de imagem: {e}")

                # Deleta movimentacoes, imagens e produtos
                cursor.execute("""
                    DELETE FROM movimentacoes WHERE produto_id IN (
                        SELECT id FROM produtos WHERE loja_id = ?
                    )
                """, (loja_id_limpar,))
                cursor.execute("""
                    DELETE FROM imagens_produto WHERE produto_id IN (
                        SELECT id FROM produtos WHERE loja_id = ?
                    )
                """, (loja_id_limpar,))
                cursor.execute("DELETE FROM produtos WHERE loja_id = ?", (loja_id_limpar,))
                limpos.append("Produtos (e Movimentações)")

            if "categorias" in tabelas_limpar:
                # Deleta categorias
                cursor.execute("DELETE FROM categorias WHERE loja_id = ?", (loja_id_limpar,))
                # Se limpou categorias, remove categoria_id dos produtos restantes
                cursor.execute("UPDATE produtos SET categoria_id = NULL WHERE loja_id = ?", (loja_id_limpar,))
                limpos.append("Categorias")

            if "vendas" in tabelas_limpar:
                # Deleta itens_venda e vendas
                cursor.execute("""
                    DELETE FROM itens_venda WHERE venda_id IN (
                        SELECT id FROM vendas WHERE loja_id = ?
                    )
                """, (loja_id_limpar,))
                cursor.execute("DELETE FROM vendas WHERE loja_id = ?", (loja_id_limpar,))
                limpos.append("Vendas (e Carrinhos de Itens)")

            if "clientes" in tabelas_limpar:
                # Deleta clientes
                cursor.execute("DELETE FROM clientes WHERE loja_id = ?", (loja_id_limpar,))
                # Define cliente_id nas vendas restantes como NULL
                cursor.execute("UPDATE vendas SET cliente_id = NULL WHERE loja_id = ?", (loja_id_limpar,))
                limpos.append("Clientes")

            if "despesas" in tabelas_limpar:
                # Deleta despesas
                cursor.execute("DELETE FROM despesas WHERE loja_id = ?", (loja_id_limpar,))
                limpos.append("Despesas")

            if "colaboradores" in tabelas_limpar:
                # Segurança: Deleta todos os colaboradores da loja EXCETO o Master daquela loja!
                # E se for a loja administradora principal (1), protege o Super Master logado
                if loja_id_limpar == 1:
                    cursor.execute(
                        "DELETE FROM usuarios WHERE loja_id = ? AND id != ?",
                        (loja_id_limpar, session["usuario_id"])
                    )
                else:
                    cursor.execute(
                        "DELETE FROM usuarios WHERE loja_id = ? AND cargo != 'master'",
                        (loja_id_limpar,)
                    )
                limpos.append("Colaboradores (contas Masters preservadas)")

            conn.commit()
            
            if limpos:
                msg_sucesso = f"Limpeza concluída na loja '{nome_loja}' para os seguintes módulos: {', '.join(limpos)}."
                flash(msg_sucesso, "success")
            else:
                flash("Nenhum módulo selecionado para limpeza.", "info")

        except Exception as e:
            conn.rollback()
            flash(f"Erro ao executar limpeza: {str(e)}", "danger")

        conn.close()
        return redirect("/limpeza")

    # GET Handler: Carrega lista de lojas para o dropdown
    cursor.execute("SELECT id, nome FROM lojas ORDER BY COALESCE(id=1, 0) DESC, nome ASC")
    lojas_lista = cursor.fetchall()
    conn.close()

    return render_template("limpeza.html", lojas=lojas_lista)


# 🏷️ ROTAS DO GERENCIADOR DE CUPONS E DESCONTOS
@app.route("/cupons", methods=["GET", "POST"])
@cargo_requerido(["produtos", "configuracoes"])
def cupons():
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().upper()
        tipo = request.form.get("tipo", "percentual")
        valor = float(request.form.get("valor", 0.0) or 0.0)
        validade = request.form.get("validade") or None
        limite_usos = request.form.get("limite_usos") or None
        
        if limite_usos:
            limite_usos = int(limite_usos)

        try:
            cursor.execute(
                """
                INSERT INTO cupons (codigo, tipo, valor, validade, limite_usos, loja_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (codigo, tipo, valor, validade, limite_usos, loja_id)
            )
            conn.commit()
            flash(f"Cupom '{codigo}' cadastrado com sucesso!", "success")
        except sqlite3.IntegrityError:
            flash(f"Erro: O código de cupom '{codigo}' já está em uso!", "danger")
        
        conn.close()
        return redirect("/cupons")

    # GET Handler: Lista os cupons da loja
    cursor.execute("SELECT id, codigo, tipo, valor, validade, limite_usos, usos_atuais, ativo FROM cupons WHERE loja_id = ? ORDER BY id DESC", (loja_id,))
    cupons_lista = cursor.fetchall()
    conn.close()
    
    return render_template("cupons.html", cupons=cupons_lista)


@app.route("/cupons/status/<int:id>")
@cargo_requerido(["produtos", "configuracoes"])
def status_cupom(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    # Verifica permissao sobre o cupom
    cursor.execute("SELECT ativo FROM cupons WHERE id = ? AND loja_id = ?", (id, loja_id))
    row = cursor.fetchone()
    if row:
        novo_status = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE cupons SET ativo = ? WHERE id = ? AND loja_id = ?", (novo_status, id, loja_id))
        conn.commit()
        flash("Status do cupom alterado com sucesso!", "success")
    else:
        flash("Erro: Cupom não localizado.", "danger")

    conn.close()
    return redirect("/cupons")


@app.route("/cupons/excluir/<int:id>")
@cargo_requerido(["produtos", "configuracoes"])
def excluir_cupom(id):
    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()
    loja_id = session.get("loja_id", 1)

    cursor.execute("DELETE FROM cupons WHERE id = ? AND loja_id = ?", (id, loja_id))
    conn.commit()
    conn.close()

    flash("Cupom excluído com sucesso!", "success")
    return redirect("/cupons")


@app.route("/validar-cupom", methods=["POST"])
@login_requerido
def validar_cupom():
    codigo = request.json.get("codigo", "").strip().upper()
    loja_id = session.get("loja_id", 1)
    
    if not codigo:
        return jsonify({"valido": False, "mensagem": "Código de cupom não informado."})

    conn = sqlite3.connect("database/loja.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, codigo, tipo, valor, validade, limite_usos, usos_atuais, ativo 
        FROM cupons 
        WHERE codigo = ? AND loja_id = ?
        """,
        (codigo, loja_id)
    )
    cupom = cursor.fetchone()
    conn.close()

    if not cupom:
        return jsonify({"valido": False, "mensagem": "Cupom não encontrado ou inválido."})

    c_id, c_codigo, c_tipo, c_valor, c_validade, c_limite, c_usos, c_ativo = cupom

    # Validações
    if c_ativo != 1:
        return jsonify({"valido": False, "mensagem": "Este cupom está desativado."})

    # Valida limite de usos
    if c_limite is not None and c_usos >= c_limite:
        return jsonify({"valido": False, "mensagem": "Este cupom atingiu o limite máximo de utilizações."})

    # Valida data de validade
    if c_validade:
        from datetime import datetime
        data_atual = datetime.now().date()
        try:
            data_val = datetime.strptime(c_validade, "%Y-%m-%d").date()
            if data_atual > data_val:
                return jsonify({"valido": False, "mensagem": "Este cupom está expirado."})
        except Exception:
            pass

    return jsonify({
        "valido": True,
        "id": c_id,
        "codigo": c_codigo,
        "tipo": c_tipo,
        "valor": c_valor,
        "mensagem": "Cupom aplicado com sucesso!"
    })


# 🏁 Inicialização do servidor local
if __name__ == "__main__":
    app.run(debug=True)