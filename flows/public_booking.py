"""Flujos custom del booking público (ver e2e-manifest.yaml)."""


def flow_c10(runner, flow):
    """C10 — Anti doble reserva: pendiente de implementar en D2.

    Diseño (manifiesto): 1ª pasada = C1 completo guardando staff+fecha+slot;
    2ª pasada con el mismo trío — si el slot ya no se ofrece en la UI → PASS;
    si se ofrece y el submit muestra booking-error → PASS.
    """
    raise NotImplementedError("C10 se implementa en la tarea D2 del plan")
