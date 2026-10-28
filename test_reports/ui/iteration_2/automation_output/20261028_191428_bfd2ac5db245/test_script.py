async def run_test(page, output_dir, page_url):
    import json

    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    findings = []

    def finding(message):
        print(f"FINDING: {message}")
        findings.append(message)

    try:
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.wait_for_selector('[data-testid="video-preview-panel"]', timeout=10000)
        print("PASS: studio loaded")

        # Upper preview play/pause regression
        upper = page.locator('[data-testid="icon-play-preview"]').first
        await upper.scroll_into_view_if_needed()
        await upper.click()
        await page.wait_for_timeout(250)
        if await page.locator('[data-testid="icon-pause-preview"]').count() != 1:
            finding("upper preview play button did not toggle to pause")
        else:
            print("PASS: upper preview toggles to pause")
        upper_pause = page.locator('[data-testid="icon-pause-preview"]').first
        await upper_pause.scroll_into_view_if_needed()
        await upper_pause.click()
        await page.wait_for_timeout(150)
        if await page.locator('[data-testid="icon-play-preview"]').count() != 1:
            finding("upper preview pause button did not toggle back to play")
        else:
            print("PASS: upper preview toggles back to play")

        # Scene editing/add/delete
        headline = page.locator('[data-testid="scene-headline-input"]')
        await headline.fill("Regression headline")
        if await headline.input_value() != "Regression headline": finding("scene headline input did not retain edit")
        else: print("PASS: scene headline edit")
        before = await page.locator('[data-testid^="scene-item-"]').count()
        await page.locator('[data-testid="add-scene-button"]').click()
        after_add = await page.locator('[data-testid^="scene-item-"]').count()
        if after_add != before + 1: finding("add scene did not add exactly one scene")
        else: print("PASS: add scene")
        await page.locator('[data-testid="icon-delete-scene"]').click()
        after_delete = await page.locator('[data-testid^="scene-item-"]').count()
        if after_delete != before: finding("delete scene did not restore scene count")
        else: print("PASS: delete scene")

        # Fast mode and generation/SSE
        await page.locator('[data-testid="fast-mode-toggle"]').click()
        await page.locator('[data-testid="generate-button"]').click()
        await page.wait_for_selector('[data-testid="notice-message"]', timeout=3000)
        await page.wait_for_timeout(1800)
        if "Draft ready" not in (await page.locator('[data-testid="notice-message"]').inner_text()):
            finding("SSE generation did not reach Draft ready")
        else: print("PASS: fast mode generation SSE completed")

        # Save/export notices
        await page.locator('[data-testid="icon-save-project"]').click()
        await page.wait_for_timeout(300)
        if "saved locally" not in (await page.locator('[data-testid="notice-message"]').inner_text()).lower(): finding("save notice missing")
        else: print("PASS: save flow")
        await page.locator('[data-testid="export-button"]').click()
        await page.wait_for_timeout(200)
        if "Render queued" not in await page.locator('[data-testid="notice-message"]').inner_text(): finding("export notice missing")
        else: print("PASS: export flow")

        # Projects navigation, reopen, duplicate
        await page.locator('[data-testid="nav-projects-button"]').click()
        await page.wait_for_selector('[data-testid="projects-list"]', timeout=5000)
        print("PASS: projects list opened")
        cards = page.locator('[data-testid^="project-card-"]')
        if await cards.count() < 1: finding("projects list has no cards")
        else: print("PASS: project card present")
        duplicate_buttons = page.locator('[data-testid^="icon-duplicate-"]')
        if await duplicate_buttons.count() < 1: finding("duplicate control missing")
        else: print("PASS: duplicate control exists")
        open_buttons = page.locator('[data-testid^="icon-open-"]')
        await open_buttons.first.click()
        await page.wait_for_selector('[data-testid="video-preview-panel"]', timeout=5000)
        print("PASS: project reopened")

        # Settings/health
        await page.locator('[data-testid="icon-settings"]').click()
        await page.wait_for_selector('[data-testid="settings-back-button"]', timeout=3000)
        if await page.locator('[data-testid="model-select-orchestrator"]').count() != 1: finding("settings model control missing")
        else: print("PASS: settings loaded")
        await page.locator('[data-testid="settings-back-button"]').click()

        # Mobile overflow
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.reload()
        await page.wait_for_selector('[data-testid="video-preview-panel"]', timeout=10000)
        overflow = await page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        if overflow: finding("mobile viewport has horizontal overflow")
        else: print("PASS: mobile no horizontal overflow")

        error_text = await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*=' + '"error"' + '], [id*=' + '"error"' + ']')); return errorElements.map(el => el.textContent).join(', '); }""")
        if error_text: print(f"Found error message: {error_text}")
        else: print("No error messages found on the page")
    except Exception as exc:
        print(f"SCRIPT ERROR: {exc}")
        raise
    finally:
        print(json.dumps({"findings": findings}))
