from flask import Flask, render_template, redirect, request, flash, jsonify
import json
import mysql.connector


app = Flask(__name__)
app.config['SECRET_KEY'] = 'joao paulo'

logado = False

@app.route("/")
def home():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def login():

    
    nome = request.form.get('matricula')
    
    with open('usuarios.json') as usuarioscadastrados:
        usuarios = json.load(usuarioscadastrados)
        cont = 0
        for usuario in usuarios:
            cont += 1
            if usuario['nome'] == nome:
                return render_template('abas.html')
            
        if cont >= len(usuarios):
            flash('Matrícula não cadastrada!')
            return redirect('/')

    
@app.route("/cadastrar", methods=['GET'])
def cadastrar():
    return render_template("login_adm.html")

@app.route('/administrador', methods=['POST'])
def administrador():
    nome = request.form.get('cadastro')
    
    if not nome:
        return redirect('/cadastrar')
    
    with open('usuarios.json', 'r', encoding='utf-8') as usarioscadastrados:
        usuarios = json.load(usarioscadastrados)
    
    for usuario in usuarios:
        if usuario['nome']. lower() == nome. lower():
            flash('Matrícula já cadastrada!')
            return redirect('/cadastrar')    
    novo_usuario = {
        'nome': nome
    }
    usuarios.append(novo_usuario)
    with open('usuarios.json', 'w', encoding='utf-8') as usarioscadastrados:
        json.dump(usuarios, usarioscadastrados, indent=3, ensure_ascii=False)
        
    return redirect('/')

@app.route("/abas")
def abas():
    if logado == True:
        return render_template("abas.html")
    if logado == False:
        return render_template("login.html")
    

@app.route('/mapa', methods=['POST'])
def mapa():
    return render_template("mapa.html")

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="visaTaio@2026",
        database="sytemvisataio"
    )

@app.route("/estabelecimentos")
def estabelecimentos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
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
        DATE_FORMAT(ultima_inspecao, '%Y-%m-%d') AS ultima_inspecao,
        alvara,
        vigi_risco,
        observacoes
    FROM cadastros
    WHERE latitude IS NOT NULL
      AND longitude IS NOT NULL
    """)

    dados = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(dados)

@app.route("/pesquisar_estabelecimentos", methods=["GET"])
def pesquisar_estabelecimentos():

    campos = {
        "id": "id",
        "nivel": "nivel",
        "classe": "classe",
        "razao_social": "razao_social",
        "nome_fantasia": "nome_fantasia",
        "endereco": "endereco",
        "cnpj_ou_cpf": "cnpj_ou_cpf",
        "cnae": "cnae",
        "numero_parecer_tecnico": "parecer",
        "ultima_inspecao": "ultima_inspecao",
        "alvara": "alvara",
        "vigi_risco": "vigi_risco",
        "observacoes": "observacoes",
        "baixados": "baixados",
        "excluidos": "excluidos",
        "fiscal_responsavel": "fiscal_responsavel"
    }

    filtros = []
    valores = []

    for campo_html, campo_db in campos.items():
        valor = request.args.get(campo_html)
        if valor:
            filtros.append(f"{campo_db} LIKE %s")
            valores.append(f"%{valor}%")

    sql = "SELECT * FROM cadastros"

    if filtros:
        sql += " WHERE " + " AND ".join(filtros)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, valores)

    licencas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "abas.html",
        licencas=licencas
    )

@app.route("/usuarios")
def usuarios():
    if logado == True:
        return render_template("usuarios.html")
    if logado == False:
        return render_template("login.html")


@app.route('/licencas/<int:licenca_id>/analisar', methods=['GET', 'POST'])
def analisar_licenca(licenca_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Atualiza campo específico
        campo = request.form.get('campo')
        valor = request.form.get('valor')
        
        if campo:
            cursor.execute(f"""
                UPDATE cadastros 
                SET {campo} = %s 
                WHERE id = %s
            """, (valor, licenca_id))
            conn.commit()
            
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Atualizado!"})
        
        cursor.close()
        conn.close()
        return jsonify({"success": False}), 400

    # GET: busca dados completos
    cursor.execute("""
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
        DATE_FORMAT(ultima_inspecao, '%Y-%m-%d') AS ultima_inspecao,
        alvara,
        vigi_risco,
        observacoes
    FROM cadastros
        WHERE id = %s
    """, (licenca_id,))
    
    licenca = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not licenca:
        return "Licença não encontrada", 404

    return render_template('usuarios.html', licenca=licenca)



if __name__ == "__main__":
    app.run(debug=True)
    