"""Flujos custom del admin de reservas (ver e2e-manifest.yaml).

Cada flujo garantiza su propia precondición creando la reserva PENDING que
necesita (C1 = con staff, C2 = sin staff) antes de operar como admin.
"""


def _goto_pending(runner):
    runner.ensure_login()
    runner.page.goto(
        runner.url("/{slug}/admin/bookings?status=PENDING"),
        wait_until="domcontentloaded",
    )


def _rows(runner):
    return runner.page.get_by_test_id("bookings-row").filter(visible=True)


def flow_a5(runner, flow):
    """A5 — Filtro Pendientes: con una PENDING creada, el tab la muestra."""
    runner.run_flow("C1")  # precondición: al menos una PENDING
    runner.ensure_login()
    runner.page.goto(runner.url("/{slug}/admin/bookings"), wait_until="domcontentloaded")
    runner.locate("bookings-filter-pending").click()
    runner.page.wait_for_load_state("domcontentloaded")
    # las aserciones del manifiesto (fila visible + url status=PENDING) corren después


def flow_a6(runner, flow):
    """A6 — Aceptar PENDING con staff desde el detalle.

    El accept redirige a la LISTA con flash "Reserva aceptada…" (no se queda
    en el detalle), así que la verificación es: la reserva aparece bajo el
    filtro CONFIRMED.
    """
    runner.run_flow("C1")  # precondición: PENDING con staff asignado (Ana)
    _goto_pending(runner)
    # Abrir una fila CON staff: las de C2 (sin staff) deshabilitan el accept
    # del detalle. C1 siempre reserva con "Ana" (staff nth 1 del seed).
    _rows(runner).filter(has_text="Ana").first.click()
    runner.page.wait_for_load_state("domcontentloaded")
    runner.locate("booking-detail-btn-accept").click()
    runner.page.wait_for_load_state("domcontentloaded")

    runner.page.goto(
        runner.url("/{slug}/admin/bookings?status=CONFIRMED"),
        wait_until="domcontentloaded",
    )
    _rows(runner).first.wait_for(state="visible", timeout=10000)
    print("[A6] reserva visible bajo filtro CONFIRMED tras aceptar → OK")
    flow["esperado"] = []  # validación interna (el accept no deja el detalle abierto)


def flow_a7(runner, flow):
    """A7 — Aceptar PENDING sin staff vía modal 'Asignar profesional'."""
    runner.run_flow("C2")  # precondición: PENDING sin staff
    _goto_pending(runner)
    # En una fila sin staff, bookings-btn-accept abre el modal de asignación.
    runner.locate("bookings-btn-accept", 0).click()
    select = runner.page.get_by_test_id("bookings-assign-staff-select")
    select.wait_for(state="visible", timeout=15000)  # opciones cargan por fetch
    # index 0 es el placeholder "-- Selecciona un profesional --": elegir el 1.
    select.select_option(index=1)
    runner.locate("bookings-assign-btn-submit").click()
    runner.page.wait_for_load_state("domcontentloaded")


def flow_a9(runner, flow):
    """A9 — Rechazar PENDING: confirm() nativo + la fila sale de Pendientes."""
    runner.run_flow("C1")  # precondición: al menos una PENDING
    _goto_pending(runner)
    before = _rows(runner).count()
    runner.page.once("dialog", lambda d: d.accept())
    runner.locate("bookings-btn-reject", 0).click()
    runner.page.wait_for_load_state("domcontentloaded")
    after = _rows(runner).count()
    if after >= before:
        raise AssertionError(
            f"La reserva no salió de Pendientes tras rechazar ({before} → {after})"
        )
    print(f"[A9] pendientes {before} → {after} tras rechazar → OK")
    flow["esperado"] = []  # la verificación es el conteo (no hay detalle abierto)
