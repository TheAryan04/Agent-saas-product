async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width":1920,"height":1080})
        await page.wait_for_selector('[data-testid="video-preview-panel"]', timeout=10000)
        await page.locator('[data-testid="nav-projects-button"]').click()
        await page.wait_for_selector('[data-testid="projects-list"]', timeout=5000)
        await page.wait_for_timeout(500)
        print('projects text:', await page.locator('[data-testid="projects-list"]').inner_text())
        print('project cards:', await page.locator('[data-testid^="project-card-"]').count())
        print('all testids:', await page.evaluate("Array.from(document.querySelectorAll('[data-testid]')).map(x=>x.getAttribute('data-testid')).filter(x=>x.includes('project')||x.includes('duplicate')||x.includes('open')).join('|')"))
    except Exception as e:
        print('SCRIPT ERROR:',e)
        raise

