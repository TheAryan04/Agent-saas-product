async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.wait_for_selector('[data-testid="prompt-input"]', timeout=10000)
        await page.click('[data-testid="icon-save-project"]')
        await page.wait_for_selector('[data-testid="notice-message"]', timeout=5000)
        assert 'saved locally' in (await page.text_content('[data-testid="notice-message"]') or '')
        print('PASS: save project notice')
        await page.click('[data-testid="export-button"]')
        assert 'Render queued' in (await page.text_content('[data-testid="notice-message"]') or '')
        print('PASS: export notice')
        await page.click('[data-testid="icon-play-preview"]')
        await page.wait_for_timeout(250)
        print('PASS: player control is clickable')
    except AssertionError as exc:
        print(f'FINDING: {exc}')
    except Exception as exc:
        print(f'FINDING: {exc}')
        raise

