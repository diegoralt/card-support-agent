import html
import re
import threading
import time
from pathlib import Path

import streamlit as st

from agent import MAX_MESSAGE_CHARS, MAX_USER_MESSAGES, chat, confirm_block, db, start_session

st.set_page_config(page_title="Soporte Tarjeta Nube", page_icon=":material/credit_card:")

# Tope global: el de 20 mensajes es por pestaña y recargar abre otra sesión. Con esto un
# script puede gastar a lo más esto por día (UTC) sin agotar el crédito de la clave.
DAILY_BUDGET_USD = 0.50
SUGGESTIONS = [
    "¿Hasta qué día puedo pagar?",
    "¿Qué cargos tengo del 10 al 15 de septiembre?",
    "Me robaron la cartera, bloquea mi tarjeta.",
    "No reconozco un cargo, quiero una aclaración.",
]
# Lo que hizo el agente en el turno, en palabras del cliente (una vez por tool).
TOOL_LABELS = {
    "search_policies": ":material/menu_book: Consultó las políticas",
    "get_transactions": ":material/receipt_long: Revisó tus movimientos",
    "block_card": ":material/lock: Preparó el bloqueo",
    "escalate_to_human": ":material/support_agent: Creó un ticket para un asesor",
}
AVATARS = {"user": ":material/person:", "assistant": ":material/support_agent:"}
CITATION = re.compile(r"\[([\w-]+\.md)\s*[—–-]\s*([^\]]+)\]")

CARD_CSS = """<style>
.tn-card { aspect-ratio: 1.586; max-width: 340px; box-sizing: border-box; padding: 20px 22px;
  border-radius: 16px; color: #F3F5FB; display: flex; flex-direction: column;
  justify-content: space-between; box-shadow: 0 14px 28px -16px rgba(28,36,48,.55);
  background: radial-gradient(ellipse at 88% 8%, rgba(255,255,255,.20), transparent 55%),
              linear-gradient(160deg, #3A4DA6, #243275); }
.tn-card.blocked { background: linear-gradient(160deg, #6B7482, #474E59); }
.tn-brand { font-family: "Bricolage Grotesque", sans-serif; font-weight: 800; font-size: 21px; }
.tn-number { font-size: 19px; letter-spacing: .14em; font-variant-numeric: tabular-nums; }
.tn-row { display: flex; justify-content: space-between; align-items: end; gap: 12px; }
.tn-holder { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; opacity: .9; }
.tn-state { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
  background: rgba(255,255,255,.16); white-space: nowrap; }
.tn-card.blocked .tn-state { background: #B3261E; }
</style>"""


@st.cache_data
def load_customers():
    with db() as conn:
        rows = conn.execute(
            "select c.id, c.name, c.kyc_status, k.last4 "
            "from customers c join cards k on k.customer_id = c.id order by c.id").fetchall()
    return [dict(zip(["id", "name", "kyc_status", "last4"], r)) for r in rows]


@st.cache_data
def policy_titles():
    """archivo.md → título legible, tomado del `# ` de cada política."""
    return {p.name: p.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").split(" · ")[0]
            for p in Path("docs/politicas").glob("*.md")}


def render_answer(text):
    """Las citas [archivo — sección] se muestran como etiqueta de fuente."""
    titles = policy_titles()
    return CITATION.sub(lambda m: f":blue-badge[:material/description: "
                                  f"{titles.get(m[1], m[1])}, {m[2].strip()}]", text)


def show_message(role, text, tools=()):
    with st.chat_message(role, avatar=AVATARS[role]):
        st.markdown(render_answer(text) if role == "assistant" else text)
        done = [TOOL_LABELS[t] for t in dict.fromkeys(tools) if t in TOOL_LABELS]
        if done:
            st.caption("   ".join(done))


def chat_with_timer(session, text):
    """Corre el turno en un hilo y muestra los segundos en español (el contador de
    st.spinner viene fijo en inglés). El agente no reporta sus pasos: solo el tiempo."""
    result = {}

    def run():
        try:
            result["out"] = chat(session, text)  # chat() no usa st: seguro fuera del hilo de Streamlit
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    t0 = time.monotonic()
    with st.spinner("Revisando tu solicitud…"):
        elapsed = st.empty()
        while thread.is_alive():
            elapsed.caption(f"Llevas {int(time.monotonic() - t0)} s. Suele tardar entre 5 y 20 s.")
            thread.join(0.5)
    if "error" in result:
        raise result["error"]
    return result["out"]


def card_html(customer, blocked):
    name = html.escape(customer["name"])
    return (f'{CARD_CSS}<div class="tn-card{" blocked" if blocked else ""}" role="img" '
            f'aria-label="Tarjeta terminación {customer["last4"]}, {"bloqueada" if blocked else "activa"}">'
            f'<div class="tn-brand">Tarjeta Nube</div>'
            f'<div class="tn-number">•••• •••• •••• {customer["last4"]}</div>'
            f'<div class="tn-row"><span class="tn-holder">{name}</span>'
            f'<span class="tn-state">{"Bloqueada" if blocked else "Activa"}</span></div></div>')


