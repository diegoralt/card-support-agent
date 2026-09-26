import streamlit as st

from agent import MAX_MESSAGE_CHARS, MAX_USER_MESSAGES, chat, confirm_block, db, start_session

st.set_page_config(page_title="Tarjeta Nube · Soporte", page_icon="💳")


@st.cache_data
def load_customers():
    with db() as conn:
        rows = conn.execute(
            "select c.id, c.name, c.kyc_status, k.last4 "
            "from customers c join cards k on k.customer_id = c.id order by c.id").fetchall()
    return [dict(zip(["id", "name", "kyc_status", "last4"], r)) for r in rows]


def new_conversation(customer_id):
    st.session_state.session = start_session(customer_id, origin="demo")
    st.session_state.log = []  # solo lo que se muestra: (rol, texto)


customers = load_customers()

with st.sidebar:
    st.header("Cliente de prueba")
    customer = st.selectbox(
        "Elige un cliente sintético", customers,
        format_func=lambda c: f"{c['name']} · •••• {c['last4']}"
                              + (" · KYC pendiente" if c["kyc_status"] == "pending" else ""))
    if st.button("Nueva conversación", use_container_width=True):
        new_conversation(customer["id"])

    st.divider()
    st.caption("Prueba, por ejemplo:")
    st.caption("• ¿Hasta qué día puedo pagar?\n\n"
               "• ¿Qué cargos tengo del 10 al 15 de septiembre?\n\n"
               "• Me robaron la cartera, bloquea mi tarjeta.\n\n"
               "• No reconozco un cargo, quiero una aclaración.")

# Streamlit vuelve a ejecutar todo el script en cada interacción: lo que debe sobrevivir
# entre ejecuciones vive en st.session_state (una por pestaña del navegador).
if "session" not in st.session_state or st.session_state.session.customer["id"] != customer["id"]:
    new_conversation(customer["id"])
session = st.session_state.session

st.title("💳 Tarjeta Nube · Soporte")
st.info("Demo con datos 100 % ficticios. No ingreses datos personales ni de tarjetas reales.", icon="ℹ️")

card_status = "bloqueada en esta sesión" if session.card_blocked else "activa"
remaining = MAX_USER_MESSAGES - session.user_messages
st.caption(f"Tarjeta •••• {customer['last4']} · {card_status} · {remaining} mensajes restantes")

for role, text in st.session_state.log:
    with st.chat_message(role):
        st.markdown(text)

# Compuerta: solo este clic bloquea; el LLM nunca llama confirm_block.
if session.pending_action:
    with st.container(border=True):
        st.warning("El bloqueo es definitivo: una tarjeta bloqueada no se puede reactivar.", icon="⚠️")
        if st.button("Confirmar bloqueo", type="primary"):
            st.session_state.log.append(("assistant", confirm_block(session)))
            st.rerun()

text = st.chat_input(
    "Escribe tu pregunta…" if remaining > 0 else "Llegaste al límite de mensajes de esta demo",
    max_chars=MAX_MESSAGE_CHARS, disabled=remaining <= 0)

if text:
    st.session_state.log.append(("user", text))
    with st.chat_message("user"):
        st.markdown(text)
    with st.chat_message("assistant"), st.spinner("Pensando…"):
        out = chat(session, text)
    st.session_state.log.append(("assistant", out["text"]))
    st.rerun()  # vuelve a dibujar con el botón de confirmación si quedó un bloqueo pendiente
