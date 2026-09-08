#!/usr/bin/env python3
"""Real-browser regression for the experimental public site (no AI submission).

Install: python3 -m pip install playwright
Browser: Google Chrome, or `python3 -m playwright install chromium` and --channel chromium
Run:     python3 tests/verify_site.py [https://your-public-site.example/]

Without a URL, serve only site/ on an ephemeral loopback port, applying the
checked-in Vercel headers. Live runs compare downloads to this checkout too;
build the distribution first. Archive internals belong to the package tests.
Reports/screenshots go to test-results/ (gitignored), not site/.
Fail-fast by design: an initial RED leaves later checks explicitly unexecuted.
"""

import argparse
from contextlib import contextmanager
from functools import partial
import hashlib
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from threading import Thread
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "test-results"
WIDTHS = (2560, 1440, 1024, 768, 620, 390, 320)
# Packaging release only: canonical protocol/SKILL remain version 0.1.0.
ARCHIVES = ("ask-giorgio-universal-v0.1.1.zip", "ask-giorgio-skill-v0.1.1.zip")
MODES = {
    "wander": ("Wandering", "Wandering: follow my curiosity without imposing a fixed itinerary."),
    "highlights": ("Highlights", "Highlights: help select a few worthwhile works around my interests and time, rather than a comprehensive tour."),
    "tour": ("A tour", "A tour: help build a coherent, walkable itinerary with connected stops, realistic time to linger, and a flexible order."),
    "theme": ("A themed tour", "A themed tour: help build a coherent itinerary around my chosen theme, or help me choose a theme if I have not supplied one."),
}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def origin(url):
    parsed = urlsplit(url)
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


@contextmanager
def target(url):
    if url:
        parsed = urlsplit(url)
        check(parsed.scheme in ("http", "https") and parsed.hostname,
              "URL must be an absolute HTTP(S) public-site URL")
        check(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
              "Do not put credentials, query strings or fragments in the test URL")
        yield url.rstrip("/") + "/"
        return
    rules = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["headers"]

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            for rule in rules:
                if re.fullmatch(rule["source"], urlsplit(self.path).path):
                    for header in rule["headers"]:
                        self.send_header(header["key"], header["value"])
            super().end_headers()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def expected_handoff(protocol, mode, minutes, museum="", interests=""):
    museum, interests = museum.strip(), interests.strip()
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    place = ("Museum supplied by me: " + quote(museum) + "." if museum
             else "Ask which museum I am visiting.")
    topic = (("My chosen theme: " if mode == "theme" else "My interests: ") + quote(interests) + "."
             if interests else "Help me decide what interests me, without assuming a preference.")
    return (protocol + "\n\n## My visit preferences\n"
            + f"For this visit: {MODES[mode][1]} I have about {minutes} minutes. {place} {topic} "
            + "Keep the conversation brief, voice-friendly, and flexible so I can look at the art, not my phone. "
            + "Use available evidence for suggested stops; do not assume current display status or gallery locations. "
            + "If routing is uncertain, ask for the museum map or on-site signs.")


def ready(page):
    page.evaluate("document.fonts.ready")
    page.evaluate("""async () => {
        for (const image of document.images) image.loading = 'eager';
        await Promise.all([...document.images].map(image => image.decode()));
    }""")


def privacy(page, context):
    state = page.evaluate("""async () => ({
        local: localStorage.length, session: sessionStorage.length,
        databases: (await indexedDB.databases()).length,
        caches: (await caches.keys()).length,
        workers: (await navigator.serviceWorker.getRegistrations()).length,
        storageWrites: window.__regressionStorageWrites,
        violations: window.__regressionCspViolations
    })""")
    check(all(state[key] == 0 for key in ("local", "session", "databases", "caches", "workers")),
          f"Unexpected persistent browser state: {state}")
    check(not state["storageWrites"] and not state["violations"], f"Privacy/CSP regression: {state}")
    check(not context.cookies(), "The site must not create cookies")


