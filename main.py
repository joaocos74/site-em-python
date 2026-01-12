from flask import Flask, render_template, redirect, request, flash
import json


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
    
    
if __name__ == "__main__":
    app.run(debug=True)
    