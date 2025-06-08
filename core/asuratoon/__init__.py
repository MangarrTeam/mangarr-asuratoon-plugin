from plugins.base import MangaPluginBase, Formats, AgeRating, Status, NO_THUMBNAIL_URL
import requests
from datetime import datetime
import pytz
import re
from bs4 import BeautifulSoup
from lxml import etree, html
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import logging
logger = logging.getLogger(__name__)

class AsuraToon(MangaPluginBase):
    languages = ["en"]
    base_url = "https://asuracomic.net"

    def search_manga(self, query:str, language:str=None) -> list[dict]:
        logger.debug(f'Searching for "{query}"')
        try:
            words = re.findall(r"[A-z]*", query)
            filtered_words = [w for w in words if len(w) > 0]
            result = " ".join(filtered_words).lower()
            response = requests.get(f'{self.base_url}/series',
                                        params={
                                            "name": result,
                                        },
                                        timeout=10
                                        )
            
            response.raise_for_status()

            return self.get_manga_list_from_html(response.text)

        except Exception as e:
            logger.error(f'Error while searching manga - {e}')

        return []
    
    def get_manga_list_from_html(self, document) -> list[dict]:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))
        mangaList = dom.xpath("//a[starts-with(@href,'series')]")

        if not mangaList and len(mangaList) == 0:
            return []
        
        mangas = []
        for m in mangaList:
            manga_dict = self.search_manga_dict()
            url = m.get("href")
            if url is None:
                continue
            manga_dict["url"] = f'{self.base_url}/{url}'
            img_node = m.xpath(".//img")
            manga_dict["cover"] = (img_node[0].get("src") or NO_THUMBNAIL_URL) if len(img_node) > 0 else NO_THUMBNAIL_URL
            name_node = m.xpath("./div/div/div[2]/span[1]")
            if len(name_node) == 0:
                continue
            manga_dict["name"] = name_node[0].text

            mangas.append(manga_dict)

        return mangas

    def get_manga(self, arguments:dict) -> dict:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_manga_from_html(response.text, url)

        except Exception as e:
            logger.error(f'Error while getting manga - {e}')

        return {}
    
    def get_manga_from_html(self, document, url) -> dict:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))
        genreNodes = dom.xpath("//h3[text()='Genres']/../div/button")

        manga = self.get_manga_dict()
        manga["tags"] = [t.text for t in genreNodes]

        statusNode = dom.xpath("//h3[text()='Status']/../h3[2]")[0]
        statuses = {
            "ongoing": Status.ONGOING,
            "hiatus": Status.HIATUS,
            "completed": Status.COMPLETED,
            "dropped": Status.CANCELLED,
            "season end": Status.ONGOING,
            "coming soon": Status.ONGOING,
        }

        manga["complete"] = (statuses.get(statusNode.text.lower()) or Status.UNKNOWN) == Status.COMPLETED

        titleNode = dom.xpath("//title")[0]
        match = re.match(r"(.*) - Asura Scans", titleNode.text)
        if match:
            manga["name"] = match.group(1)

        coverNode = dom.xpath("//img[@alt='poster' and @width >= 200 and @height >= 350]")[0]
        coverParentNode = coverNode.getparent().getparent()
        descriptionNode = coverParentNode.xpath(".//span/p")[0]

        descriptionHtml = html.fromstring(etree.tostring(descriptionNode))

        manga["description"] = descriptionHtml.text_content()

        manga["url"] = url

        return manga
    
    def get_chapters(self, arguments:dict) -> list[dict]:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            response = requests.get(url,
                                    timeout=10
                                    )
            response.raise_for_status()

            return self.get_chapters_list_from_html(response.text, url, arguments)

        except Exception as e:
            logger.error(f'Error while getting chapters - {e}')

        return []
        
    def get_chapters_list_from_html(self, document, url, arguments) -> list[dict]:
        soup = BeautifulSoup(document, 'lxml')
        dom = etree.HTML(str(soup))
        chapterList = dom.xpath("//a[contains(@href, '/chapter/')]")

        name_rex = re.compile(
            r"Chapter\s+(\d+(?:\.\d+)?)(.*)?$"
        )
        tz = pytz.timezone("UTC")
        added_urls = set()
        chapters = []
        for chapter in chapterList[::-1]:
            chapter_infos = chapter.xpath("./h3")
            if len(chapter_infos) < 2:
                continue
            name_element = html.fromstring(etree.tostring(chapter_infos[0]))
            date_element = html.fromstring(etree.tostring(chapter_infos[1]))
            chapter_dict = self.get_chapter_dict()
            chapter_dict["source_url"] = chapter_dict["url"]

            if chapter_dict["url"] in added_urls:
                continue

            added_urls.add(chapter_dict["url"])

            name_match = name_rex.match(name_element.text_content())
            chapter_dict["chapter_number"] = name_match.group(1)
            chapter_dict["url"] = f'{url}/chapter/{chapter_dict["chapter_number"]}'
            chapter_dict["name"] = name_match.group(2) if name_match and name_match.group(2) and len(name_match.group(2).strip()) > 1 else str(chapter_dict["chapter_number"])
            date_str = date_element.text_content()

            if date_str:
                try:
                    clean_date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
                    dt = datetime.strptime(clean_date_str, "%B %d %Y")
                    dt_tz = tz.localize(dt)
                finally:
                    chapter_dict["release_date"] = dt_tz

            chapter_dict["arguments"] = arguments
            chapter_dict["page_count"] = 0


            chapters.append(chapter_dict)

        return chapters
    
    def get_pages(self, arguments:dict) -> list[dict]:
        try:
            url = arguments.get("url")
            if url is None:
                raise Exception("There is no URL in arguments")
            
            self.driver.set_page_load_timeout(10)
            self.driver.get(url)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//img[contains(@alt, 'chapter page')]"))
            )
            pages = self.get_pages_list_from_html(self.driver.page_source, arguments)

            self.close_driver()
            
            return pages

        except Exception as e:
            logger.error(f'Error while getting pages - {e}')

        return []
    
    def get_pages_list_from_html(self, document, arguments) -> list[dict]:
        dom = html.fromstring(document)

        pages = []
        images = dom.xpath("//img[contains(@alt, 'chapter page')]")
        for page in images:
            page_dict = self.get_page_dict()
            page_dict["url"] = page.get("src")
            pages.append(page_dict)
        
        return pages