def posture(page, response):
    if response is None:
        raise AssertionError("Site navigation returned no HTTP response")
    check(response.status == 200, "Site must return anonymous HTTP 200")
    headers = response.headers
    check("noindex" in headers.get("x-robots-tag", "").lower(), "Missing HTTP noindex")
    check(headers.get("x-content-type-options") == "nosniff", "Missing nosniff")
    directives = {}
    for part in headers.get("content-security-policy", "").split(";"):
        fields = part.split()
        if fields:
            directives[fields[0]] = fields[1:]
    for key, values in {"default-src": ["'self'"], "script-src": ["'self'"],
                        "connect-src": ["'none'"], "object-src": ["'none'"],
                        "base-uri": ["'self'"], "frame-ancestors": ["'none'"],
                        "form-action": ["'none'"]}.items():
        check(directives.get(key) == values, f"Unsafe/missing CSP {key}: {directives.get(key)}")
    check("script-src-elem" not in directives or directives["script-src-elem"] == ["'self'"],
          "script-src-elem must not weaken script policy")
    check("noindex" in (page.locator('meta[name="robots"]').get_attribute("content") or "").lower(),
          "Missing HTML noindex")


class Anchors(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.ids.update(value for key, value in attrs.items() if key == "id" or (tag == "a" and key == "name"))


def same_origin_get(context, base, url):
    # Do not follow even a broken local link to an external provider/login.
    for _ in range(8):
        check(origin(url) == origin(base), f"Refusing external link request: {url}")
        response = context.request.get(url, max_redirects=0)
        if response.status not in (301, 302, 303, 307, 308):
            return response
        check(response.headers.get("location"), f"Redirect without Location: {url}")
        url = urljoin(url, response.headers["location"])
    raise AssertionError("Too many local link redirects")


def local_links(page, context, base):
    checked = []
    hrefs = sorted(set(page.locator("a[href]").evaluate_all("xs => xs.map(x => x.getAttribute('href'))")))
    for href in hrefs:
        absolute, fragment = urldefrag(urljoin(page.url, href))
        parts = urlsplit(absolute)
        check(parts.scheme in ("http", "https"), f"Unexpected link scheme: {href}")
        if origin(absolute) != origin(base):
            check(parts.hostname not in ("localhost", "127.0.0.1", "::1"), f"Private review link: {href}")
            continue  # Inspect provider/credit links only; never visit external sites.
        response = same_origin_get(context, base, absolute)
        check(response.ok, f"Broken local link {href}: HTTP {response.status}")
        if fragment:
            check(unquote(fragment) in Anchors(response.text()).ids, f"Missing anchor: {href}")
        checked.append(href)
    return checked


def exercise(page, context, base, protocol, record, shot):
    response = page.goto(base, wait_until="networkidle")
    posture(page, response)
    ready(page)
    check("WORK IN PROGRESS" in page.locator(".reviewbar").inner_text().upper(), "Missing visible WIP banner")
    check(" ".join(page.locator("h1").inner_text().split()) == "Look at the art. Not your phone.",
          "Editorial headline changed")
    check(page.locator(".hero .portrait-image").get_attribute("src") == "assets/vasari-portrait.webp",
          "Missing Vasari portrait")
    check("parchment.webp" in page.locator("body").evaluate("x => getComputedStyle(x).backgroundImage"),
          "Missing parchment")
    record("Anonymous HTTP 200, WIP, noindex, strict CSP and editorial identity")

    triggers = page.locator("[data-setup]")
    count = triggers.count()
    check(count == 3, f"Enabled setup: expected 3 [data-setup] controls, found {count}")
    check(page.locator("button.unavailable:disabled").count() == 0, "Setup CTAs still disabled")
    check("experimental" in page.locator(".reviewbar").inner_text().lower(), "Banner must label enabled guide experimental")
    for index in range(count):
        trigger = triggers.nth(index)
        expect(trigger).to_be_enabled()
        trigger.click()
        expect(page.locator("#setup")).to_be_visible()
        check(page.locator("#setup").evaluate("x => x.tagName === 'DIALOG' && x.matches(':modal')"),
              "Setup must be a native modal dialog")
        page.locator("[data-close]").click()
        expect(page.locator("#setup")).to_be_hidden()
        expect(trigger).to_be_focused()
    check(page.locator('script[src="guide.js"]').count() == 1, "Load exactly one external guide.js")
    check(page.locator("script:not([src])").count() == 0, "No inline scripts under script-src self")
    record("Three enabled setup CTAs, external guide.js, native modal and close-button focus restoration")

    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 1050 if width == 1440 else 844})
        ready(page)
        layout = page.evaluate("""() => ({width: innerWidth, scroll: document.documentElement.scrollWidth,
            clipped: [...document.querySelectorAll('main h1,main h2,main h3,main p')]
            .filter(x => x.clientWidth > 0 && x.scrollWidth > x.clientWidth + 2).map(x => x.textContent)})""")
        check(layout["scroll"] <= width + 1 and not layout["clipped"], f"Layout overflow: {layout}")
        shot(f"home-{width}", full_page=True)
        record(f"{width}px home responsive layout", layout)
    page.set_viewport_size({"width": 1440, "height": 1050})
    titles = []
    for mode, (label, _) in MODES.items():
        page.locator(f'[data-visit-mode="{mode}"]').click()
        check(page.locator('[data-visit-mode][aria-pressed="true"]').count() == 1, "Mode selection must be exclusive")
        check(page.locator('[data-visit-mode][aria-pressed="true"]').get_attribute("data-visit-mode") == mode,
              "Wrong active mode")
        titles.append(page.locator("#mission-title").inner_text())
        for minutes in ("30", "60", "90", "120"):
            page.locator("#visit-minutes").select_option(minutes)
            expect(page.locator("#duration-summary")).to_have_text(minutes + " minutes")
            # Empty and explicit settings for every mode/time combination.
            for museum, interests in (("", ""), ('The Met — "New York"', "Myths & monsters")):
                page.locator("#visit-museum").fill(museum)
                page.locator("#visit-interests").fill(interests)
                expect(page.locator("#museum-summary")).to_have_text(museum or "Choose together")
                expect(page.locator("#interests-label")).to_have_text("Your theme" if mode == "theme" else "Your interests")
                expect(page.locator("#interest-summary")).to_have_text(interests or ("Choose a theme together" if mode == "theme" else "Find what draws you in"))
                page.locator("#ticket [data-setup]").click()
                text = page.locator("#guide-text").input_value()
                check(text == expected_handoff(protocol, mode, minutes, museum, interests),
                      f"Exact protocol + handoff mismatch: {mode}/{minutes}/{'filled' if museum else 'empty'}")
                duration_label = "2 hours" if minutes == "120" else minutes + " minutes"
                expect(page.locator("#chosen-visit")).to_have_text(" · ".join(filter(None, (label, duration_label, museum, interests))))
                page.locator("[data-close]").click()
        record(f"{mode}: exact canonical protocol + four durations, empty and explicit museum/interests")
    check(len(set(titles)) == len(MODES), "All four modes must have distinct preview titles")

    page.locator("#visit-minutes").select_option("90")
    page.locator("#visit-museum").fill("The Met")
    page.locator("#visit-interests").fill("Myths and monsters")
    expected = expected_handoff(protocol, "theme", "90", "The Met", "Myths and monsters")
    page.locator("#ticket [data-setup]").click()
    for provider, href in (("ChatGPT", "https://chatgpt.com/"), ("Claude", "https://claude.ai/"), ("Other AI", None)):
        page.locator(f'[data-provider="{provider}"]').click()
        check(page.locator('[data-provider][aria-pressed="true"]').count() == 1, "Provider selection must be exclusive")
        expect(page.locator(f'[data-provider="{provider}"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#provider-name")).to_have_text("your AI app" if href is None else provider)
        if href is None:
            expect(page.locator("#open-provider")).to_be_hidden()
        else:
            expect(page.locator("#open-provider")).to_be_visible()
            expect(page.locator("#open-provider")).to_have_attribute("href", href)
            expect(page.locator("#open-provider")).to_have_attribute("target", "_blank")
            check("noopener" in (page.locator("#open-provider").get_attribute("rel") or "").split(), "Unsafe external opener")
        check(page.locator("#guide-text").input_value() == expected, "Provider choice altered the guide")
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base.rstrip("/"))
    page.locator("#copy-guide").click()
    expect(page.locator("#copy-status")).to_contain_text("Copied.")
    check(page.evaluate("navigator.clipboard.readText()") == expected, "Real clipboard differs from exact protocol + settings")
    shot("setup-desktop")
    record("Provider selectors (no external navigation) and real clipboard exact contents")

    for reason, replacement in (("denied", "{writeText: async () => {throw Error('test clipboard denied')}}"),
                                ("unavailable", "undefined")):
        page.evaluate(f"Object.defineProperty(navigator, 'clipboard', {{configurable:true,value:{replacement}}})")
        page.locator("#copy-guide").click()
        expect(page.locator("#manual")).to_have_attribute("open", "")
        expect(page.locator("#copy-status")).to_contain_text("Clipboard unavailable")
        expect(page.locator("#guide-text")).to_be_focused()
        check(page.locator("#guide-text").input_value() == expected, "Fallback text differs from clipboard")
        check(page.locator("#guide-text").evaluate("x => x.selectionStart === 0 && x.selectionEnd === x.value.length"),
              "Fallback must select the complete guide")
        record(f"Clipboard {reason}: complete manual fallback, focus and selection")
    for key in ("Tab", "Shift+Tab"):
        for _ in range(18):
            page.keyboard.press(key)
            check(page.evaluate("document.activeElement === document.body || document.querySelector('#setup').contains(document.activeElement)"),
                  "Focus escaped native modal into background controls")
    page.keyboard.press("Escape")
    expect(page.locator("#setup")).to_be_hidden()
    expect(page.locator("#ticket [data-setup]")).to_be_focused()
    record("Modal forward/reverse keyboard containment, Escape and opener focus restoration")

    page.set_viewport_size({"width": 320, "height": 640})
    page.locator(".site-header [data-setup]").click()
    for provider in ("ChatGPT", "Claude", "Other AI"):
        page.locator(f'[data-provider="{provider}"]').click()
    page.locator("#copy-guide").click()
    check(page.locator("#setup").evaluate("x => x.scrollWidth <= x.clientWidth + 1"), "320px dialog has horizontal overflow")
    box = page.locator("#setup").bounding_box()
    check(box and box["x"] >= 0 and box["x"] + box["width"] <= 321 and box["height"] <= 640,
          f"320px dialog escapes viewport: {box}")
    shot("setup-320")
    page.keyboard.press("Escape")
    expect(page.locator(".site-header [data-setup]")).to_be_focused()
    record("320px dialog: provider controls, manual copy, viewport fit and Escape")

    page.set_viewport_size({"width": 1440, "height": 1050})
    literal = '<b>Art & sculpture</b><img src=x onerror="window.__inputExecuted=true">'
    page.locator("#visit-museum").fill(literal)
    page.locator("#visit-interests").fill(literal)
    for selector in ("#museum-summary", "#interest-summary"):
        expect(page.locator(selector)).to_have_text(literal)
        check(page.locator(selector + " *").count() == 0, f"HTML input interpreted in {selector}")
    page.locator("#ticket [data-setup]").click()
    check(page.locator("#guide-text").input_value() == expected_handoff(protocol, "theme", "90", literal, literal),
          "Literal input must remain quoted in the complete handoff")
    check(page.locator("#chosen-visit b, #chosen-visit img").count() == 0, "Dialog interpreted visitor markup")
    check(page.evaluate("window.__inputExecuted === undefined"), "Visitor input executed")
    page.keyboard.press("Escape")
    privacy(page, context)
    record("Literal visitor input in preview/dialog/handoff; no storage writes, persisted state or cookies")

    for summary in page.locator(".faq summary").all():
        summary.click()
        expect(summary.locator("..")).to_have_attribute("open", "")
        summary.click()
    page.emulate_media(reduced_motion="reduce")
    check(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto", "Reduced motion ignored")
    record("FAQ controls and reduced-motion preference")
    record("Homepage local/fragment/download links resolve", local_links(page, context, base))

    page.locator(".site-header [data-setup]").click()
    page.locator("#setup summary").filter(has_text="Prefer a download?").click()
    hashes = {}
    for filename in ARCHIVES:
        reference = SITE / "downloads" / filename
        check(reference.is_file(), f"Build required: site/downloads/{filename} missing")
        with page.expect_download() as download_event:
            page.locator(f'#setup a[href="downloads/{filename}"]').click()
        download = download_event.value
        check(download.failure() is None, f"Browser download failed: {filename}")
        check(download.suggested_filename == filename, f"Wrong download filename: {download.suggested_filename}")
        expected_bytes = reference.read_bytes()
        downloaded_bytes = Path(download.path()).read_bytes()
        actual_hash = hashlib.sha256(downloaded_bytes).hexdigest()
        check(downloaded_bytes == expected_bytes, f"Browser ZIP bytes differ from site/downloads/{filename}")
        served = same_origin_get(context, base, urljoin(base, "downloads/" + filename))
        check(served.ok and served.body() == expected_bytes, f"Served ZIP differs from local build: {filename}")
        hashes[filename] = {"sha256": actual_hash, "bytes": len(downloaded_bytes)}
    record("Browser-downloaded release ZIPs exactly match local and HTTP-served bytes", hashes)
    page.keyboard.press("Escape")
    privacy(page, context)

    response = page.goto(urljoin(base, "credits.html"), wait_until="networkidle")
    posture(page, response)
    ready(page)
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 844})
        check(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Credits overflow at {width}px")
    shot("credits-320", full_page=True)
    record("Credits at all seven widths; credit/license/local links resolve", local_links(page, context, base))
    privacy(page, context)

    page.goto(base, wait_until="networkidle")
    check(page.locator("#visit-museum").input_value() == "" and page.locator("#visit-interests").input_value() == "",
          "Visitor inputs persisted after a fresh navigation")
    privacy(page, context)
    record("Fresh navigation does not restore private visit inputs")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", nargs="?", help="Optional public site URL; never an AI provider URL")
    parser.add_argument("--channel", default="chrome", help="chrome (default) or chromium for Playwright's bundled browser")
    args = parser.parse_args()
    label = "live" if args.url else "local"
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / f"{label}-results.json"
    results = []
    runtime = {"errors": [], "failed_responses": [], "failed_requests": [], "external": [], "connect": [], "requests": []}
    report = {"status": "running", "checks": results, "runtime": runtime,
              "note": "Fail-fast; checks after the first failure were not executed. No provider login or conversation submission."}

    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def record(name, detail=True):
        results.append({"test": name, "pass": True, "detail": detail})
        save()
        print("PASS", name, flush=True)

    page = None
    browser = None
    try:
        protocol = (ROOT / "ask-giorgio" / "references" / "protocol.md").read_text(encoding="utf-8")
        with target(args.url) as base, sync_playwright() as playwright:
            report["base"] = base
            browser = playwright.chromium.launch(headless=True, **({} if args.channel == "chromium" else {"channel": args.channel}))
            context = browser.new_context(viewport={"width": 1440, "height": 1050}, device_scale_factor=1, accept_downloads=True)
            context.set_default_timeout(10000)
            context.add_init_script("""window.__regressionStorageWrites = []; window.__regressionCspViolations = [];
                const original = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    window.__regressionStorageWrites.push(String(key)); return original.call(this, key, value);
                };
                document.addEventListener('securitypolicyviolation', e => window.__regressionCspViolations.push(e.violatedDirective));""")

            def guard(route):
                request = route.request
                runtime["requests"].append({"url": request.url, "type": request.resource_type})
                if request.resource_type in ("fetch", "xhr", "eventsource", "websocket", "ping"):
                    runtime["connect"].append(request.url)
                    route.abort()
                elif origin(request.url) != origin(base):
                    runtime["external"].append(request.url)
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", guard)
            context.on("response", lambda response: runtime["failed_responses"].append([response.url, response.status]) if response.status >= 400 else None)
            context.on("requestfailed", lambda request: runtime["failed_requests"].append([request.url, request.failure]))

            def observe(new_page):
                new_page.on("pageerror", lambda error: runtime["errors"].append(str(error)))
                new_page.on("console", lambda message: runtime["errors"].append(message.text) if message.type == "error" else None)
                new_page.on("websocket", lambda socket: runtime["connect"].append(socket.url))

            context.on("page", observe)
            page = context.new_page()

            def shot(name, **kwargs):
                page.screenshot(path=str(OUT / f"{label}-{name}.png"), **kwargs)

            try:
                exercise(page, context, base, protocol, record, shot)
                for key in ("errors", "failed_responses", "failed_requests", "external", "connect"):
                    check(not runtime[key], f"Runtime {key}: {runtime[key]}")
                check(any(urlsplit(item["url"]).path.endswith("/guide.js") and item["type"] == "script" for item in runtime["requests"]),
                      "Browser never loaded the external guide.js")
                record("No JS/CSP errors, failed resources, fetch/connect calls or external runtime requests")
                report["status"] = "passed"
            except Exception as error:
                report["status"] = "failed"
                report["failure"] = f"{type(error).__name__}: {error}"
                try:
                    shot("failure", full_page=True)
                    report["screenshot"] = f"{label}-failure.png"
                except Exception as screenshot_error:
                    report["screenshot_error"] = str(screenshot_error)
                raise
            finally:
                browser.close()
                browser = None
    except Exception as error:
        report["status"] = "failed"
        report.setdefault("failure", f"{type(error).__name__}: {error}")
        print("FAIL", report["failure"], flush=True)
    finally:
        report["passed_checks"] = len(results)
        save()
        print("REPORT", report_path.relative_to(ROOT), flush=True)
    if report["status"] == "passed":
        print(f"VERIFIED {len(results)} checks", flush=True)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
