from flask import Flask, render_template, redirect, request, flash
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'joao paulo'

logado = False

@app.route("/")
def home():
    global logado
    logado = False
    return render_template("login.html")

@app.route('/admin')
def admin():
    if logado == True:    
        return render_template('admin.html')
    if not logado == False:
        return redirect('login.html')

@app.route('/login', methods=['POST'])
def login():
    global logado
    
    nome = request.form.get('nome')
    senha = request.form.get('senha')
    
    with open('usuarios.json') as usuariosTemp:
        usuarios = json.load(usuariosTemp)
        cont = 0
        
        for usuario in usuarios:
            cont += 1
            if nome == 'adm' and senha == '123':
                logado = True
                return redirect('/admin')   
            if usuario['nome'] == nome and usuario['senha'] == senha:
                return render_template('usuarios.html')
            if cont >= len(usuarios):
                flash('Usuário ou senha incorretos!')
                return redirect('/')    
       
@app.route('/cadastrarusuario', methods=['POST'])
def cadastrarusuario():
    user = []
    nome = request.form.get('nome')
    senha = request.form.get('senha')
    user = [
        {
            "nome": nome,
            "senha": senha
        }
    ] 
    with open('usuarios.json') as usuariosTemp:
        usuarios = json.load(usuariosTemp)

    usuarioNovo = usuarios + user
    
    with open('usuarios.json', 'w') as gravarTemp:
        json.dump(usuarioNovo, gravarTemp, indent=4)

    return redirect('/admin')












if __name__ == "__main__":
    app.run(debug=True)
    