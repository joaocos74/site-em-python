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
# Administrador - CADASTRO DE USUÁRIOS
# =========================


@app.route("/cadastrar")
def cadastrar():
    return render_template("cadastro.html")

@app.route("/administrador", methods=["POST"])
def administrador():

    matricula = request.form.get("matricula")
    nome = request.form.get("nome")

    if not matricula or not nome:
        flash("Preencha todos os campos.")
        return redirect("/cadastrar")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verifica se já existe
    cur.execute("""
        SELECT matricula
        FROM usuarios
        WHERE matricula = %s
    """, (matricula,))

    if cur.fetchone():
        cur.close()
        conn.close()
        flash("Matrícula já cadastrada!")
        return redirect("/cadastrar")

    # Nível padrão 2 (você pode alterar depois no banco)
    cur.execute("""
        INSERT INTO usuarios (matricula, nome, nivel)
        VALUES (%s, %s, %s)
    """, (matricula, nome, 2))

    conn.commit()
    cur.close()
    conn.close()

    flash("Usuário cadastrado com sucesso!")
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
@app.route('/mapa', methods=['POST'])
def mapa():
    return render_template("mapa.html")

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