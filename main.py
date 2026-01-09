from flask import Flask, render_template, redirect, request, flash
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'joao paulo'


@app.route("/")
def home():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def login():

    
    nome = request.form.get('matricula')
    
    if nome == 'adm':
        return render_template('abas.html')
    else:
        flash('Matrícula inválida. Tente novamente.')
        return redirect('/')








if __name__ == "__main__":
    app.run(debug=True)
    