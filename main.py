import streamlit as st
import json
import os
import win32com.client
import pythoncom

DATA_FILE = "data.json"
USERS = {"admin": "1234"}  # Usuários permitidos

# Função para carregar os dados
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Função para salvar os dados
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Função para enviar e-mail
def send_email(destinatario, assunto, corpo):
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = destinatario
        mail.Subject = assunto
        mail.Body = corpo
        mail.Send()
    finally:
        pythoncom.CoUninitialize()

# Etapas de checklist
etapas_checklists = {
    "Comercial": ["Enviar proposta", "Confirmar interesse", "Analisar contrato"],
    "Financeiro": ["Conferir documentos", "Aprovar limite", "Emitir cobrança"],
    "Diretoria": ["Avaliar risco", "Aprovar contrato", "Assinar documento"]
}

# Login
def login():
    if "login" not in st.session_state:
        st.session_state.login = False

    if not st.session_state.login:
        st.title("Login")
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if USERS.get(username) == password:
                st.session_state.login = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
        st.stop()

# Início do app
login()
data = load_data()
st.title("Sistema de Aprovação de Cliente")

menu_option = st.sidebar.selectbox("Escolha uma opção", ["Tela Inicial", "Adicionar Cliente"])

if menu_option == "Tela Inicial":
    st.subheader("Clientes Registrados")

    if data:
        selected_cliente = st.selectbox("Selecione um cliente", list(data.keys()))
        if selected_cliente:
            cliente_data = data.get(selected_cliente, {})

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

elif menu_option == "Adicionar Cliente":
    st.subheader("Adicionar Novo Cliente")
    nome_cliente = st.text_input("Nome do Cliente")
    cnpj = st.text_input("CNPJ")
    promotor = st.text_input("Promotor")

    if st.button("Cadastrar Cliente"):
        if nome_cliente.strip() == "":
            st.warning("Nome não pode estar vazio.")
        elif nome_cliente in data:
            st.warning("Cliente já cadastrado.")
        else:
            data[nome_cliente] = {
                "CNPJ": cnpj,
                "Promotor": promotor,
                **{etapa: {item: False for item in itens} for etapa, itens in etapas_checklists.items()}
            }
            save_data(data)
            st.success(f"Cliente '{nome_cliente}' cadastrado com sucesso.")


# o windows não pode encontrar streamlit certifique de que o nome foi digitado corretamente