from uuid import uuid4

from langgraph.types import Command

from src.graph.persistence import (
    build_thread_config,
    open_checkpointer,
)
from src.graph.state import create_initial_state
from src.graph.workflow import build_workflow


thread_id = f"fitfamily-approval-demo-{uuid4().hex[:8]}"

state = create_initial_state(
    run_id=thread_id,
    brief={
        "business_type": "gimnasio con ludoteca",
        "location": "Madrid",
        "study_area": "El Cañaveral",
        "questions": [],
    },
)

with open_checkpointer() as checkpointer:
    graph = build_workflow(checkpointer=checkpointer)
    config = build_thread_config(thread_id)

    # Primera ejecución: investiga, analiza, redacta y revisa.
    result = graph.invoke(state, config=config)

    snapshot = graph.get_state(config)

    if snapshot.interrupts:
        print("El informe necesita aprobación humana:")

        for item in snapshot.interrupts:
            print(item.value)

        # En una aplicación real, esta decisión debe recibirse
        # de la interfaz o del controlador después de la revisión humana.
        decision = input(
            "Escribe 'approved' o 'rejected': "
        ).strip().lower()

        if decision not in ("approved", "rejected"):
            raise ValueError("Decisión no válida.")

        report_version_id = snapshot.values["report_version_id"]

        result = graph.invoke(
            Command(
                resume={
                    "decision": decision,
                    "report_version_id": report_version_id,
                }
            ),
            config=config,
        )

        print("Estado final:", result.get("status"))
        print("Decisión:", result.get("approval_decision"))
        print(
            "Versión aprobada:",
            result.get("approved_version_id"),
        )
    else:
        status = result.get("status")
        print("Estado final:", status)

        if status == "failed":
            print("El informe no ha superado la revisión.")
        else:
            print("No hay ninguna aprobación pendiente.")
