from flask import Flask, render_template, redirect, request, flash, jsonify, session
from flask import request, redirect, url_for
from datetime import date, datetime, timedelta
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
@app.route('/mapa')
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
# agenda da semana (compartilhada)
# =========================

from datetime import date, timedelta

def _inicio_semana(dt: date) -> date:
    # segunda-feira como início
    return dt - timedelta(days=dt.weekday())

@app.route("/agenda")
def agenda():
    if "matricula" not in session:
        return redirect("/")
    return render_template("agenda.html")

@app.route("/api/agenda/semana-atual")
def api_agenda_semana_atual():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    hoje = date.today()
    inicio = _inicio_semana(hoje)
    fim = inicio + timedelta(days=6)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT p.id, p.dia, p.turno, p.texto, p.feito,
               p.matricula,
               COALESCE(p.autor_nome, u.nome) AS autor_nome,
               COALESCE(u.cor_postit, '#fff4a3') AS cor
        FROM public.agenda_postits p
        LEFT JOIN public.usuarios u ON u.matricula = p.matricula
        WHERE p.dia BETWEEN %s AND %s
        ORDER BY p.dia, p.turno, p.id
    """, (inicio, fim))

    itens = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "itens": [
            {
                "id": i["id"],
                "dia": i["dia"].isoformat(),
                "turno": i["turno"],
                "texto": i["texto"],
                "feito": i["feito"],
                "matricula": i["matricula"],
                "autor_nome": i["autor_nome"],
                "cor": i["cor"],
            } for i in itens
        ]
    })

@app.route("/api/agenda", methods=["POST"])
def api_agenda_criar():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    data = request.get_json(force=True)
    dia = data.get("dia")
    texto = (data.get("texto") or "").strip()
    turno = (data.get("turno") or "manha").strip().lower()

    if not dia or not texto:
        return jsonify({"error": "dia e texto são obrigatórios"}), 400
    if turno not in ("manha", "tarde"):
        return jsonify({"error": "turno inválido (manha/tarde)"}), 400

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        INSERT INTO public.agenda_postits (matricula, autor_nome, dia, turno, texto)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, dia, turno, texto, feito, matricula, autor_nome
    """, (session["matricula"], session.get("nome"), dia, turno, texto))

    novo = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "id": novo["id"],
        "dia": novo["dia"].isoformat(),
        "turno": novo["turno"],
        "texto": novo["texto"],
        "feito": novo["feito"],
        "matricula": novo["matricula"],
        "autor_nome": novo["autor_nome"],
    })

@app.route("/api/agenda/<int:postit_id>", methods=["PATCH"])
def api_agenda_atualizar(postit_id):
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    data = request.get_json(force=True)
    texto = data.get("texto")
    feito = data.get("feito")
    dia = data.get("dia")
    turno = data.get("turno")

    sets = []
    vals = []

    if texto is not None:
        texto = (texto or "").strip()
        if not texto:
            return jsonify({"error": "texto não pode ser vazio"}), 400
        sets.append("texto = %s")
        vals.append(texto)

    if feito is not None:
        sets.append("feito = %s")
        vals.append(bool(feito))

    if dia is not None:
        sets.append("dia = %s")
        vals.append(dia)

    if turno is not None:
        turno = (turno or "").strip().lower()
        if turno not in ("manha", "tarde"):
            return jsonify({"error": "turno inválido (manha/tarde)"}), 400
        sets.append("turno = %s")
        vals.append(turno)

    if not sets:
        return jsonify({"error": "nada para atualizar"}), 400

    sets.append("atualizado_em = now()")
    vals.append(postit_id)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(f"""
        UPDATE public.agenda_postits
        SET {", ".join(sets)}
        WHERE id = %s
        RETURNING id, dia, turno, texto, feito, matricula, autor_nome
    """, vals)

    up = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not up:
        return jsonify({"error": "post-it não encontrado"}), 404

    return jsonify({
        "id": up["id"],
        "dia": up["dia"].isoformat(),
        "turno": up["turno"],
        "texto": up["texto"],
        "feito": up["feito"],
        "matricula": up["matricula"],
        "autor_nome": up["autor_nome"],
    })

@app.route("/api/agenda/<int:postit_id>", methods=["DELETE"])
def api_agenda_apagar(postit_id):
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM public.agenda_postits
        WHERE id = %s
    """, (postit_id,))
    apagados = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"deleted": apagados})

@app.route("/api/agenda/dia/<dia>", methods=["DELETE"])
def api_agenda_apagar_dia(dia):
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM public.agenda_postits
        WHERE dia = %s
    """, (dia,))
    apagados = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"deleted": apagados})


# =========================
# agenda da semana espelho
# =========================

@app.route("/api/agenda/semana-atual/minha")
def api_agenda_semana_atual_minha():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    hoje = date.today()
    inicio = _inicio_semana(hoje)
    fim = inicio + timedelta(days=6)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.id, p.dia, p.turno, p.texto, p.feito,
               p.matricula,
               COALESCE(u.cor_postit, '#fff4a3') AS cor
        FROM public.agenda_postits p
        LEFT JOIN public.usuarios u ON u.matricula = p.matricula
        WHERE p.dia BETWEEN %s AND %s
          AND p.matricula = %s
        ORDER BY p.dia, p.turno, p.id
    """, (inicio, fim, session["matricula"]))

    itens = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "itens": [
            {
                "id": i["id"],
                "dia": i["dia"].isoformat(),
                "turno": i["turno"],
                "texto": i["texto"],
                "feito": i["feito"],
                "cor": i["cor"],
            } for i in itens
        ]
    })



# =========================
if __name__ == "__main__":
    app.run(debug=True)



