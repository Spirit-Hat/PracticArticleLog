import json
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


def save_to_json(data, filename="input/articles_data.json"):
    with open(filename, 'w', encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    print(f"Data saved to {filename}")


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

