<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Criar Loja - AstroControl SaaS</title>
    <!-- Favicon -->
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;800&display=swap" rel="stylesheet">
    <!-- FontAwesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.4);
            --bg-deep: #0b0f19;
            --bg-card: #151c2c;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: rgba(255, 255, 255, 0.08);
            --radius-md: 12px;
            --radius-lg: 20px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-deep);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow-y: auto;
            background-image: radial-gradient(circle at 50% 30%, rgba(139, 92, 246, 0.08) 0%, transparent 65%);
        }

        .signup-container {
            max-width: 480px;
            width: 100%;
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            position: relative;
        }

        .logo {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 8px;
        }

        .logo i {
            color: var(--primary);
            filter: drop-shadow(0 0 8px var(--primary-glow));
        }

        .subtitle {
            text-align: center;
            color: var(--text-muted);
            font-size: 0.88rem;
            margin-bottom: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            color: #e2e8f0;
            margin-bottom: 8px;
        }

        .form-control {
            width: 100%;
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 12px 16px;
            border-radius: var(--radius-md);
            font-size: 0.9rem;
            outline: none;
            transition: all 0.2s ease;
        }

        .form-control:focus {
            border-color: var(--primary);
            background-color: rgba(255, 255, 255, 0.05);
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15);
        }

        .btn-submit {
            width: 100%;
            background-color: var(--primary);
            color: #ffffff;
            border: none;
            padding: 14px;
            font-weight: 700;
            font-size: 0.95rem;
            border-radius: var(--radius-md);
            cursor: pointer;
            transition: all 0.25s ease;
            box-shadow: 0 4px 14px var(--primary-glow);
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-submit:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
        }

        .btn-submit:active {
            transform: translateY(1px);
        }

        .footer-links {
            text-align: center;
            margin-top: 25px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .footer-links a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s ease;
        }

        .footer-links a:hover {
            color: #a78bfa;
            text-decoration: underline;
        }

        /* Alertas */
        .alert {
            padding: 12px 16px;
            border-radius: var(--radius-md);
            font-size: 0.85rem;
            margin-bottom: 24px;
            border: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .alert-danger {
            background-color: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.15);
        }

        .alert-success {
            background-color: rgba(16, 185, 129, 0.1);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.15);
        }
    </style>
</head>
<body>

    <div class="signup-container">
        <!-- Logo -->
        <a href="/" class="logo">
            <i class="fa-solid fa-meteor"></i> AstroControl
        </a>
        <p class="subtitle">Cadastre sua loja e comece seu teste grátis</p>

        <!-- FLASH ALERTS -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' or category == 'danger' else 'success' }}">
                        <i class="fa-solid fa-circle-exclamation"></i>
                        <span>{{ message }}</span>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" action="/assinar">
            <!-- Dados da Loja -->
            <div class="form-group">
                <label for="loja_nome">Nome da Loja / Empresa:</label>
                <input type="text" class="form-control" id="loja_nome" name="loja_nome" placeholder="Ex: Mercadinho Estrela" required autocomplete="off">
            </div>

            <div class="form-group">
                <label for="loja_cnpj">CNPJ (Opcional):</label>
                <input type="text" class="form-control" id="loja_cnpj" name="loja_cnpj" placeholder="00.000.000/0001-00" autocomplete="off">
            </div>

            <hr style="border: 0; border-top: 1px solid var(--border); margin: 25px 0 20px 0;">

            <!-- Dados do Administrador -->
            <div class="form-group">
                <label for="admin_nome">Seu Nome Completo (Administrador Master):</label>
                <input type="text" class="form-control" id="admin_nome" name="admin_nome" placeholder="Ex: Roberto Silva" required autocomplete="off">
            </div>

            <div class="form-group">
                <label for="admin_email">E-mail de Acesso (Login):</label>
                <input type="email" class="form-control" id="admin_email" name="admin_email" placeholder="nome@provedor.com" required autocomplete="off">
            </div>

            <div class="form-group" style="margin-bottom: 25px;">
                <label for="admin_senha">Senha de Acesso:</label>
                <input type="password" class="form-control" id="admin_senha" name="admin_senha" placeholder="Mínimo 6 caracteres" required minlength="6">
            </div>

            <button type="submit" class="btn-submit">
                <i class="fa-solid fa-rocket"></i> Ativar Minha Conta & Entrar
            </button>
        </form>

        <div class="footer-links">
            Já tem uma conta? <a href="/login">Acesse o Painel</a>
        </div>
    </div>

</body>
</html>
