# AstroControl

Sistema web de gestão comercial criado para centralizar a operação de lojas físicas em uma única plataforma. O projeto reúne controle de estoque, vendas, PDV, clientes, colaboradores e indicadores do negócio em uma interface simples e responsiva.

> Projeto desenvolvido para estudo e portfólio, com foco na construção de uma aplicação completa usando Python e Flask.

[Acessar demonstração](https://astrocontrol.onrender.com) · [Ver meu perfil no GitHub](https://github.com/luca-ssales)

## Sobre o projeto

O AstroControl nasceu da proposta de facilitar tarefas comuns da rotina comercial. Em vez de utilizar ferramentas separadas para registrar produtos, acompanhar o estoque e controlar vendas, a aplicação concentra essas informações em um único ambiente.

O sistema adota uma estrutura multi-loja: cada estabelecimento possui seus próprios dados, usuários e configurações. Também há controle de acesso por cargo e permissões personalizadas para diferentes integrantes da equipe.

## Funcionalidades

- Dashboard com indicadores de produtos, vendas e valor em estoque
- Cadastro de produtos com SKU, código de barras, categoria e imagens
- Controle de estoque e alerta de quantidade mínima
- PDV com carrinho, busca de produtos e finalização de vendas
- Cadastro e consulta de clientes por CPF
- Registro de vendas, orçamentos e histórico de movimentações
- Cupons de desconto com validade e limite de utilização
- Gestão de despesas
- Cadastro de colaboradores, cargos, permissões e comissões
- Emissão de recibos com dados da empresa e da venda
- Registro de informações para entrega
- Administração de múltiplas lojas
- Interface disponível em português e inglês
- Recuperação e alteração de senha

## Tecnologias

| Área | Tecnologias |
| --- | --- |
| Back-end | Python, Flask e Werkzeug |
| Front-end | HTML, CSS e JavaScript |
| Banco de dados | SQLite |
| Servidor | Gunicorn |
| Hospedagem | Render |

## Estrutura do projeto

```text
AstroControl/
├── app.py                 # Aplicação, rotas e regras de negócio
├── database/
│   └── loja.db            # Banco de dados SQLite
├── static/
│   ├── css/               # Estilos da aplicação
│   ├── images/            # Imagens e mascote do sistema
│   ├── js/                # Traduções e interações do front-end
│   └── uploads/           # Imagens enviadas pelos usuários
├── templates/             # Páginas HTML renderizadas pelo Flask
├── requirements.txt       # Dependências Python
└── LICENSE                # Licença do projeto
```

## Como executar localmente

### Pré-requisitos

- Python 3.10 ou superior
- Git

### Instalação

```bash
git clone https://github.com/luca-ssales/AstroControl.git
cd AstroControl
```

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
```

No Windows:

```powershell
.venv\Scripts\Activate.ps1
```

No Linux ou macOS:

```bash
source .venv/bin/activate
```

Instale as dependências e inicie a aplicação:

```bash
pip install -r requirements.txt
python app.py
```

Depois, acesse `http://127.0.0.1:5000` no navegador e crie uma loja pela tela inicial.

## Principais aprendizados

Durante o desenvolvimento deste projeto, trabalhei com:

- criação de rotas e autenticação com Flask;
- modelagem e manipulação de um banco de dados relacional;
- separação de dados entre diferentes lojas;
- aplicação de regras de negócio em vendas e estoque;
- controle de sessão, cargos e permissões;
- integração entre back-end, templates e JavaScript;
- organização e publicação de uma aplicação web.

## Status

O AstroControl está em desenvolvimento. A versão atual apresenta o fluxo principal de gestão comercial e serve como base para futuras melhorias de segurança, escalabilidade e experiência do usuário.

## Autor

Desenvolvido por [Lucas Sales](https://github.com/luca-ssales).

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
