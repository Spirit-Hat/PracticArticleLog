import json
import requests
import os
from utils.util import get_full_page_content, extract_article_data, header_for_download_pdf, save_to_json


def download_pdfs() -> None:
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
                    download_link = get_full_page_content(url).find("a", class_="btn-primary")["href"]
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