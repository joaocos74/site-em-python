from flask import Flask, render_template, redirect, request, flash, jsonify, session
from flask import request, redirect, url_for
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

    sql = "SELECT * FROM public.cadastros WHERE 1=1"
    valores = []

    # 🔹 PRIMEIRO aplica filtro por matrícula
    if session["nivel"] != 1:
        sql += " AND fiscal_matricula = %s"
        valores.append(session["matricula"])

    # 🔹 DEPOIS aplica filtros dinâmicos
    filtros = []

    for campo_html, campo_db in campos.items():
        valor = request.args.get(campo_html)

        if not valor:
            continue

        if campo_db == "id":
            filtros.append("id = %s")
            valores.append(int(valor))

        elif campo_db in ["ultima_inspecao", "alvara", "vigi_risco"]:
            filtros.append(f"{campo_db} = %s")
            valores.append(valor)

        else:
            filtros.append(f"{campo_db}::text ILIKE %s")
            valores.append(f"%{valor}%")

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

    # =========================
    # POST - SALVAR ALTERAÇÕES
    # =========================
    if request.method == "POST":

        cur.execute("""
            UPDATE public.cadastros SET
                razao_social = %s,
                nome_fantasia = %s,
                nivel = %s,
                classe = %s,
                cnpj_ou_cpf = %s,
                cnae_principal = %s,
                ultima_inspecao = %s,
                alvara = %s,
                vigi_risco = %s,
                fiscal_responsavel = %s,
                fiscal_matricula = %s,
                observacoes = %s
            WHERE id = %s
        """, (
            request.form.get("razao_social"),
            request.form.get("nome_fantasia"),
            request.form.get("nivel"),
            request.form.get("classe"),
            request.form.get("cnpj_ou_cpf"),
            request.form.get("cnae_principal"),
            request.form.get("ultima_inspecao") or None,
            request.form.get("alvara") or None,
            request.form.get("vigi_risco") or None,
            request.form.get("fiscal_responsavel"),
            request.form.get("fiscal_matricula"),
            request.form.get("observacoes"),
            licenca_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(f"/licencas/{licenca_id}/analisar")

    # =========================
    # GET - CARREGAR PÁGINA
    # =========================
    cur.execute("SELECT * FROM public.cadastros WHERE id = %s", (licenca_id,))
    licenca = cur.fetchone()

    cur.close()
    conn.close()

    if not licenca:
        return "Registro não encontrado", 404

    return render_template("analisar.html", licenca=licenca)

    # =========================
    # PAGINA DE CADASTRO DE NOVO ESTABELECIMENTO
    # =========================
@app.route("/cadastros/novo", methods=["GET", "POST"])
def novo_cadastro():
    if "matricula" not in session:
        return redirect("/")

    if request.method == "POST":
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            INSERT INTO public.cadastros
            (razao_social, nome_fantasia, nivel, classe, cnpj_ou_cpf, cnae_principal,
             ultima_inspecao, alvara, vigi_risco, fiscal_responsavel, fiscal_matricula,
             observacoes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            request.form.get("razao_social"),
            request.form.get("nome_fantasia"),
            request.form.get("nivel"),
            request.form.get("classe"),
            request.form.get("cnpj_ou_cpf"),
            request.form.get("cnae_principal"),
            request.form.get("ultima_inspecao") or None,
            request.form.get("alvara") or None,
            request.form.get("vigi_risco") or None,
            request.form.get("fiscal_responsavel"),
            request.form.get("fiscal_matricula"),
            request.form.get("observacoes"),
        ))

        novo = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        # opcional: já abrir a página de edição do registro criado
        return redirect(f"/licencas/{novo['id']}/analisar")

    return render_template("analisar_novo_estabelecimento.html")





# =========================
if __name__ == "__main__":
    app.run(debug=True)



