"""Presupuesto local del redactor: entrada, salida y separación de peticiones."""

from collections import deque
from threading import Lock
import time

from litellm import token_counter


WRITER_ROLE = "Redactor de informes de mercado"
WRITER_MAX_OUTPUT_TOKENS = 4096
# Margen respecto a los 8000 TPM observados; incluye salida reservada.
WRITER_REQUEST_TOKEN_LIMIT = 7600
# Reserva adicional para los mensajes e instrucciones que añade CrewAI.
WRITER_TASK_TOKEN_LIMIT = 3000
_reservations = deque()
_reservation_lock = Lock()


def count_writer_tokens(messages, model: str) -> int:
    """Cuenta localmente; no llama al proveedor ni requiere una clave API."""
    return token_counter(model=model, messages=messages)


def reserve_writer_tokens(tokens: int) -> None:
    """Evita acumular más presupuesto del permitido en el mismo proceso."""
    if tokens > WRITER_REQUEST_TOKEN_LIMIT:
        raise ValueError("La petición del redactor supera el presupuesto de tokens.")
    with _reservation_lock:
        while True:
            now = time.monotonic()
            while _reservations and now - _reservations[0][0] >= 61:
                _reservations.popleft()
            if sum(item[1] for item in _reservations) + tokens <= WRITER_REQUEST_TOKEN_LIMIT:
                _reservations.append((now, tokens))
                return
            time.sleep(max(0.01, 61 - (now - _reservations[0][0])))
