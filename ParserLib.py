from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def get_random_headers():
    ua = UserAgent()
    return {
        'User-Agent': ua.random,
        'Accept-Language': 'en-GB,en;uk;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'close',
        'DNT': '1'
    }


def header_for_download_pdf(url):
    ua = UserAgent()
    return {
        "User-Agent": ua.random,
        "Referer": url,
    }


def get_full_page_content(url: str):
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=12)
        response.raise_for_status()

        if not response.text.strip():
            print("The page is empty.")
            return None

        soup = BeautifulSoup(response.text, "lxml")
        body = soup.find("body")

        if not body:
            print("The <body> tag was not found.")
            return None

        return body

    except requests.exceptions.RequestException as e:
        print(f"Error while fetching the page: {e}")
        return None


def find_rows_by_years(bs: BeautifulSoup, years: List[int]) -> List[BeautifulSoup]:
    """
    Ищет строки таблицы (`<tr>`), содержащие указанные годы.
    """
    rows = bs.find_all("tr")
    matching_rows = []
    for row in rows:
        if any(str(year) in row.text for year in years):
            matching_rows.append(row)
    return matching_rows


def parse_row_to_links(row: BeautifulSoup) -> Dict[int, List[str]]:
    """
    Распарсивает строку таблицы `<tr>` и возвращает год и ссылки.
    """
    result = {}
    cells = row.find_all("td")
    year = None

    for cell in cells:
        if cell.find("strong"):
            try:
                year = int(cell.text.strip())
                result[year] = []
            except ValueError:
                continue
        elif cell.find("a"):
            link = cell.find("a")["href"]
            if year:
                result[year].append(link)

    return result


def process_table(url: str, years: List[int]) -> None:
    """
    Processes the table, fetches the page content, and writes unique URLs for each year to a JSON file.
    """
    json_filename = "all_years_data.json"

    if os.path.exists(json_filename):
        with open(json_filename, 'r') as f:
            existing_data = json.load(f)
            if existing_data:
                print(f"{json_filename} already contains data. Exiting...")
                return

    bs = get_full_page_content(url)
    rows = find_rows_by_years(bs, years)

    year_data = defaultdict(list)

    for row in rows:
        year_links = parse_row_to_links(row)
        for year, links in year_links.items():
            if year in years:
                for link in links:
                    if link not in year_data[year]:
                        year_data[year].append(link)

    json_filename = "all_years_data.json"

    if os.path.exists(json_filename):
        with open(json_filename, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    existing_data.update(year_data)

    with open(json_filename, 'w') as f:
        json.dump(existing_data, f, indent=4)

    print(f"All data saved to {json_filename}")


def save_to_json(data, filename="articles_data.json"):
    with open(filename, 'w', encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    print(f"Data saved to {filename}")


def download_pdfs_from_urls() -> None:
    """
    Processes the all_years_data.json file, creates folders for each year and URL,
    fetches the webpage content, finds PDF links, and downloads them.
    """

    json_filename = "all_years_data.json"
    article_id = 0
    parent_url_counter = 1
    articles_data = {}

    if not os.path.exists(json_filename):
        print(f"{json_filename} not found!")
        return

    with open(json_filename, 'r') as f:
        all_years_data = json.load(f)

    for year, urls in all_years_data.items():
        year_folder = f"./{year}"
        os.makedirs(year_folder, exist_ok=True)

        for parent_url_counter, url in enumerate(urls, start=parent_url_counter):
            url_folder = os.path.join(year_folder, str(parent_url_counter))
            os.makedirs(url_folder, exist_ok=True)

            print(f"Processing URL for Year {year}, URL #{parent_url_counter}: {url}")
            body = get_full_page_content(url)
            if not body:
                print(f"Failed to fetch or parse the page for URL: {url}")
                continue

            articles = body.find_all("article", class_="article_summary")
            article_title = body.find("h4", class_="section_title").get_text(strip=True)
            article_id += 1

            for article_id, article in enumerate(articles, start=article_id):
                article_data = extract_article_data(article, article_title)
                if article_data["link"]:
                    # articles_data[article_data["link"]] = article_data
                    articles_data[article_id] = article_data
                    url = article_data['link']
                    download_link = get_full_page_content(url).find("a", class_="btn btn-primary")["href"]
                    pdf_filename = os.path.join(url_folder, f"{article_id}.pdf")
                    try:
                        print(f"Downloading PDF #{article_id} from {download_link}...")

                        response = requests.get(download_link, headers=header_for_download_pdf(url), stream=True)
                        response.raise_for_status()

                        with open(pdf_filename, "wb") as pdf_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                pdf_file.write(chunk)

                        print(f"Successfully downloaded: {pdf_filename}")

                        articles_data[article_id]['pdf_url'] = os.path.normpath(pdf_filename)

                    except requests.exceptions.RequestException as e:
                        print(f"Failed to download PDF from {download_link}. Error: {e}")
    save_to_json(articles_data)


def extract_article_data(article , article_title ) -> dict:
    title = article.find("a", class_="summary_title").get_text(strip=True)
    authors = article.find("div", class_="authors").get_text(strip=True)
    pages = article.find("div", class_="pages").get_text(strip=True)

    link = article.find("a", class_="obj_galley_link")["href"] if article.find("a", class_="obj_galley_link") else None

    return {
        "article": article_title,
        "title": title,
        "authors": authors,
        "pages": pages,
        "link": link,
    }


# def process_and_inspect_urls() -> None:
#     json_filename = "all_years_data.json"
#
#     if not os.path.exists(json_filename):
#         print(f"{json_filename} not found!")
#         return
#     with open(json_filename, 'r') as f:
#         all_years_data = json.load(f)
#
#     inspected_data = {}
#
#     for year, year_links in all_years_data.items():
#         inspected_data[year] = {}
#
#         for index, url in enumerate(year_links, start=1):
#             print(f"Inspecting URL for Year {year}, URL #{index}: {url}")
#             content = get_full_page_content(url)
#             inspected_data[year][f"URL_{index}"] = content
#             print(f"Content for URL #{index}:\n{content[:500]}...")  # Print the first 500 characters for brevity
#
#     new_json_filename = "inspected_urls_data.json"
#
#     with open(new_json_filename, 'w') as f:
#         json.dump(inspected_data, f, indent=4)
#
#     print(f"Inspected data saved to {new_json_filename}")

