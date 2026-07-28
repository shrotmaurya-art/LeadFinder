"""Playwright-based Google Maps data source implementation for LeadFinder."""

import asyncio
import random
import time
import urllib.parse
from playwright.async_api import async_playwright, Page

import config
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
        Delegates to search_city for a single category.
        """
        batch = self.search_city(city, [category])
        return batch.get(category, [])

    def search_city(self, city: str, categories: list[str]) -> dict[str, list[dict]]:
        """Search multiple categories for a city using a single browser session.

        Returns a dict mapping category name to its list of business records.
        This is dramatically faster than calling search() per category because
        it launches the browser only once.
        """
        now = time.time()
        elapsed = now - PlaywrightMapsSource._last_search_time
        required_delay = random.uniform(config.SEARCH_DELAY_MIN, config.SEARCH_DELAY_MAX)
        if PlaywrightMapsSource._last_search_time > 0 and elapsed < required_delay:
            sleep_time = required_delay - elapsed
            logger.info("Throttling search_city() call. Sleeping for %.2f seconds.", sleep_time)
            time.sleep(sleep_time)

        try:
            results = asyncio.run(self._async_search_city(city, categories))
        except Exception as e:
            logger.error("Failed to complete batch search for %s: %s", city, e, exc_info=True)
            results = {cat: [] for cat in categories}
        finally:
            PlaywrightMapsSource._last_search_time = time.time()

        return results

    async def _async_search_city(self, city: str, categories: list[str]) -> dict[str, list[dict]]:
        """Search all categories for a city in a single browser session."""
        all_results: dict[str, list[dict]] = {}
        user_agent = random.choice(USER_AGENTS)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800},
            )

            for idx, category in enumerate(categories):
                if idx > 0:
                    await asyncio.sleep(random.uniform(config.SEARCH_DELAY_MIN, config.SEARCH_DELAY_MAX))

                page = await context.new_page()
                try:
                    all_results[category] = await self._search_category(page, city, category)
                except Exception as e:
                    logger.error("Failed to search %s in %s: %s", category, city, e, exc_info=True)
                    all_results[category] = []
                finally:
                    await page.close()

            await browser.close()

        return all_results

    async def _search_category(self, page: Page, city: str, category: str) -> list[dict]:
        """Search a single category using an already-open page."""
        results: list[dict] = []

        query = f"{category} in {city}"
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/maps/search/{encoded_query}"

        logger.info("Navigating to search URL: %s", search_url)
        await page.goto(search_url)

        try:
            await page.wait_for_selector('div[role="feed"]', timeout=config.PAGE_LOAD_TIMEOUT_MS)
            is_list = True
        except Exception:
            is_list = False

        if not is_list:
            h1_count = await page.locator('h1').count()
            if h1_count > 0:
                logger.info("Directly redirected to single business detail page.")
                try:
                    place = await self._extract_current_place(page, page.url, city, category)
                    results.append(place)
                except Exception as e:
                    logger.error("Failed to extract single page result: %s", e, exc_info=True)
                return results
            else:
                logger.info("No list feed or detail page found (possibly zero results).")
                return []

        feed = page.locator('div[role="feed"]')
        scroll_attempts = 0
        max_scroll_attempts = config.MAX_SCROLL_ATTEMPTS
        card_urls = []

        while len(card_urls) < config.SCROLL_TARGET_RESULTS and scroll_attempts < max_scroll_attempts:
            cards = page.locator('div[role="feed"] a[href*="/maps/place/"]')
            count = await cards.count()

            new_urls_found = False
            for i in range(count):
                href = await cards.nth(i).get_attribute("href")
                if href and href not in card_urls:
                    card_urls.append(href)
                    new_urls_found = True

            if len(card_urls) >= config.SCROLL_TARGET_RESULTS:
                break

            logger.info("Scrolling results panel. Currently found %d URLs.", len(card_urls))
            try:
                await feed.evaluate('(el) => el.scrollTop = el.scrollHeight')
            except Exception as scroll_err:
                logger.warning("Failed to scroll feed panel: %s", scroll_err)
                break

            await asyncio.sleep(random.uniform(config.SEARCH_DELAY_MIN, config.SEARCH_DELAY_MAX))

            if not new_urls_found:
                scroll_attempts += 1
            else:
                scroll_attempts = 0

        logger.info("Found %d total card URLs. Starting detail extraction.", len(card_urls))

        for card_url in card_urls[:config.SCROLL_TARGET_RESULTS]:
            try:
                logger.info("Visiting details for: %s", card_url)
                await page.goto(card_url)
                place = await self._extract_current_place(page, card_url, city, category)
                results.append(place)
            except Exception as e:
                logger.error("Failed to extract details from card %s: %s", card_url, e)

        return results

    async def _extract_current_place(self, page: Page, url: str, city: str, category: str) -> dict:
        """Extracts business details from the currently loaded page."""
        # Wait for the name element (h1) to load
        await page.wait_for_selector("h1", timeout=config.PAGE_LOAD_TIMEOUT_MS)
        
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
