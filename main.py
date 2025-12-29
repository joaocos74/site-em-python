from flask import Flask, render_template, redirect, request, flash


app = Flask(__name__)
app.config['SECRET_KEY'] = 'joao paulo'

@app.route("/")
def home():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def login():
    
    nome = request.form.get('nome')
    senha = request.form.get('senha')
    print(nome)
    print(senha)
    
    if nome == 'admin' and senha == '1234':
        return render_template('usuarios.html')   
    else:
        flash('Usuário ou senha inválido!')
        
        return redirect('/')




















if __name__ == "__main__":
    app.run(debug=True)
    