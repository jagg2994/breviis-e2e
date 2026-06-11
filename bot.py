#!/usr/bin/env python3
"""
bot_QA_BREVIIS — bot de pruebas E2E de Breviis.

Corre los flujos declarados en e2e-manifest.yaml (copia sincronizada de
mvp_breviis/docs/e2e-manifest.yaml) contra el entorno develop, localizando
elementos por data-testid (contrato: mvp_breviis/docs/E2E_SELECTORS.md).

Uso:
    python3 bot.py -f A1 C1 --headless
    python3 bot.py -f C10 --base-url https://breviis-dev.oiz33t.easypanel.host
    python3 bot.py --skip-seed --admin-email x@y.com --admin-password secreto

Antes de correr flujos llama a POST {base}/api/dev/seed-e2e con el header
X-E2E-Seed-Token (env E2E_SEED_TOKEN) y usa las credenciales de la respuesta.
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import certifi

import yaml
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        return json.load(f)


def load_manifest(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_seed(base_url, token):
    """POST /api/dev/seed-e2e → dict con slug, adminEmail, adminPassword."""
    req = urllib.request.Request(
        base_url.rstrip("/") + "/api/dev/seed-e2e",
        method="POST",
        headers={"X-E2E-Seed-Token": token, "Accept": "application/json"},
    )
    # El Python de macOS no trae CAs configurados para urllib: usar certifi.
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        body = json.loads(resp.read().decode())
    if not body.get("success"):
        raise RuntimeError(f"Seed falló: {body}")
    return body["data"]


class Runner:
    """Ejecuta flujos del manifiesto. Los `impl: custom` se delegan a flows/."""

    def __init__(self, page, manifest, ctx):
        self.page = page
        self.manifest = manifest
        self.ctx = ctx  # base_url, tenant_slug, admin_email, admin_password
        self.logged_in = False

    # ── helpers ──────────────────────────────────────────────────────────

    def url(self, path):
        path = path.replace("{slug}", self.ctx["tenant_slug"])
        return self.ctx["base_url"].rstrip("/") + path

    def fill_value(self, valor):
        for key in ("admin_email", "admin_password", "tenant_slug"):
            valor = valor.replace("{" + key + "}", str(self.ctx.get(key, "")))
        return valor.replace("{slug}", self.ctx["tenant_slug"])

    def locate(self, testid, nth=0):
        """N-ésimo elemento VISIBLE con ese data-testid."""
        if testid == "booking-date-cell":
            # Las celdas de días pasados llevan .disabled y no tienen onclick:
            # el nth cuenta solo celdas elegibles.
            loc = self.page.locator('[data-testid="booking-date-cell"]:not(.disabled)')
        else:
            loc = self.page.get_by_test_id(testid)
        return loc.filter(visible=True).nth(nth)

    def pick_slot(self, desde_nth=0, max_dias=6):
        """Clickea celdas de fecha en orden hasta que aparezcan chips de hora
        y elige el primero. Cubre días cerrados (domingo del seed) y días con
        slots agotados (fin de jornada). Devuelve el texto del slot elegido."""
        for n in range(desde_nth, desde_nth + max_dias):
            cell = self.locate("booking-date-cell", n)
            if cell.count() == 0:
                break
            cell.click()
            chips = self.page.get_by_test_id("booking-time-chip").filter(visible=True)
            try:
                chips.first.wait_for(timeout=6000)
            except Exception:
                continue  # sin horarios este día: probar el siguiente
            slot_text = chips.first.inner_text().strip()
            chips.first.click()
            return slot_text
        raise AssertionError(
            f"Sin slots disponibles en {max_dias} días desde la celda {desde_nth}"
        )

    # ── ejecución ────────────────────────────────────────────────────────

    def ensure_login(self):
        if self.logged_in:
            return
        self.run_flow("A1")
        self.logged_in = True

    def run_flow(self, flow_id):
        flow = self.manifest["flows"][flow_id]
        if flow.get("requiere_login"):
            self.ensure_login()

        if flow.get("impl") == "custom":
            from flows import CUSTOM

            if flow_id not in CUSTOM:
                raise NotImplementedError(
                    f"Flujo {flow_id} es impl:custom y no está en flows/ todavía"
                )
            CUSTOM[flow_id](self, flow)
        else:
            self.run_declarative(flow)

        self.assert_expected(flow)

    def run_declarative(self, flow):
        expecting_dialog = False
        for paso in flow.get("pasos", []):
            accion = paso.get("accion")
            if accion is None:
                continue  # paso de solo nota (documentación)
            if accion == "goto":
                self.page.goto(self.url(flow["entrada"]), wait_until="domcontentloaded")
            elif accion == "expect_dialog":
                self.page.once("dialog", lambda d: d.accept())
                expecting_dialog = True
            elif accion == "click":
                self.locate(paso["testid"], paso.get("nth", 0)).click()
                if expecting_dialog:
                    expecting_dialog = False
                self.page.wait_for_load_state("domcontentloaded")
            elif accion == "pick_slot":
                self.pick_slot(paso.get("desde_nth", 0))
            elif accion == "fill":
                self.locate(paso["testid"], paso.get("nth", 0)).fill(
                    self.fill_value(paso["valor"])
                )
            elif accion == "select":
                loc = self.locate(paso["testid"])
                loc.select_option(index=paso.get("nth", 0))
            elif accion == "check":
                self.locate(paso["testid"], paso.get("nth", 0)).check()
            else:
                raise ValueError(f"Acción desconocida en manifiesto: {accion}")

    def assert_expected(self, flow):
        for exp in flow.get("esperado", []):
            tipo = exp["tipo"]
            if tipo == "visible":
                expect(self.locate(exp["testid"])).to_be_visible(timeout=10000)
            elif tipo == "texto":
                expect(self.locate(exp["testid"])).to_contain_text(
                    exp["valor"], timeout=10000
                )
            elif tipo == "url_contiene":
                expect(self.page).to_have_url(
                    lambda u, frag=exp["valor"]: frag in u, timeout=10000
                ) if False else self._assert_url_contains(exp["valor"])
            else:
                raise ValueError(f"Aserción desconocida: {tipo}")

    def _assert_url_contains(self, frag, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if frag in self.page.url:
                return
            time.sleep(0.25)
        raise AssertionError(f"URL no contiene '{frag}': {self.page.url}")


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description="bot_QA_BREVIIS — E2E Breviis")
    ap.add_argument("-f", "--flows", nargs="+", help="IDs de flujo (ej. C1 A1). Default: todos los del manifiesto")
    ap.add_argument("--base-url", default=os.environ.get("E2E_BASE_URL", cfg["base_url"]))
    ap.add_argument("--manifest", default=cfg["manifest"])
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--skip-seed", action="store_true", help="No llamar al seed (usar --admin-email/--admin-password)")
    ap.add_argument("--admin-email")
    ap.add_argument("--admin-password")
    args = ap.parse_args()

    manifest = load_manifest(ROOT / args.manifest)
    flow_ids = args.flows or list(manifest["flows"].keys())
    unknown = [f for f in flow_ids if f not in manifest["flows"]]
    if unknown:
        sys.exit(f"Flujos no definidos en el manifiesto: {unknown}")

    ctx = {
        "base_url": args.base_url,
        "tenant_slug": manifest["tenant_slug"],
        "admin_email": args.admin_email or manifest["admin_email"],
        "admin_password": args.admin_password or "",
    }

    if not args.skip_seed:
        token = os.environ.get("E2E_SEED_TOKEN", "")
        if not token:
            sys.exit("Falta E2E_SEED_TOKEN (o usar --skip-seed con credenciales explícitas).")
        seed = call_seed(args.base_url, token)
        ctx["tenant_slug"] = seed["slug"]
        ctx["admin_email"] = seed["adminEmail"]
        ctx["admin_password"] = seed["adminPassword"]
        print(f"[seed] tenant={seed['slug']} admin={seed['adminEmail']}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (OUTPUT / "flow_status").mkdir(parents=True, exist_ok=True)
    (OUTPUT / "debug").mkdir(parents=True, exist_ok=True)

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        runner = Runner(page, manifest, ctx)

        for fid in flow_ids:
            t0 = time.time()
            entry = {"flow_id": fid, "status": "pass", "error": None,
                     "screenshot": None, "seconds": None}
            try:
                print(f"[{fid}] {manifest['flows'][fid]['nombre']} ...")
                runner.run_flow(fid)
                print(f"[{fid}] PASS")
            except Exception as e:  # noqa: BLE001 — el reporte necesita todo fallo
                shot = OUTPUT / "debug" / f"{fid}_{ts}.png"
                try:
                    page.screenshot(path=str(shot), full_page=True)
                    entry["screenshot"] = str(shot.relative_to(ROOT))
                except Exception:
                    pass
                entry["status"] = "fail"
                entry["error"] = f"{type(e).__name__}: {e}"
                print(f"[{fid}] FAIL — {entry['error']}", file=sys.stderr)
            entry["seconds"] = round(time.time() - t0, 1)
            results.append(entry)

        browser.close()

    report = {"bot": "bot_QA_BREVIIS", "base_url": args.base_url, "ts": ts,
              "results": results}
    out = OUTPUT / "flow_status" / f"run_{ts}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[report] {out}")

    sys.exit(0 if all(r["status"] == "pass" for r in results) else 1)


if __name__ == "__main__":
    main()
