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