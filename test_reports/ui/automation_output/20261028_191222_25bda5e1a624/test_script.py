async def run_test(page, output_dir, page_url):
    import json
    try:
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.wait_for_selector('[data-testid="prompt-input"]', timeout=10000)
        print('PASS: studio loaded')
        await page.fill('[data-testid="prompt-input"]', 'Create a launch film for teams')
        await page.click('[data-testid="fast-mode-toggle"]')
        assert 'on' in (await page.get_attribute('[data-testid="fast-mode-toggle"]', 'class') or '')
        print('PASS: prompt and fast mode')
        await page.click('[data-testid="scene-item-1"]')
        await page.fill('[data-testid="scene-headline-input"]', 'Updated headline')
        await page.fill('[data-testid="scene-duration-input"]', '4')
        await page.select_option('[data-testid="scene-template-select"]', 'SearchBar')
        assert await page.input_value('[data-testid="scene-headline-input"]') == 'Updated headline'
        print('PASS: scene selection and edits')
        before = await page.locator('[data-testid^="scene-item-"]').count()
        await page.click('[data-testid="add-scene-button"]')
        assert await page.locator('[data-testid^="scene-item-"]').count() == before + 1
        await page.click('[data-testid="icon-delete-scene"]')
        print('PASS: add and delete scene')
        await page.click('[data-testid="play-preview-button"]')
        await page.wait_for_timeout(300)
        assert 'Playing' in await page.text_content('.play-label')
        await page.locator('[data-testid="preview-scrubber"]').fill('80')
        print('PASS: playback and scrubber')
        await page.click('[data-testid="generate-button"]')
        await page.wait_for_selector('[data-testid="notice-message"]', timeout=3000)
        await page.wait_for_timeout(2500)
        assert 'Draft ready' in (await page.text_content('[data-testid="notice-message"]') or '')
        print('PASS: SSE generation and completion notice')
        await page.click('[data-testid="icon-settings"]')
        await page.wait_for_selector('[data-testid="settings-back-button"]')
        assert await page.is_visible('[data-testid="model-select-orchestrator"]')
        assert await page.is_visible('.health-box')
        print('PASS: settings and Ollama health')
        await page.click('[data-testid="settings-back-button"]')
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(300)
        overflow = await page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        assert not overflow, 'horizontal overflow detected'
        print('PASS: mobile has no horizontal overflow')
    except AssertionError as exc:
        print(f'FINDING: {exc}')
    except Exception as exc:
        print(f'FINDING: {exc}')
        raise
    finally:
        error_text = await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*='error'], [id*='error']')); return errorElements.map(el => el.textContent).join(', '); }""")
        print('Page errors:' + (error_text or ' none'))

