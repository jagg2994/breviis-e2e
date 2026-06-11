# bot_QA_BREVIIS

Bot Playwright de pruebas E2E de **Breviis**. Corre los flujos declarados en
[e2e-manifest.yaml](e2e-manifest.yaml) (copia sincronizada de
`mvp_breviis/docs/e2e-manifest.yaml`) contra el **entorno develop**
(`https://breviis-dev.oiz33t.easypanel.host`), localizando elementos por
`data-testid` (contrato: `mvp_breviis/docs/E2E_SELECTORS.md`).

## Setup

```bash
pip install -r requirements.txt
python3 -m playwright install chromium
export E2E_SEED_TOKEN=...   # el mismo valor configurado en Easypanel dev
```

## Uso

```bash
python3 bot.py -f A1 --headless          # un flujo
python3 bot.py -f C1 C2 C3 --headless    # varios
python3 bot.py --headless                # todos los del manifiesto
python3 bot.py -f C1                     # con navegador visible (debug)

# Sin seed (credenciales explícitas):
python3 bot.py -f A1 --skip-seed --admin-email x@y.com --admin-password secreto
```

Antes de correr, el bot llama a `POST {base}/api/dev/seed-e2e` con el header
`X-E2E-Seed-Token` y usa las credenciales devueltas (tenant `e2e-demo`).

## Salida

- `output/flow_status/run_<ts>.json` — `{flow_id, status: pass|fail, error, screenshot, seconds}` por flujo.
- `output/debug/*.png` — screenshot full-page de cada fallo.

## Arquitectura

- `bot.py` — runner: interpreta los pasos declarativos del manifiesto
  (`goto/click/fill/select/check/expect_dialog` por `testid` + aserciones
  `visible/texto/url_contiene`).
- `flows/` — flujos `impl: custom` del manifiesto (lógica que no cabe en
  pasos declarativos, ej. C10 anti doble-reserva con dos pasadas).
- Los IDs de flujo (C1, A5, …) son los de `mvp_breviis/docs/E2E_TESTS.md` —
  lenguaje compartido entre repos. Un fallo se reporta como "falló C10".

## Sincronización con mvp_breviis

Los cambios de flujos/testids llegan vía `mvp_breviis/docs/e2e-delta.md`
(workflow `e2e-sync` → `repository_dispatch`, Fase E del plan
`mvp_breviis/docs/NEXT_STEPS.md`). Al recibir un delta: actualizar el
manifiesto vendorizado y los flujos afectados.
