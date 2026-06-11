# CLAUDE.md — bot_QA_BREVIIS

Bot Playwright (Python, API sync) de pruebas E2E de Breviis. Corre contra el
**entorno develop** (`https://breviis-dev.oiz33t.easypanel.host`), nunca prod.

## Reglas
- **Selectores:** SIEMPRE `page.get_by_test_id(...)` (los `data-testid` son
  contrato con `mvp_breviis` — ver su `docs/E2E_SELECTORS.md`). `get_by_role`/
  `get_by_label` como segunda opción. CSS solo como último recurso comentado.
- **Manifiesto:** `e2e-manifest.yaml` es copia de
  `mvp_breviis/docs/e2e-manifest.yaml` — no editarlo acá sin reflejar el
  cambio allá (fuente de verdad: mvp_breviis).
- **IDs de flujo** (C1, A5, E1…) = los de `mvp_breviis/docs/E2E_TESTS.md`.
- **No validar inboxes** (email/WhatsApp): solo estado observable en UI.
- **Seed primero:** `POST /api/dev/seed-e2e` con header `X-E2E-Seed-Token`
  (env `E2E_SEED_TOKEN`); usar las credenciales de la respuesta.
- `output/` está gitignorado: nunca commitear evidencia.

## Comandos
```bash
pip install -r requirements.txt && python3 -m playwright install chromium
python3 bot.py -f A1 --headless     # correr un flujo
python3 bot.py --headless           # suite completa
```

## Plan de trabajo
El roadmap vive en `mvp_breviis/docs/NEXT_STEPS.md` (Fases D y E) con su
bitácora `NEXT_STEPS_NOTES.md` — leerla antes de ejecutar tareas.
Pendientes: D2 (flujos C1–C3, C10), D3 (A5–A9), D4 (workflow CI `run-e2e.yml`
+ issue de fallo en mvp_breviis con label `e2e-failure`).
