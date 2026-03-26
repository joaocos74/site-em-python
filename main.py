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
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5433),
        database=os.getenv("DB_NAME", "sistema_vigilancia"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "visaTaio@2026")
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

        # =========================
        # UPDATE CADASTRO (SEU ORIGINAL)
        # =========================
        cur.execute("""
            UPDATE public.cadastros SET
                razao_social = %s,
                nome_fantasia = %s,
                nivel = %s,
                classe = %s,
                cnpj_ou_cpf = %s,
                endereco = %s,
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
            request.form.get("endereco"),
            request.form.get("cnae_principal"),
            request.form.get("ultima_inspecao") or None,
            request.form.get("alvara") or None,
            request.form.get("vigi_risco") or None,
            request.form.get("fiscal_responsavel"),
            request.form.get("fiscal_matricula"),
            request.form.get("observacoes"),
            licenca_id
        ))

        # =========================
        # RESPONSÁVEL
        # =========================
        cur.execute("SELECT id FROM responsavel WHERE cadastro_id = %s", (licenca_id,))
        resp = cur.fetchone()

        if resp:
            cur.execute("""
                UPDATE responsavel SET
                    nome=%s,
                    nacionalidade=%s,
                    naturalidade=%s,
                    estado_civil=%s,
                    identidade=%s,
                    profissao=%s,
                    cpf=%s,
                    endereco=%s,
                    telefone=%s,
                    cep=%s,
                    municipio=%s,
                    uf=%s
                WHERE cadastro_id=%s
            """, (
                request.form.get("resp_nome"),
                request.form.get("resp_nacionalidade"),
                request.form.get("resp_naturalidade"),
                request.form.get("resp_estado_civil"),
                request.form.get("resp_identidade"),
                request.form.get("resp_profissao"),
                request.form.get("resp_cpf"),
                request.form.get("resp_endereco"),
                request.form.get("resp_telefone"),
                request.form.get("resp_cep"),
                request.form.get("resp_municipio"),
                request.form.get("resp_uf"),
                licenca_id
            ))
        else:
            cur.execute("""
                INSERT INTO responsavel (
                    cadastro_id, nome, nacionalidade, naturalidade,
                    estado_civil, identidade, profissao, cpf,
                    endereco, telefone, cep, municipio, uf
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                licenca_id,
                request.form.get("resp_nome"),
                request.form.get("resp_nacionalidade"),
                request.form.get("resp_naturalidade"),
                request.form.get("resp_estado_civil"),
                request.form.get("resp_identidade"),
                request.form.get("resp_profissao"),
                request.form.get("resp_cpf"),
                request.form.get("resp_endereco"),
                request.form.get("resp_telefone"),
                request.form.get("resp_cep"),
                request.form.get("resp_municipio"),
                request.form.get("resp_uf")
            ))

        # =========================
        # RESPONSÁVEL TÉCNICO
        # =========================
        cur.execute("SELECT id FROM responsavel_tecnico WHERE cadastro_id = %s", (licenca_id,))
        rt = cur.fetchone()

        if rt:
            cur.execute("""
                UPDATE responsavel_tecnico SET
                    nome=%s,
                    inscricao=%s,
                    endereco=%s,
                    telefone=%s,
                    cep=%s,
                    municipio=%s,
                    uf=%s
                WHERE cadastro_id=%s
            """, (
                request.form.get("rt_nome"),
                request.form.get("rt_inscricao"),
                request.form.get("rt_endereco"),
                request.form.get("rt_telefone"),
                request.form.get("rt_cep"),
                request.form.get("rt_municipio"),
                request.form.get("rt_uf"),
                licenca_id
            ))
        else:
            cur.execute("""
                INSERT INTO responsavel_tecnico (
                    cadastro_id, nome, inscricao,
                    endereco, telefone, cep, municipio, uf
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                licenca_id,
                request.form.get("rt_nome"),
                request.form.get("rt_inscricao"),
                request.form.get("rt_endereco"),
                request.form.get("rt_telefone"),
                request.form.get("rt_cep"),
                request.form.get("rt_municipio"),
                request.form.get("rt_uf")
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

    cur.execute("SELECT * FROM responsavel WHERE cadastro_id = %s", (licenca_id,))
    responsavel = cur.fetchone()

    cur.execute("SELECT * FROM responsavel_tecnico WHERE cadastro_id = %s", (licenca_id,))
    responsavel_tecnico = cur.fetchone()

    cur.close()
    conn.close()

    if not licenca:
        return "Registro não encontrado", 404

    return render_template(
        "analisar.html",
        licenca=licenca,
        responsavel=responsavel,
        responsavel_tecnico=responsavel_tecnico
    )

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
            (razao_social, nome_fantasia, nivel, classe, cnpj_ou_cpf, endereco, cnae_principal,
             ultima_inspecao, alvara, vigi_risco, fiscal_responsavel, fiscal_matricula,
             observacoes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            request.form.get("razao_social"),
            request.form.get("nome_fantasia"),
            request.form.get("nivel"),
            request.form.get("classe"),
            request.form.get("cnpj_ou_cpf"),
            request.form.get("endereco"),
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
               p.matricula_autor,
               COALESCE(p.autor_nome, u.nome) AS autor_nome,
               COALESCE(u.cor_postit, '#fff4a3') AS cor
        FROM public.agenda_postits p
        LEFT JOIN public.usuarios u ON u.matricula = p.matricula_autor
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
                "matricula": i["matricula_autor"],
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
    vinculados = data.get("vinculados", [])

    if not dia or not texto:
        return jsonify({"error": "dia e texto são obrigatórios"}), 400

    if turno not in ("manha", "tarde"):
        return jsonify({"error": "turno inválido"}), 400

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1️⃣ cria post-it
    cur.execute("""
        INSERT INTO public.agenda_postits
        (matricula_autor, autor_nome, dia, turno, texto)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, dia, turno, texto, feito
    """, (session["matricula"], session.get("nome"), dia, turno, texto))

    novo = cur.fetchone()
    postit_id = novo["id"]

    # 2️⃣ garante que criador está vinculado
    vinculados = set(vinculados)
    vinculados.add(session["matricula"])

    # 3️⃣ cria vínculos
    for matricula in vinculados:
        cur.execute("""
            INSERT INTO public.agenda_postits_usuarios (postit_id, matricula)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (postit_id, matricula))

    conn.commit()
    cur.close()
    conn.close()


    return jsonify({
        "id": novo["id"],
        "dia": novo["dia"].isoformat(),
        "turno": novo["turno"],
        "texto": novo["texto"],
        "feito": novo["feito"],
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
        RETURNING id, dia, turno, texto, feito, matricula_autor, autor_nome
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
        "matricula": up["matricula_autor"],
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
            p.matricula_autor,
            COALESCE(u.cor_postit, '#fff4a3') AS cor
        FROM public.agenda_postits p
        JOIN public.agenda_postits_usuarios pu
            ON pu.postit_id = p.id
        LEFT JOIN public.usuarios u
            ON u.matricula = p.matricula_autor
        WHERE p.dia BETWEEN %s AND %s
        AND pu.matricula = %s
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
# agenda da semana espelho
# =========================

@app.route("/api/usuarios")
def api_usuarios():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT matricula, nome
        FROM public.usuarios
        ORDER BY nome
    """)

    usuarios = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(usuarios)

# =========================
# aba redesim
# =========================

@app.route("/redesim", methods=["GET"])
def redesim():
    if "matricula" not in session:
        return redirect("/")
    return render_template("redesim.html")

@app.route("/api/redesim/buscar_cnpj")
def buscar_cnpj_redesim():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    cnpj = request.args.get("cnpj")

    if not cnpj:
        return jsonify({"error": "cnpj obrigatório"}), 400

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT * FROM public.cadastros
        WHERE cnpj_ou_cpf = %s
        LIMIT 1
    """, (cnpj,))

    cadastro = cur.fetchone()

    cur.close()
    conn.close()

    if not cadastro:
        return jsonify({"existe": False})

    return jsonify({
        "existe": True,
        "dados": cadastro
    })


@app.route("/redesim", methods=["POST"])
def salvar_redesim():
    if "matricula" not in session:
        return redirect("/")
    
    cnpj = request.form.get("cnpj_ou_cpf", "").strip()
    razao_social = request.form.get("razao_social", "").strip()
    
    if not cnpj or not razao_social:
        flash("CNPJ e Razão Social são obrigatórios!")
        return redirect("/redesim")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cnpj = request.form.get("cnpj_ou_cpf")

    # 🔎 Verifica se já existe cadastro
    cur.execute("""
        SELECT id FROM public.cadastros
        WHERE cnpj_ou_cpf = %s
        LIMIT 1
    """, (cnpj,))

    existente = cur.fetchone()

    if existente:
        cadastro_id = existente["id"]

        # 🔄 Atualiza cadastro existente
        cur.execute("""
            UPDATE public.cadastros SET
                razao_social = %s,
                nome_fantasia = %s,
                nivel = %s,
                classe = %s,
                cnae_principal = %s,
                alvara = %s,
                fiscal_responsavel = %s,
                fiscal_matricula = %s,
                observacoes = %s
            WHERE id = %s
        """, (
            request.form.get("razao_social"),
            request.form.get("nome_fantasia"),
            request.form.get("nivel"),
            request.form.get("classe"),
            request.form.get("cnae_principal"),
            request.form.get("alvara") or None,
            request.form.get("fiscal_responsavel") or None,
            request.form.get("fiscal_matricula") or None,
            request.form.get("observacoes"),
            cadastro_id
        ))

    else:
        # ➕ Insere novo cadastro
        cur.execute("""
            INSERT INTO public.cadastros
            (razao_social, nome_fantasia, nivel, classe, cnpj_ou_cpf, cnae_principal,
             alvara, fiscal_responsavel, fiscal_matricula,
             observacoes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            request.form.get("razao_social"),
            request.form.get("nome_fantasia"),
            request.form.get("nivel"),
            request.form.get("classe"),
            request.form.get("cnpj_ou_cpf"),
            request.form.get("cnae_principal"),
            request.form.get("alvara") or None,
            request.form.get("fiscal_responsavel") or None,
            request.form.get("fiscal_matricula") or None,
            request.form.get("observacoes"),
        ))

        novo = cur.fetchone()
        cadastro_id = novo["id"]

    # 📦 Sempre salva na tabela redesim
    cur.execute("""
        INSERT INTO public.redesim
        (cadastro_id, razao_social, nome_fantasia, cnpj_ou_cpf,
         nivel, classe, cnae_principal, alvara,
         fiscal_responsavel, fiscal_matricula, observacoes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        cadastro_id,
        request.form.get("razao_social"),
        request.form.get("nome_fantasia"),
        cnpj,
        request.form.get("nivel"),
        request.form.get("classe"),
        request.form.get("cnae_principal"),
        request.form.get("alvara") or None,
        request.form.get("fiscal_responsavel") or None,
        request.form.get("fiscal_matricula") or None,
        request.form.get("observacoes"),
    ))

    conn.commit()
    cur.close()
    conn.close()

    flash("Registro REDESIM salvo com sucesso!")
    return redirect("/redesim")



@app.route("/api/redesim/listar")
def listar_redesim():

    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    
    cur.execute("""
        SELECT cadastro_id,
               nivel,
               classe,
               razao_social,
               cnpj_ou_cpf,
               TO_CHAR(alvara,'DD/MM/YYYY') as alvara
        FROM public.redesim
        ORDER BY id DESC
    """)

    dados = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(dados)
    
# =========================
# aba cronograma
# =========================

def get_quadrimestre_por_mes(mes):
    if mes in [1,2,3,4]:
        return 1
    elif mes in [5,6,7,8]:
        return 2
    return 3


def distribuir_por_quadrimestre(estabelecimentos):
    distribuicao = {1: [], 2: [], 3: []}

    por_nivel = {}
    for e in estabelecimentos:
        por_nivel.setdefault(e["nivel"], []).append(e)

    for nivel, lista in por_nivel.items():
        lista.sort(key=lambda x: x["id"])
        tamanho = len(lista)
        bloco = tamanho // 3

        distribuicao[1] += lista[0:bloco]
        distribuicao[2] += lista[bloco:bloco*2]
        distribuicao[3] += lista[bloco*2:]

    return distribuicao


@app.route("/cronograma")
def cronograma():
    if "matricula" not in session:
        return redirect("/")

    ano = request.args.get("ano", 2026)
    return render_template("cronograma.html", ano=ano)

@app.route("/api/cronograma")
def api_cronograma():

    ano = request.args.get("ano", 2026)
    fiscal = request.args.get("fiscal")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    sql = """
        SELECT c.id,
               c.nome_fantasia,
               c.nivel,
               c.cnpj_ou_cpf,
               c.ultima_inspecao,
               c.alvara,
               c.fiscal_matricula,
               cr.quadrimestre,
               cr.mes_previsto
        FROM public.cadastros c
        LEFT JOIN public.cronograma_inspecoes cr
            ON cr.cadastro_id = c.id AND cr.ano = %s
        WHERE 1=1
    """

    valores = [ano]

    if fiscal:
        sql += " AND c.fiscal_matricula = %s"
        valores.append(fiscal)

    cur.execute(sql, valores)
    dados = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(dados)


@app.route("/api/cronograma", methods=["POST"])
def salvar_cronograma():

    data = request.get_json(force=True)

    cadastro_id = data.get("cadastro_id")
    ano = data.get("ano")
    mes = data.get("mes")
    quadrimestre = get_quadrimestre_por_mes(int(mes))
    fiscal = data.get("fiscal")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO public.cronograma_inspecoes
        (cadastro_id, ano, quadrimestre, mes_previsto, fiscal_matricula)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (cadastro_id, ano)
        DO UPDATE SET
            quadrimestre = EXCLUDED.quadrimestre,
            mes_previsto = EXCLUDED.mes_previsto,
            fiscal_matricula = EXCLUDED.fiscal_matricula,
            atualizado_em = now()
    """, (cadastro_id, ano, quadrimestre, mes, fiscal))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "ok"})

# =========================
# aba robertinho
# =========================

@app.route("/robertinho")
def robertinho():
    if "matricula" not in session:
        return redirect("/")
    return render_template("robertinho.html")

@app.route("/api/robertinho")
def api_robertinho():

    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    hoje = date.today()
    ano = hoje.year
    mes = hoje.month

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 🔹 Inspeções no mês
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM public.cadastros
        WHERE ultima_inspecao IS NOT NULL
        AND EXTRACT(MONTH FROM ultima_inspecao) = %s
        AND EXTRACT(YEAR FROM ultima_inspecao) = %s
    """, (mes, ano))

    inspecoes = cur.fetchone()["total"]

    # 🔹 Alvarás no mês
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM public.cadastros
        WHERE alvara IS NOT NULL
        AND EXTRACT(MONTH FROM alvara) = %s
        AND EXTRACT(YEAR FROM alvara) = %s
    """, (mes, ano))

    alvaras = cur.fetchone()["total"]

    cur.close()
    conn.close()

    return jsonify({
        "mes": mes,
        "ano": ano,
        "inspecoes": inspecoes,
        "alvaras": alvaras
    })

# =========================
# ABA ESTATISTICAS
# =========================
# ========= ESTATÍSTICAS (modelo print) =========

from datetime import date

@app.route("/estatisticas")
def estatisticas():
    if "matricula" not in session:
        return redirect("/")
    return render_template("estatisticas.html")

def _base_filters(req, alias_c="c", alias_cr="cr"):
    # Nesta aba NÃO aplica regra de permissão por fiscal (conforme pedido).
    # Fiscal/nivel/classe são apenas filtros opcionais.
    fiscal = req.args.get("fiscal") or ""
    nivel  = req.args.get("nivel") or ""
    classe = req.args.get("classe") or ""

    filtros = []
    vals = []

    if fiscal:
        # pode vir do cadastros ou do cronograma (quando join)
        filtros.append(f" AND {alias_c}.fiscal_matricula = %s ")
        vals.append(fiscal)

    if nivel:
        filtros.append(f" AND {alias_c}.nivel = %s ")
        vals.append(nivel)

    if classe:
        filtros.append(f" AND {alias_c}.classe = %s ")
        vals.append(classe)

    return "".join(filtros), vals

@app.route("/api/estatisticas/filtros")
def api_est_filtros():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # anos por inspeção
    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM c.ultima_inspecao)::int AS ano
        FROM public.cadastros c
        WHERE c.ultima_inspecao IS NOT NULL
        ORDER BY ano DESC
    """)
    anos_inspecao = [r["ano"] for r in cur.fetchall() if r["ano"]]

    # anos por cronograma
    cur.execute("""
        SELECT DISTINCT cr.ano::int AS ano
        FROM public.cronograma_inspecoes cr
        ORDER BY ano DESC
    """)
    anos_cronograma = [r["ano"] for r in cur.fetchall() if r["ano"]]

    # anos por redesim (alvara)
    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM r.alvara)::int AS ano
        FROM public.redesim r
        WHERE r.alvara IS NOT NULL
        ORDER BY ano DESC
    """)
    anos_redesim = [r["ano"] for r in cur.fetchall() if r["ano"]]

    # classes / niveis
    cur.execute("""
        SELECT DISTINCT c.classe
        FROM public.cadastros c
        WHERE c.classe IS NOT NULL AND c.classe <> ''
        ORDER BY c.classe
    """)
    classes = [r["classe"] for r in cur.fetchall()]

    cur.execute("""
        SELECT DISTINCT c.nivel
        FROM public.cadastros c
        WHERE c.nivel IS NOT NULL
        ORDER BY c.nivel
    """)
    niveis = [r["nivel"] for r in cur.fetchall()]

    # fiscais (a partir de usuários e/ou cadastros)
    cur.execute("""
        SELECT DISTINCT c.fiscal_matricula AS matricula,
               COALESCE(u.nome, 'Fiscal ' || c.fiscal_matricula) AS nome
        FROM public.cadastros c
        LEFT JOIN public.usuarios u ON u.matricula = c.fiscal_matricula
        WHERE c.fiscal_matricula IS NOT NULL AND c.fiscal_matricula <> ''
        ORDER BY nome
    """)
    fiscais = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "anos_inspecao": anos_inspecao,
        "anos_cronograma": anos_cronograma,
        "anos_redesim": anos_redesim,
        "classes": classes,
        "niveis": niveis,
        "fiscais": fiscais
    })

# --------- MÉTRICAS POR ANO (cadastros) ---------
@app.route("/api/estatisticas/por_ano")
def api_est_por_ano():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    ano = int(request.args.get("ano", date.today().year))
    extra_sql, extra_vals = _base_filters(request, alias_c="c")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(f"""
        SELECT COUNT(*)::int AS total
        FROM public.cadastros c
        WHERE 1=1 {extra_sql}
    """, extra_vals)
    total = cur.fetchone()["total"]

    cur.execute(f"""
        SELECT COUNT(*)::int AS feito
        FROM public.cadastros c
        WHERE c.ultima_inspecao IS NOT NULL
          AND EXTRACT(YEAR FROM c.ultima_inspecao) = %s
          {extra_sql}
    """, [ano] + extra_vals)
    feito = cur.fetchone()["feito"]

    cur.close()
    conn.close()

    perc = round((feito / total * 100.0), 1) if total else 0.0

    return jsonify({
        "ano": ano,
        "table": [{
            "ano": ano,
            "total": int(total),
            "feito": int(feito),
            "percentual": perc
        }],
        "chart": {"labels": ["INSPECIONADO", "NÃO INSPECIONADO"], "values": [int(feito), max(int(total)-int(feito), 0)]}
    })

# --------- POR CLASSE (cadastros) ---------
@app.route("/api/estatisticas/por_classe")
def api_est_por_classe():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    ano = int(request.args.get("ano", date.today().year))
    extra_sql, extra_vals = _base_filters(request, alias_c="c")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # total por classe (universo)
    cur.execute(f"""
        SELECT COALESCE(NULLIF(c.classe,''), 'SEM CLASSE') AS classe,
               COUNT(*)::int AS total
        FROM public.cadastros c
        WHERE 1=1 {extra_sql}
        GROUP BY classe
        ORDER BY total DESC
    """, extra_vals)
    tot = cur.fetchall()

    # feito por classe (inspecionado no ano)
    cur.execute(f"""
        SELECT COALESCE(NULLIF(c.classe,''), 'SEM CLASSE') AS classe,
               COUNT(*)::int AS feito
        FROM public.cadastros c
        WHERE c.ultima_inspecao IS NOT NULL
          AND EXTRACT(YEAR FROM c.ultima_inspecao) = %s
          {extra_sql}
        GROUP BY classe
    """, [ano] + extra_vals)
    fei = cur.fetchall()

    cur.close()
    conn.close()

    fei_map = {r["classe"]: int(r["feito"]) for r in fei}
    table = []
    for r in tot:
        classe = r["classe"]
        total = int(r["total"])
        feito = int(fei_map.get(classe, 0))
        perc = round((feito / total * 100.0), 1) if total else 0.0
        table.append({"classe": classe, "total": total, "feito": feito, "percentual": perc})

    # gráfico: percentual por classe (top 10)
    top = table[:10]
    chart = {"x": [t["classe"] for t in top], "y": [t["percentual"] for t in top]}

    return jsonify({"ano": ano, "table": table, "chart": chart})

# --------- POR NÍVEL (cadastros) ---------
@app.route("/api/estatisticas/por_nivel")
def api_est_por_nivel():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    ano = int(request.args.get("ano", date.today().year))
    extra_sql, extra_vals = _base_filters(request, alias_c="c")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(f"""
        SELECT c.nivel, COUNT(*)::int AS total
        FROM public.cadastros c
        WHERE c.nivel IS NOT NULL {extra_sql}
        GROUP BY c.nivel
        ORDER BY c.nivel
    """, extra_vals)
    tot = cur.fetchall()

    cur.execute(f"""
        SELECT c.nivel, COUNT(*)::int AS feito
        FROM public.cadastros c
        WHERE c.nivel IS NOT NULL
          AND c.ultima_inspecao IS NOT NULL
          AND EXTRACT(YEAR FROM c.ultima_inspecao) = %s
          {extra_sql}
        GROUP BY c.nivel
        ORDER BY c.nivel
    """, [ano] + extra_vals)
    fei = cur.fetchall()

    cur.close()
    conn.close()

    fei_map = {str(r["nivel"]): int(r["feito"]) for r in fei}
    table = []
    for r in tot:
        nivel = str(r["nivel"])
        total = int(r["total"])
        feito = int(fei_map.get(nivel, 0))
        perc = round((feito / total * 100.0), 1) if total else 0.0
        table.append({"nivel": nivel, "total": total, "feito": feito, "percentual": perc})

    # gráfico pizza: participação dos feitos por nível (só entre os feitos)
    labels = [f"Nível {t['nivel']}" for t in table]
    values = [t["feito"] for t in table]

    return jsonify({"ano": ano, "table": table, "chart": {"labels": labels, "values": values}})

# --------- QUADRIMESTRE (cronograma_inspecoes) ---------
@app.route("/api/estatisticas/por_quadrimestre")
def api_est_por_quadrimestre():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    ano = int(request.args.get("ano", date.today().year))
    quadr = request.args.get("quadrimestre")  # 1/2/3 ou vazio

    # filtros base via cadastros, mas fiscal aqui deve ser do CRONOGRAMA também
    fiscal = request.args.get("fiscal") or ""
    nivel  = request.args.get("nivel") or ""
    classe = request.args.get("classe") or ""

    filtros = ["cr.ano = %s"]
    vals = [ano]

    if quadr:
        filtros.append("cr.quadrimestre = %s")
        vals.append(int(quadr))
    if fiscal:
        filtros.append("c.fiscal_matricula = %s")
        vals.append(fiscal)
    if nivel:
        filtros.append("c.nivel = %s")
        vals.append(nivel)
    if classe:
        filtros.append("c.classe = %s")
        vals.append(classe)

    where = " AND ".join(filtros)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # total a fazer por quadrimestre
    cur.execute(f"""
        SELECT cr.quadrimestre::int AS quadrimestre,
               COUNT(*)::int AS total_a_fazer
        FROM public.cronograma_inspecoes cr
        JOIN public.cadastros c ON c.id = cr.cadastro_id
        WHERE {where}
        GROUP BY cr.quadrimestre
        ORDER BY cr.quadrimestre
    """, vals)
    tot_rows = cur.fetchall()

    # total feito por quadrimestre (inspeção no quadrimestre do ano)
    cur.execute(f"""
        SELECT cr.quadrimestre::int AS quadrimestre,
               COUNT(*)::int AS total_feito
        FROM public.cronograma_inspecoes cr
        JOIN public.cadastros c ON c.id = cr.cadastro_id
        WHERE {where}
          AND c.ultima_inspecao IS NOT NULL
          AND EXTRACT(YEAR FROM c.ultima_inspecao) = %s
          AND (
            (cr.quadrimestre = 1 AND EXTRACT(MONTH FROM c.ultima_inspecao) BETWEEN 1 AND 4) OR
            (cr.quadrimestre = 2 AND EXTRACT(MONTH FROM c.ultima_inspecao) BETWEEN 5 AND 8) OR
            (cr.quadrimestre = 3 AND EXTRACT(MONTH FROM c.ultima_inspecao) BETWEEN 9 AND 12)
          )
        GROUP BY cr.quadrimestre
        ORDER BY cr.quadrimestre
    """, vals + [ano])
    fei_rows = cur.fetchall()

    cur.close()
    conn.close()

    tot_map = {int(r["quadrimestre"]): int(r["total_a_fazer"]) for r in tot_rows}
    fei_map = {int(r["quadrimestre"]): int(r["total_feito"]) for r in fei_rows}

    table = []
    for q in (1, 2, 3):
        total = tot_map.get(q, 0)
        feito = fei_map.get(q, 0)
        perc = round((feito / total * 100.0), 1) if total else 0.0
        table.append({"quadrimestre": q, "total": total, "feito": feito, "percentual": perc})

    if quadr:
        q = int(quadr)
        total = tot_map.get(q, 0)
        feito = fei_map.get(q, 0)
    else:
        total = sum(tot_map.values())
        feito = sum(fei_map.values())

    return jsonify({
        "ano": ano,
        "table": table,
        "chart": {"labels": ["FEITO", "A FAZER"], "values": [feito, max(total-feito, 0)]}
    })

# --------- MÊS (cronograma_inspecoes) ---------
@app.route("/api/estatisticas/por_mes")
def api_est_por_mes():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    ano = int(request.args.get("ano", date.today().year))
    mes = int(request.args.get("mes", date.today().month))

    fiscal = request.args.get("fiscal") or ""
    nivel  = request.args.get("nivel") or ""
    classe = request.args.get("classe") or ""

    filtros = ["cr.ano = %s", "cr.mes_previsto = %s"]
    vals = [ano, mes]

    if fiscal:
        filtros.append("c.fiscal_matricula = %s")
        vals.append(fiscal)
    if nivel:
        filtros.append("c.nivel = %s")
        vals.append(nivel)
    if classe:
        filtros.append("c.classe = %s")
        vals.append(classe)

    where = " AND ".join(filtros)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(f"""
        SELECT COUNT(*)::int AS total_a_fazer
        FROM public.cronograma_inspecoes cr
        JOIN public.cadastros c ON c.id = cr.cadastro_id
        WHERE {where}
    """, vals)
    total = cur.fetchone()["total_a_fazer"]

    cur.execute(f"""
        SELECT COUNT(*)::int AS total_feito
        FROM public.cronograma_inspecoes cr
        JOIN public.cadastros c ON c.id = cr.cadastro_id
        WHERE {where}
          AND c.ultima_inspecao IS NOT NULL
          AND EXTRACT(YEAR FROM c.ultima_inspecao) = %s
          AND EXTRACT(MONTH FROM c.ultima_inspecao) = %s
    """, vals + [ano, mes])
    feito = cur.fetchone()["total_feito"]

    cur.close()
    conn.close()

    perc = round((feito / total * 100.0), 1) if total else 0.0

    return jsonify({
        "ano": ano,
        "mes": mes,
        "table": [{"mes": mes, "total": int(total), "feito": int(feito), "percentual": perc}],
        "chart": {"labels": ["FEITO", "A FAZER"], "values": [int(feito), max(int(total)-int(feito), 0)]}
    })

# --------- REDESIM por CLASSE ---------
@app.route("/api/estatisticas/redesim_por_classe")
def api_est_redesim_por_classe():
    if "matricula" not in session:
        return jsonify({"error": "não autenticado"}), 401

    ano = int(request.args.get("ano", date.today().year))
    classe = request.args.get("classe") or ""

    filtros = ["r.alvara IS NOT NULL", "EXTRACT(YEAR FROM r.alvara) = %s"]
    vals = [ano]

    if classe:
        filtros.append("r.classe = %s")
        vals.append(classe)

    where = " AND ".join(filtros)

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT COALESCE(NULLIF(r.classe,''), 'SEM CLASSE') AS classe,
               COUNT(*)::int AS total
        FROM public.redesim r
        WHERE {where}
        GROUP BY classe
        ORDER BY total DESC
    """, vals)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({
        "ano": ano,
        "table": rows,
        "chart": {"x": [r["classe"] for r in rows[:10]], "y": [r["total"] for r in rows[:10]]}
    })
    
    
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # localhost usa http
)
# --------- ANALISAR GERAR AUTO TERMO E NOTIFICAÇÃO ---------
@app.route("/notificacao/<int:id>")
def abrir_notificacao(id):

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 🔹 DADOS DO ESTABELECIMENTO
    cur.execute("""
        SELECT *
        FROM cadastros
        WHERE id = %s
    """, (id,))
    cadastro = cur.fetchone()

    # 🔹 PROPRIETÁRIO / RESPONSÁVEL
    cur.execute("""
        SELECT *
        FROM responsavel
        WHERE cadastro_id = %s
        LIMIT 1
    """, (id,))
    responsavel = cur.fetchone()

    # 🔹 RESPONSÁVEL TÉCNICO
    cur.execute("""
        SELECT *
        FROM responsavel_tecnico
        WHERE cadastro_id = %s
        LIMIT 1
    """, (id,))
    rt = cur.fetchone()

    cur.close()
    conn.close()

    from datetime import datetime
    hoje = datetime.now()

    return render_template("notificacao.html",

        licenca_id=id,

        # 🔢 número vazio (JS vai preencher)
        numero_notificacao="",

        # 📍 CAMPOS AUTOMÁTICOS
        campo_02="SRS Montes Claros",
        campo_03="Taiobeiras",

        campo_04=cadastro.get("nome_fantasia"),
        campo_05=cadastro.get("razao_social"),
        campo_06=cadastro.get("cnpj_ou_cpf"),
        campo_08=cadastro.get("cnae_principal"),
        campo_09=cadastro.get("edereco"),

        campo_12="Taiobeiras",
        campo_13="MG",

        # 👤 RESPONSÁVEL
        campo_14=responsavel.get("nome") if responsavel else "",
        campo_20=responsavel.get("cpf") if responsavel else "",
        campo_21=responsavel.get("endereco") if responsavel else "",
        campo_22=responsavel.get("telefone") if responsavel else "",

        # 🧪 RESPONSÁVEL TÉCNICO
        campo_26=rt.get("nome") if rt else "",
        campo_27=rt.get("registro") if rt else "",
        campo_28=rt.get("endereco") if rt else "",
        campo_29=rt.get("telefone") if rt else "",

        # 📅 DATA
        campo_38_dia=hoje.strftime("%d"),
        campo_38_mes=hoje.strftime("%m"),
        campo_38_ano=hoje.strftime("%Y"),

        # 👮 FISCAL
        campo_34_nome_1=cadastro.get("fiscal_responsavel"),
        campo_35_matricula_1=cadastro.get("fiscal_matricula"),
        campo_36_cargo_1="Fiscal Sanitário"
    )
# =========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)



