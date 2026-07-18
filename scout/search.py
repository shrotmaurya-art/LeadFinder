"""Playwright-based Google Maps data source implementation for LeadFinder."""

import asyncio
import random
import time
import urllib.parse
from playwright.async_api import async_playwright, Page

from scout.base import BusinessDataSource
from scout.normalize import normalize_phone, normalize_website, normalize_address
from utils.logger import get_logger

logger = get_logger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

class PlaywrightMapsSource(BusinessDataSource):
    """Data source that scrapes business details from Google Maps using Playwright."""
    
    _last_search_time = 0.0

    def search(self, city: str, category: str) -> list[dict]:
        """Performs a synchronous search for businesses in a city and category.
        
        Enforces a random 2-5 second delay between separate search() calls.
        """
        now = time.time()
        elapsed = now - PlaywrightMapsSource._last_search_time
        required_delay = random.uniform(2.0, 5.0)
        if PlaywrightMapsSource._last_search_time > 0 and elapsed < required_delay:
            sleep_time = required_delay - elapsed
            logger.info("Throttling search() call. Sleeping for %.2f seconds.", sleep_time)
            time.sleep(sleep_time)

        try:
            results = asyncio.run(self._async_search(city, category))
        except Exception as e:
            logger.error("Failed to complete search for %s in %s: %s", category, city, e, exc_info=True)
            results = []
        finally:
            PlaywrightMapsSource._last_search_time = time.time()

        return results

    async def _async_search(self, city: str, category: str) -> list[dict]:
        """Asynchronously scrapes Google Maps for results."""
        results = []
        user_agent = random.choice(USER_AGENTS)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            query = f"{category} in {city}"
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://www.google.com/maps/search/{encoded_query}"
            
            logger.info("Navigating to search URL: %s", search_url)
            await page.goto(search_url)

            # Check if we landed on a details page directly or a list feed
            try:
                await page.wait_for_selector('div[role="feed"]', timeout=10000)
                is_list = True
            except Exception:
                is_list = False

            if not is_list:
                # Check if we redirected directly to a single business detail page
                h1_count = await page.locator('h1').count()
                if h1_count > 0:
                    logger.info("Directly redirected to single business detail page.")
                    try:
                        place = await self._extract_current_place(page, page.url, city, category)
                        results.append(place)
                    except Exception as e:
                        logger.error("Failed to extract single page result: %s", e, exc_info=True)
                    await browser.close()
                    return results
                else:
                    logger.info("No list feed or detail page found (possibly zero results).")
                    await browser.close()
                    return []

            # We are on a list feed page. Scroll to load ~20 results.
            feed = page.locator('div[role="feed"]')
            scroll_attempts = 0
            max_scroll_attempts = 3
            card_urls = []

            while len(card_urls) < 20 and scroll_attempts < max_scroll_attempts:
                cards = page.locator('div[role="feed"] a[href*="/maps/place/"]')
                count = await cards.count()

                new_urls_found = False
                for i in range(count):
                    href = await cards.nth(i).get_attribute("href")
                    if href and href not in card_urls:
                        card_urls.append(href)
                        new_urls_found = True

                if len(card_urls) >= 20:
                    break

                logger.info("Scrolling results panel. Currently found %d URLs.", len(card_urls))
                try:
                    await feed.evaluate('(el) => el.scrollTop = el.scrollHeight')
                except Exception as scroll_err:
                    logger.warning("Failed to scroll feed panel: %s", scroll_err)
                    break

                # Random 2-5 second delay between scroll actions
                await asyncio.sleep(random.uniform(2.0, 5.0))

                if not new_urls_found:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0

            logger.info("Found %d total card URLs. Starting detail extraction.", len(card_urls))

            # Process up to 20 listings
            for card_url in card_urls[:20]:
                try:
                    logger.info("Visiting details for: %s", card_url)
                    await page.goto(card_url)
                    place = await self._extract_current_place(page, card_url, city, category)
                    results.append(place)
                except Exception as e:
                    # Log failure of individual listing and continue
                    logger.error("Failed to extract details from card %s: %s", card_url, e)

            await browser.close()

        return results

    async def _extract_current_place(self, page: Page, url: str, city: str, category: str) -> dict:
        """Extracts business details from the currently loaded page."""
        # Wait for the name element (h1) to load
        await page.wait_for_selector("h1", timeout=10000)
        
        # Give dynamic elements half a second to populate
        await page.wait_for_timeout(500)

        # 1. Name
        name = ""
        h1_locator = page.locator("h1")
        if await h1_locator.count() > 0:
            name = await h1_locator.first.inner_text()
        name = name.strip()

        # 2. Address
        raw_address = None
        address_locator = page.locator('[data-item-id="address"]')
        if await address_locator.count() > 0:
            raw_address = await address_locator.first.inner_text()
        address = normalize_address(raw_address)

        # 3. Website
        website = None
        website_locator = page.locator('a[data-item-id="authority"]')
        if await website_locator.count() > 0:
            website = await website_locator.first.get_attribute("href")
            if not website:
                website = await website_locator.first.inner_text()
        normalized_website = normalize_website(website)

        # 4. Phone
        phone = None
        phone_locator = page.locator('[data-item-id^="phone:tel:"]')
        if await phone_locator.count() > 0:
            item_id = await phone_locator.first.get_attribute("data-item-id")
            if item_id and item_id.startswith("phone:tel:"):
                phone = item_id.replace("phone:tel:", "").strip()
            else:
                phone = await phone_locator.first.inner_text()
        normalized_phone = normalize_phone(phone)

        # 5. Rating and Review Count
        google_rating = None
        google_reviews_count = None

        # Fallback A: Check div.F7nice (very common container)
        f7_locator = page.locator('div.F7nice')
        if await f7_locator.count() > 0:
            try:
                text = await f7_locator.first.inner_text()
                import re
                m = re.search(r'([3-5]\.[0-9])\s*\(?([0-9,]+)\)?', text)
                if m:
                    google_rating = float(m.group(1))
                    google_reviews_count = int(m.group(2).replace(",", ""))
            except Exception as e:
                logger.debug("Failed parsing div.F7nice for rating: %s", e)

        # Fallback B: Scan aria-label with 'stars'
        if google_rating is None:
            try:
                stars_locator = page.locator('[aria-label*="stars"]')
                if await stars_locator.count() > 0:
                    aria_label = await stars_locator.first.get_attribute("aria-label")
                    if aria_label:
                        import re
                        m = re.search(r'([3-5]\.[0-9])\s*stars', aria_label)
                        if m:
                            google_rating = float(m.group(1))
                        m2 = re.search(r'([0-9,]+)\s+reviews', aria_label)
                        if m2 and google_reviews_count is None:
                            google_reviews_count = int(m2.group(1).replace(",", ""))
            except Exception as e:
                logger.debug("Failed parsing aria-label stars for rating: %s", e)

        # Fallback C: Scan aria-label with 'reviews'
        if google_reviews_count is None:
            try:
                reviews_locator = page.locator('[aria-label*="reviews"]')
                count = await reviews_locator.count()
                for i in range(count):
                    aria_label = await reviews_locator.nth(i).get_attribute("aria-label")
                    if aria_label:
                        import re
                        m = re.search(r'([0-9,]+)\s+reviews', aria_label)
                        if m:
                            google_reviews_count = int(m.group(1).replace(",", ""))
                            break
            except Exception as e:
                logger.debug("Failed parsing aria-label reviews for count: %s", e)

        # Fallback D: Check MW4etd/UY7F9 classes
        if google_rating is None:
            try:
                rating_elem = page.locator('span.MW4etd')
                if await rating_elem.count() > 0:
                    google_rating = float(await rating_elem.first.inner_text())
            except Exception as e:
                logger.debug("Failed parsing span.MW4etd for rating: %s", e)

        if google_reviews_count is None:
            try:
                reviews_elem = page.locator('span.UY7F9')
                if await reviews_elem.count() > 0:
                    text = await reviews_elem.first.inner_text()
                    text = text.replace("(", "").replace(")", "").replace(",", "").strip()
                    google_reviews_count = int(text)
            except Exception as e:
                logger.debug("Failed parsing span.UY7F9 for reviews count: %s", e)

        return {
            "name": name,
            "phone": phone,
            "normalized_phone": normalized_phone,
            "website": website,
            "normalized_website": normalized_website,
            "email": None,
            "instagram_url": None,
            "address": address,
            "city": city,
            "category": category,
            "google_rating": google_rating,
            "google_reviews_count": google_reviews_count,
            "source_url": url,
        }
