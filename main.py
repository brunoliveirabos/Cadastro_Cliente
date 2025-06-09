import streamlit as st
import json
import os
import requests
import win32com.client as win32
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DATA_FILE = "data.json"
PASTA_FICHAS = "fichas"

etapas_checklists = {
    "Comercial": ["Enviar proposta", "Confirmar interesse", "Analisar contrato"],
    "Financeiro": ["Conferir documentos", "Aprovar limite", "Emitir cobrança"],
    "Diretoria": ["Avaliar risco", "Aprovar contrato", "Assinar documento"]
}

os.makedirs(PASTA_FICHAS, exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def consultar_cnpj(cnpj):
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def send_email(destinatario, assunto, corpo):
    try:
        outlook = win32.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = destinatario
        mail.Subject = assunto
        mail.Body = corpo
        mail.Send()
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")

def gerar_pdf(nome, info):
    caminho = os.path.join(PASTA_FICHAS, f"{nome}.pdf")
    c = canvas.Canvas(caminho, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "Ficha Cadastral da Empresa")
    c.setFont("Helvetica", 12)

    y = 770
    for chave, valor in info.items():
        if isinstance(valor, dict):
            continue
        c.drawString(50, y, f"{chave}: {valor}")
        y -= 20
        if y < 60:
            c.showPage()
            y = 800

    c.save()
    return caminho

# INÍCIO DA INTERFACE
st.set_page_config(layout="wide")
st.title("Sistema de Aprovação de Cliente")
data = load_data()

menu_option = st.sidebar.selectbox("Menu", ["Painel"])

if menu_option == "Painel":
    st.subheader("Adicionar Novo Cliente")

    with st.form("adicionar_cliente"):
        cnpj = st.text_input("CNPJ")
        promotor = st.text_input("Promotor")
        consultar = st.form_submit_button("Consultar CNPJ e Cadastrar")

    if consultar:
        dados = consultar_cnpj(cnpj)
        if not dados or dados.get("status") == "ERROR":
            st.error("CNPJ inválido ou bloqueado.")
        else:
            nome_cliente = dados["nome"]
            if nome_cliente in data:
                st.warning("Cliente já cadastrado.")
            else:
                cliente_info = {
                    "CNPJ": dados["cnpj"],
                    "Razao Social": dados["nome"],
                    "Nome Fantasia": dados["fantasia"],
                    "Endereço": f"{dados['logradouro']}, {dados['numero']} - {dados['bairro']} - {dados['municipio']}/{dados['uf']}",
                    "CEP": dados["cep"],
                    "Telefone": dados["telefone"],
                    "Email": dados["email"],
                    "Atividade Principal": dados["atividade_principal"][0]["text"],
                    "Situação": dados["situacao"],
                    "Capital Social": dados["capital_social"],
                    "Promotor": promotor
                }
                cliente_info.update({etapa: {item: False for item in itens} for etapa, itens in etapas_checklists.items()})
                data[nome_cliente] = cliente_info
                save_data(data)
                st.success(f"Cliente '{nome_cliente}' cadastrado com sucesso.")

                # Gerar PDF e salvar no session_state para download fora do form
                caminho_pdf = gerar_pdf(nome_cliente, cliente_info)
                st.session_state["caminho_pdf"] = caminho_pdf
                st.session_state["nome_cliente"] = nome_cliente

    # Botão de download fora do form
    if "caminho_pdf" in st.session_state and "nome_cliente" in st.session_state:
        with open(st.session_state["caminho_pdf"], "rb") as f:
            st.download_button(
                label="📄 Baixar ficha em PDF",
                data=f,
                file_name=f"{st.session_state['nome_cliente']}.pdf",
                mime="application/pdf"
            )

    st.divider()
    st.subheader("Status dos Clientes")

    if data:
        selected_cliente = st.selectbox("Selecione um cliente", list(data.keys()))
        if selected_cliente:
            cliente_data = data[selected_cliente]

            for etapa in etapas_checklists:
                if etapa not in cliente_data or not isinstance(cliente_data[etapa], dict):
                    cliente_data[etapa] = {item: False for item in etapas_checklists[etapa]}

            cols = st.columns(len(etapas_checklists))
            for idx, (etapa, checklist) in enumerate(etapas_checklists.items()):
                with cols[idx]:
                    st.markdown(f"### {etapa}")

                    with st.expander("Itens para aprovar", expanded=False):
                        for item in checklist:
                            marcado = st.checkbox(
                                item,
                                value=cliente_data[etapa][item],
                                key=f"{selected_cliente}_{etapa}_{item}"
                            )
                            if marcado != cliente_data[etapa][item]:
                                cliente_data[etapa][item] = marcado
                                data[selected_cliente] = cliente_data
                                save_data(data)

                    status_geral = "✅ Feito" if all(cliente_data[etapa][item] for item in checklist) else "❌ Pendente"
                    st.markdown(f"**Status:** {status_geral}")

                    if st.button(f"Notificar {etapa}", key=f"notificar_{selected_cliente}_{etapa}"):
                        corpo = f"Cliente: {selected_cliente}\nEtapa: {etapa}\n\nDetalhes:\n"
                        for item in checklist:
                            estado = "Feito" if cliente_data[etapa][item] else "Pendente"
                            corpo += f"- {item}: {estado}\n"
                        send_email(
                            destinatario="bruno.oliveira@maiorca.com.br",
                            assunto=f"Status - {etapa} - Cliente {selected_cliente}",
                            corpo=corpo
                        )
                        st.success(f"E-mail enviado para {etapa}")
    else:
        st.warning("Nenhum cliente cadastrado ainda.")
