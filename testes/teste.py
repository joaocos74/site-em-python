@app.route("/pesquisar_estabelecimentos", methods=["GET"])
def licencas():
    filtros = {
        "cnpj": request.args.get("cnpj"),
        "orgao": request.args.get("orgao"),
        "nome_empresarial": request.args.get("nome_empresarial"),
        "tipo_data": request.args.get("tipo_data"),
        "data_de": request.args.get("data_de"),
        "data_ate": request.args.get("data_ate"),
        "mei": request.args.get("mei"),
        "orgao_registro": request.args.get("orgao_registro"),
        "numero_viabilidade": request.args.get("numero_viabilidade"),
        "situacao": request.args.get("situacao"),
        "grau_risco": request.args.get("grau_risco"),
        "atividade_economica": request.args.get("atividade_economica"),
        "municipio": request.args.get("municipio"),
        "tipo_evento": request.args.get("tipo_evento"),
        "filial": request.args.get("filial"),
    }

    # aqui você usa os filtros para consultar seu banco, por exemplo com SQLAlchemy
    licencas = []  # substitua pela lista de objetos retornados

    return render_template("licenciamento_busca.html", licencas=licencas)

@app.route("/licencas/<int:licenca_id>/analisar")
def analisar_licenca(licenca_id: int):
    # busca e exibe detalhes da licença
    return f"Detalhes da licença {licenca_id}"




from flask import Flask, render_template, redirect, request, flash, jsonify, session
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'joao_paulo_seguro'

# =========================
# CONEXÃO POSTGRES
# =========================
def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "aws-0-us-west-2.pooler.supabase.com"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres.bizolwxybpgrlbpvjzaq"),
        password=os.getenv("DB_PASSWORD", "A6Y0bU1s3nb13YB1"),
        sslmode="require"
    )
    return conn


# =========================
# LOGIN
# =========================
@app.route("/")
def home():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    matricula = request.form.get("matricula")

    if not matricula:
        flash("Informe a matrícula.")
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT matricula, nome, nivel
        FROM usuarios
        WHERE matricula = %s
    """, (matricula,))

    usuario = cur.fetchone()
    cur.close()
    conn.close()

    if not usuario:
        flash("Matrícula não cadastrada.")
        return redirect("/")

    session["matricula"] = usuario["matricula"]
    session["nome"] = usuario["nome"]
    session["nivel"] = usuario["nivel"]

    return redirect("/abas")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# ÁREA PRINCIPAL
# =========================
@app.route("/abas")
def abas():
    if "matricula" not in session:
        return redirect("/")
    return render_template("abas.html")


# =========================
# MAPA / LISTAGEM
# =========================
@app.route("/estabelecimentos")
def estabelecimentos():

    if "matricula" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if session["nivel"] == 1:
        # ADMIN
        cur.execute("""
            SELECT *
            FROM public.cadastros
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
        """)
    else:
        # USUÁRIO NORMAL
        cur.execute("""
            SELECT *
            FROM public.cadastros
            WHERE fiscal_matricula = %s
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
        """, (session["matricula"],))

    dados = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(dados)


# =========================
# PESQUISA COM FILTRO SEGURO
# =========================
@app.route("/pesquisar_estabelecimentos")
def pesquisar_estabelecimentos():

    if "matricula" not in session:
        return redirect("/")

    campos = {
        "id": "id",
        "nivel": "nivel",
        "classe": "classe",
        "razao_social": "razao_social",
        "nome_fantasia": "nome_fantasia",
        "endereco": "endereco",
        "cnpj_ou_cpf": "cnpj_ou_cpf",
        "cnae": "cnae_principal",
        "numero_parecer_tecnico": "numero_parecer_tecnico",
        "ultima_inspecao": "ultima_inspecao",
        "alvara": "alvara",
        "vigi_risco": "vigi_risco",
        "observacoes": "observacoes"
    }

    filtros = []
    valores = []

    for campo_html, campo_db in campos.items():
        valor = request.args.get(campo_html)

        if not valor:
            continue

        if campo_db == "ultima_inspecao":
            filtros.append("TO_CHAR(ultima_inspecao, 'DD/MM/YYYY') ILIKE %s")
        else:
            filtros.append(f"{campo_db}::text ILIKE %s")

        valores.append(f"%{valor}%")

    sql = "SELECT * FROM public.cadastros WHERE 1=1"

    # FILTRO POR MATRÍCULA
    if session["nivel"] != 1:
        sql += " AND fiscal_matricula = %s"
        valores.append(session["matricula"])

    if filtros:
        sql += " AND " + " AND ".join(filtros)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, valores)

    dados = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("abas.html", licencas=dados)


# =========================
# ANALISAR / EDITAR LICENÇA
# =========================
@app.route("/licencas/<int:licenca_id>/analisar", methods=["GET", "POST"])
def analisar_licenca(licenca_id):

    if "matricula" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verifica se usuário tem acesso
    if session["nivel"] != 1:
        cur.execute("""
            SELECT id
            FROM public.cadastros
            WHERE id = %s
              AND fiscal_matricula = %s
        """, (licenca_id, session["matricula"]))

        if not cur.fetchone():
            cur.close()
            conn.close()
            return "Acesso negado", 403

    if request.method == "POST":
        campo = request.form.get("campo")
        valor = request.form.get("valor")

        if campo:
            cur.execute(
                f"UPDATE public.cadastros SET {campo} = %s WHERE id = %s",
                (valor, licenca_id)
            )
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True})

        return jsonify({"success": False}), 400

    # GET
    if session["nivel"] == 1:
        cur.execute("SELECT * FROM public.cadastros WHERE id = %s", (licenca_id,))
    else:
        cur.execute("""
            SELECT *
            FROM public.cadastros
            WHERE id = %s
              AND fiscal_matricula = %s
        """, (licenca_id, session["matricula"]))

    licenca = cur.fetchone()
    cur.close()
    conn.close()

    if not licenca:
        return "Registro não encontrado", 404

    return render_template("usuarios.html", licenca=licenca)


# =========================
if __name__ == "__main__":
    app.run(debug=True)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    from flask import Flask, render_template, redirect, request, flash, jsonify
import json
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'joao paulo'

logado = False


# =========================
# CONEXÃO COM POSTGRES
# =========================
def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "aws-0-us-west-2.pooler.supabase.com"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres.bizolwxybpgrlbpvjzaq"),
        password=os.getenv("DB_PASSWORD", "A6Y0bU1s3nb13YB1"),
        sslmode="require"
    )

    with conn.cursor() as cur:
        cur.execute("SET search_path TO public, public")
        cur.execute("SET datestyle = 'DMY'")

    return conn


# =========================
# ROTAS BÁSICAS
# =========================
@app.route("/")
def home():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def login():
    nome = request.form.get('matricula')

    with open('usuarios.json', encoding='utf-8') as f:
        usuarios = json.load(f)

    for usuario in usuarios:
        if usuario['nome'] == nome:
            return render_template('abas.html')

    flash('Matrícula não cadastrada!')
    return redirect('/')


@app.route("/cadastrar")
def cadastrar():
    return render_template("login_adm.html")


@app.route('/administrador', methods=['POST'])
def administrador():
    nome = request.form.get('cadastro')

    if not nome:
        return redirect('/cadastrar')

    with open('usuarios.json', encoding='utf-8') as f:
        usuarios = json.load(f)

    if any(u['nome'].lower() == nome.lower() for u in usuarios):
        flash('Matrícula já cadastrada!')
        return redirect('/cadastrar')

    usuarios.append({'nome': nome})

    with open('usuarios.json', 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=3, ensure_ascii=False)

    return redirect('/')


@app.route("/abas")
def abas():
    return render_template("abas.html") if logado else render_template("login.html")


@app.route('/mapa', methods=['POST'])
def mapa():
    return render_template("mapa.html")


# =========================
# MAPA
# =========================
@app.route("/estabelecimentos")
def estabelecimentos():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT
            id,
            nivel,
            classe,
            razao_social,
            nome_fantasia,
            endereco,
            latitude,
            longitude,
            cnpj_ou_cpf,
            cnae_principal,
            numero_parecer_tecnico,
            TO_CHAR(ultima_inspecao, 'DD/MM/YYYY') AS ultima_inspecao,
            alvara,
            vigi_risco,
            observacoes
        FROM public.cadastros
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
    """)

    dados = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(dados)


