# import httpx
# import trafilatura
# from bs4 import BeautifulSoup
# from playwright.async_api import async_playwright
# from fastapi import HTTPException


# async def scrape_website(url: str) -> str:
#     try:
#         # 1️⃣ Try static fetch first
#         async with httpx.AsyncClient(timeout=10) as client:
#             response = await client.get(url)
#             html = response.text

#         # 2️⃣ Detect SPA / empty content
#         if looks_like_spa(html) or len(html) < 2000:
#             html = await render_with_playwright(url)

#         # 3️⃣ Clean with trafilatura
#         text = trafilatura.extract(html)

#         if not text:
#             # fallback to basic extraction
#             soup = BeautifulSoup(html, "html.parser")
#             for tag in soup(["script", "style", "noscript"]):
#                 tag.decompose()
#             text = soup.get_text(separator=" ", strip=True)

#         if not text:
#             raise ValueError("No extractable content")

#         return text

#     except Exception as e:
#         raise HTTPException(500, f"Scraping failed: {str(e)}")


# def looks_like_spa(html: str) -> bool:
#     return (
#         'id="root"' in html
#         or 'id="app"' in html
#         or "window.__INITIAL_STATE__" in html
#     )


# async def render_with_playwright(url: str) -> str:
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         page = await browser.new_page()
#         await page.goto(url, wait_until="networkidle")
#         html = await page.content()
#         await browser.close()
#         return html

# app/services/ingestion/web.py
import re

import httpx
import trafilatura
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from fastapi import HTTPException
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class WebScraper:
    """Web scraping service with SPA support"""
    
    async def scrape(self, url: str, timeout: int = 30) -> str:
        """Scrape website content"""
        try:
            # 1️⃣ Try static fetch first
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                html = response.text
            
            # 2️⃣ Detect SPA / empty content
            if self.looks_like_spa(html) or len(html) < 2000:
                logger.info(f"Detected SPA or low content for {url}, using Playwright...")
                html = await self.render_with_playwright(url)
            
            # 3️⃣ Clean with trafilatura
            text = trafilatura.extract(html)
            
            if not text:
                # Fallback to basic extraction
                logger.info("Trafilatura extraction failed, using BeautifulSoup fallback...")
                text = self.extract_with_beautifulsoup(html)
            
            if not text:
                raise ValueError("No extractable content found")
            
            # Clean up text
            text = self.clean_text(text)
            
            logger.info(f"Successfully scraped {url}: {len(text)} characters extracted")
            return text
        
        except httpx.TimeoutException:
            logger.error(f"Timeout while scraping {url}")
            raise HTTPException(500, f"Timeout while scraping {url}")
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {str(e)}")
            raise HTTPException(500, f"Scraping failed: {str(e)}")
    
    def looks_like_spa(self, html: str) -> bool:
        """Detect if the page is a Single Page Application"""
        spa_indicators = [
            'id="root"',
            'id="app"',
            'id="__next"',
            'id="__nuxt"',
            'data-reactroot',
            'ng-app',
            'window.__INITIAL_STATE__',
            'window.__NUXT__',
            'window.__NEXT_DATA__'
        ]
        
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in spa_indicators)
    
    async def render_with_playwright(self, url: str, wait_until: str = "networkidle") -> str:
        """Render JavaScript-heavy pages with Playwright"""
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set user agent to avoid being blocked
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                # Navigate to URL
                await page.goto(url, wait_until=wait_until, timeout=30000)
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                # Get page content
                html = await page.content()
                
                await browser.close()
                return html
        
        except Exception as e:
            logger.error(f"Playwright rendering failed: {str(e)}")
            raise
    
    def extract_with_beautifulsoup(self, html: str) -> str:
        """Extract text using BeautifulSoup as fallback"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                tag.decompose()
            
            # Get text
            text = soup.get_text(separator=" ", strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            
            return text
        
        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed: {str(e)}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common noise patterns
        noise_patterns = [
            r'Cookie Policy',
            r'Privacy Policy',
            r'Terms of Service',
            r'All rights reserved',
            r'© \d{4}',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    async def scrape_multiple(self, urls: List[str]) -> List[dict]:
        """Scrape multiple URLs concurrently"""
        import asyncio
        
        tasks = [self.scrape(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        scraped_data = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                scraped_data.append({
                    "url": url,
                    "success": False,
                    "error": str(result),
                    "content": None
                })
            else:
                scraped_data.append({
                    "url": url,
                    "success": True,
                    "content": result,
                    "error": None
                })
        
        return scraped_data