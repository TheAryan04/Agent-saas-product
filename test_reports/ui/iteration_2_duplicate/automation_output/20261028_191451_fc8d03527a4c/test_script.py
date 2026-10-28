async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width":1920,"height":1080})
        await page.wait_for_selector('[data-testid="video-preview-panel"]', timeout=10000)
        await page.locator('[data-testid="nav-projects-button"]').click()
        await page.wait_for_selector('[data-testid="projects-list"]', timeout=5000)
        await page.wait_for_timeout(800)
        count_before = await page.locator('[data-testid^="project-card-"]').count()
        dup = page.locator('[data-testid^="icon-duplicate-"]').first
        await dup.scroll_into_view_if_needed()
        await dup.click()
        await page.wait_for_timeout(800)
        count_after = await page.locator('[data-testid^="project-card-"]').count()
        if count_after != count_before + 1:
            print(f"FINDING: duplicate did not add one card ({count_before} -> {count_after})")
        else:
            print("PASS: duplicate adds a project card")
    except Exception as e:
        print("SCRIPT ERROR:", e)
        raise