# =========================
# PESQUISA (RESOLVIDA)
# =========================
@app.route("/pesquisar_estabelecimentos")
def pesquisar_estabelecimentos():

    campos = {
        "id": "id",
        "nivel": "nivel",
        "classe": "classe",
        "razao_social": "razao_social",
        "nome_fantasia": "nome_fantasia",
        "endereco": "endereco",
        "cnpj_ou_cpf": "cnpj_ou_cpf",
        "cnae": "cnae_principal",
        "numero_parecer_tecnico": "numero_parecer_tecnico",
        "ultima_inspecao": "ultima_inspecao",
        "alvara": "alvara",
        "vigi_risco": "vigi_risco",
        "observacoes": "observacoes"
    }

    filtros = []
    valores = []

    for campo_html, campo_db in campos.items():
        valor = request.args.get(campo_html)

        if not valor:
            continue

        # DATA
        if campo_db == "ultima_inspecao":
            filtros.append("TO_CHAR(ultima_inspecao, 'DD/MM/YYYY') ILIKE %s")
            valores.append(f"%{valor}%")

        # NUMÉRICO (busca parcial segura)
        elif campo_db in ["id", "nivel", "classe"]:
            filtros.append(f"CAST({campo_db} AS TEXT) ILIKE %s")
            valores.append(f"%{valor}%")

        # TEXTO
        else:
            filtros.append(f"{campo_db} ILIKE %s")
            valores.append(f"%{valor}%")

    sql = "SELECT * FROM public.cadastros"
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, valores)

    licencas = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("abas.html", licencas=licencas)


# =========================
# USUÁRIOS
# =========================
@app.route("/usuarios")
def usuarios():
    return render_template("usuarios.html") if logado else render_template("login.html")


# =========================
# ANALISAR LICENÇA
# =========================
@app.route('/licencas/<int:licenca_id>/analisar', methods=['GET', 'POST'])
def analisar_licenca(licenca_id):

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'POST':
        campo = request.form.get('campo')
        valor = request.form.get('valor')

        if campo:
            cur.execute(
                f"UPDATE public.cadastros SET {campo} = %s WHERE id = %s",
                (valor, licenca_id)
            )
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True})

        return jsonify({"success": False}), 400

    cur.execute("""
        SELECT
            id,
            nivel,
            classe,
            razao_social,
            nome_fantasia,
            endereco,
            latitude,
            longitude,
            cnpj_ou_cpf,
            cnae_principal,
            numero_parecer_tecnico,
            TO_CHAR(ultima_inspecao, 'DD/MM/YYYY') AS ultima_inspecao,
            alvara,
            vigi_risco,
            observacoes
        FROM public.cadastros
        WHERE id = %s
    """, (licenca_id,))

    licenca = cur.fetchone()
    cur.close()
    conn.close()

    if not licenca:
        return "Licença não encontrada", 404

    return render_template('usuarios.html', licenca=licenca)


# =========================
if __name__ == "__main__":
    app.run(debug=True)