def new_conversation(customer_id):
    st.session_state.session = start_session(customer_id, origin="demo")
    st.session_state.log = []  # solo lo que se muestra: (rol, texto, tools)


customers = load_customers()

# En la página y no en la barra lateral: en celular la barra se oculta y nadie descubre
# que hay más clientes.
pick, reset = st.columns([2, 1], vertical_alignment="bottom")
customer = pick.selectbox(
    "Estás probando como", customers,
    format_func=lambda c: f"{c['name']}, •••• {c['last4']}",
    help="Clientes ficticios: cada uno tiene movimientos y un cargo que no reconoce. "
         "Renata tiene la verificación de identidad pendiente.")
if reset.button("Nueva conversación", icon=":material/refresh:", width="stretch"):
    new_conversation(customer["id"])

# Streamlit vuelve a ejecutar todo el script en cada interacción: lo que debe sobrevivir
# entre ejecuciones vive en st.session_state (una por pestaña del navegador).
if "session" not in st.session_state or st.session_state.session.customer["id"] != customer["id"]:
    new_conversation(customer["id"])
session = st.session_state.session
remaining = MAX_USER_MESSAGES - session.user_messages

left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")
with left:
    st.html(card_html(customer, session.card_blocked))
with right:
    st.title(f"Hola, {customer['name'].split()[0]}")
    st.markdown(":material/verified_user: Identidad verificada" if customer["kyc_status"] == "approved"
                else ":orange[:material/pending: Verificación de identidad pendiente]")
    st.markdown(f":material/forum: Te quedan {remaining} mensajes en esta demo")
    # Folios reales de la BD: la UI no depende de cómo lo redacte el agente.
    with db() as conn:
        folios = [f"#{r[0]}" for r in conn.execute(
            "select id from tickets where session_id = %s order by id", (session.id,))]
    # El aviso se pide en el turno que creó el ticket y se muestra tras el rerun, ya con el folio.
    if st.session_state.pop("ticket_toast", False) and folios:
        st.toast(f"Ticket {folios[-1]} creado. Un asesor te contactará.", icon=":material/support_agent:")
    if folios:
        st.markdown(f":material/support_agent: Ticket {', '.join(folios)} abierto con un asesor"
                    if len(folios) == 1 else
                    f":material/support_agent: Tickets {', '.join(folios)} abiertos con un asesor")
st.caption(":material/info: Demo con datos 100 % ficticios. "
           "No escribas datos personales ni de tarjetas reales.")

# chat_input queda fijo abajo sin importar dónde se llame; se lee antes para ocultar los
# ejemplos en cuanto hay una pregunta en curso (si no, la respuesta queda fuera de vista).
# ponytail: se lee antes de cada turno; turnos simultáneos pueden rebasarlo por centavos.
with db() as conn:
    (spent_today,) = conn.execute(
        "select coalesce(sum(cost_usd), 0) from llm_calls "
        "where origin = 'demo' and created_at >= date_trunc('day', now())").fetchone()
open_today = spent_today < DAILY_BUDGET_USD
if not open_today:
    st.warning("La demo alcanzó su límite de uso de hoy. Vuelve mañana.", icon=":material/schedule:")

text = st.chat_input(
    "Escribe tu pregunta…" if remaining > 0 else "Llegaste al límite de mensajes de esta demo",
    max_chars=MAX_MESSAGE_CHARS, disabled=remaining <= 0 or not open_today) \
    or st.session_state.pop("suggestion", None)
if not open_today:
    text = None  # también descarta una sugerencia presionada justo antes del corte

if not st.session_state.log and not text and open_today:
    st.subheader("¿En qué te ayudo?")
    cols = st.columns(2)
    for i, s in enumerate(SUGGESTIONS):
        # on_click corre antes del rerun: la pregunta llega al script en la misma pasada.
        cols[i % 2].button(s, key=f"suggestion-{i}", width="stretch",
                           on_click=st.session_state.update, kwargs={"suggestion": s})

for role, message, tools in st.session_state.log:
    show_message(role, message, tools)

# Compuerta: solo este clic bloquea; el LLM nunca llama confirm_block.
if session.pending_action:
    with st.container(border=True):
        st.markdown(":red[**El bloqueo es definitivo.**] Una tarjeta bloqueada no se puede "
                    "reactivar; recibirás una nueva. Si no quieres bloquearla, solo escribe otro mensaje.")
        # El system prompt nombra este botón: "Confirmar bloqueo". Si cambia aquí, cambia allá.
        if st.button("Confirmar bloqueo", type="primary", icon=":material/lock:"):
            st.session_state.log.append(("assistant", confirm_block(session), []))
            st.rerun()

if text:
    st.session_state.log.append(("user", text, []))
    show_message("user", text)
    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        out = chat_with_timer(session, text)
    st.session_state.log.append(("assistant", out["text"], out["tools"]))
    st.session_state.ticket_toast = "escalate_to_human" in out["tools"]
    st.rerun()  # vuelve a dibujar con el botón de confirmación si quedó un bloqueo pendiente
