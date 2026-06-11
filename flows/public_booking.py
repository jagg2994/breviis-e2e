"""Flujos custom del booking público (ver e2e-manifest.yaml)."""

import time


def _select_staff_service(runner, staff_nth):
    """Paso 1 del wizard: especialista + servicio + continuar al calendario."""
    page = runner.page
    page.goto(runner.url("/book/{slug}"), wait_until="domcontentloaded")
    runner.locate("booking-staff-card", staff_nth).click()
    runner.locate("booking-category-header", 0).click()
    runner.locate("booking-service-card", 0).click()
    runner.locate("booking-btn-continue-step1").click()


def _fill_and_submit(runner, name, email, phone):
    runner.locate("booking-btn-continue-step2").click()
    runner.locate("booking-input-name").fill(name)
    runner.locate("booking-input-email").fill(email)
    runner.locate("booking-input-phone").fill(phone)
    runner.locate("booking-btn-submit").click()


def flow_c10(runner, flow):
    """C10 — Anti doble reserva.

    1ª pasada: flujo C1 completo guardando el texto del slot elegido.
    2ª pasada: mismo staff+servicio+fecha. PASS si (a) el slot ya no se
    ofrece en la UI, o (b) se ofrece pero el submit muestra booking-error.
    Las aserciones `esperado` del manifiesto no aplican aquí (la condición
    es disyuntiva): el flujo valida internamente y limpia `esperado`.
    """
    page = runner.page

    # ── 1ª pasada: reservar el primer slot disponible ────────────────────
    _select_staff_service(runner, staff_nth=1)
    slot_text = runner.pick_slot(desde_nth=0)
    fecha = page.locator(".cal-day.selected, [data-testid='booking-date-cell'].selected").first
    fecha_str = fecha.get_attribute("data-date") if fecha.count() else None
    _fill_and_submit(runner, "Cliente Prueba Diez", "e2e-c10@test.breviis.com", "+573001110010")
    page.get_by_test_id("confirmation-content").wait_for(timeout=15000)

    # ── 2ª pasada: mismo staff + servicio + fecha, mismo slot ────────────
    _select_staff_service(runner, staff_nth=1)
    if fecha_str:
        page.locator(f"[data-testid='booking-date-cell'][data-date='{fecha_str}']").click()
    else:
        runner.locate("booking-date-cell", 0).click()
    page.wait_for_timeout(2000)  # carga de chips del día
    chips = page.get_by_test_id("booking-time-chip").filter(visible=True)
    same = chips.filter(has_text=slot_text)

    if same.count() == 0:
        print(f"[C10] slot '{slot_text}' ya no se ofrece tras la 1ª reserva → OK")
        flow["esperado"] = []
        return

    # El slot sigue visible: intentar reservarlo y exigir error claro.
    same.first.click()
    _fill_and_submit(runner, "Cliente Prueba Diez B", "e2e-c10b@test.breviis.com", "+573001110011")
    err = page.get_by_test_id("booking-error")
    err.wait_for(state="visible", timeout=15000)
    print(f"[C10] slot '{slot_text}' rechazado con error visible → OK")
    flow["esperado"] = []
