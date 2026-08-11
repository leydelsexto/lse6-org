#!/usr/bin/env python3
"""Regression test for the LSE6.COM center links.

The test renders the real index HTML with the real stylesheet and verifies
that the visible center links receive the pointer instead of a decorative
hero layer.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from bs4 import BeautifulSoup

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


def rendered_html() -> str:
    html = (ROOT / "index.html").read_text(encoding="utf-8-sig")
    css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8-sig")
    html = re.sub(
        r'<link[^>]+assets/css/styles\.css[^>]*>',
        lambda _: f"<style>{css}</style>",
        html,
        count=1,
    )
    # The click contract is structural. Runtime effects are tested elsewhere and
    # would make actionability dependent on animation timing or asset versions.
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    html = html.replace(
        "</head>",
        "<style>*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}</style></head>",
        1,
    )
    return html


async def assert_clickable(page, selector: str) -> None:
    locator = page.locator(selector)
    if await locator.count() != 1:
        raise AssertionError(f"Expected exactly one {selector}")
    href = await locator.get_attribute("href")
    if href != "https://lse6.com/":
        raise AssertionError(f"Wrong href for {selector}: {href!r}")
    target = await locator.get_attribute("target")
    if target != "_blank":
        raise AssertionError(f"{selector} must open LSE6.com in a new tab, got target={target!r}")
    rel = set((await locator.get_attribute("rel") or "").split())
    required_rel = {"noopener", "noreferrer"}
    if not required_rel.issubset(rel):
        raise AssertionError(f"{selector} is missing secure new-tab rel tokens: {sorted(required_rel - rel)}")
    box = await locator.bounding_box()
    if not box:
        raise AssertionError(f"{selector} has no visible box")
    point = [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2]
    hit = await page.evaluate(
        """([x,y,selector]) => {
          const target = document.elementFromPoint(x,y);
          return {
            tag: target?.tagName || null,
            className: String(target?.className || ""),
            ownsLink: Boolean(target?.closest(selector)),
          };
        }""",
        [*point, selector],
    )
    if not hit["ownsLink"]:
        raise AssertionError(
            f"{selector} is covered at its center by {hit['tag']}.{hit['className']}"
        )
    # Trial mode performs the full browser actionability check without navigating.
    await locator.click(trial=True, timeout=5000)


async def main() -> None:
    html = rendered_html()
    error_html = (ROOT / "404.html").read_text(encoding="utf-8-sig")
    error_soup = BeautifulSoup(error_html, "html.parser")
    error_center = error_soup.find("a", href="https://lse6.com/")
    error_rel = set(error_center.get("rel", [])) if error_center else set()
    if not (
        error_center
        and error_center.get("target") == "_blank"
        and {"noopener", "noreferrer"}.issubset(error_rel)
    ):
        raise AssertionError("404 center link does not preserve LSE6.ORG in a new tab")
    async with async_playwright() as p:
        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path("/usr/bin/chromium"),
        ]
        executable = next((item for item in candidates if item.exists()), None)
        launch_options = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            launch_options["executable_path"] = str(executable)
        browser = await p.chromium.launch(**launch_options)
        try:
            for viewport in (
                {"width": 1440, "height": 1000},
                {"width": 390, "height": 844},
            ):
                context = await browser.new_context(viewport=viewport)
                await context.route(
                    "https://lse6.com/",
                    lambda route: route.fulfill(
                        status=200,
                        content_type="text/html",
                        body="<title>LSE6 center</title>",
                    ),
                )
                page = await context.new_page()
                await page.emulate_media(reduced_motion="reduce")
                await page.set_content(html, wait_until="domcontentloaded")
                await assert_clickable(page, "a.archive-line.center-return-link")
                await assert_clickable(page, "a.core-button")
                center_links = page.locator("a[data-lse6-center='true']")
                for index in range(await center_links.count()):
                    link = center_links.nth(index)
                    if await link.get_attribute("target") != "_blank":
                        raise AssertionError(f"Center link #{index + 1} does not preserve LSE6.ORG")
                    rel = set((await link.get_attribute("rel") or "").split())
                    if not {"noopener", "noreferrer"}.issubset(rel):
                        raise AssertionError(f"Center link #{index + 1} lacks secure new-tab rel tokens")
                original_url = page.url
                async with page.expect_popup() as popup_info:
                    await page.locator("a.core-button").click()
                popup = await popup_info.value
                await popup.wait_for_load_state("domcontentloaded")
                if page.url != original_url:
                    raise AssertionError("LSE6.ORG was replaced instead of staying open")
                # The exact destination is asserted from the real href above. In this
                # offline QA container the external navigation may resolve to Chromium's
                # network error page, but the popup event proves a separate tab was created.
                await popup.close()
                await page.close()
                await context.close()
        finally:
            await browser.close()
    print("PASS: LSE6.ORG remains open while every center link opens a separate tab on desktop and mobile")


if __name__ == "__main__":
    asyncio.run(main())
