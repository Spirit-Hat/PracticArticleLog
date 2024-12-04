import re

import pandas as pd
import fitz
import langid

from ParserLib import *
from tabulate import tabulate

langid.set_languages(['ru', 'uk', 'en'])

exclude_words = ["Часть", "Part", "Частина"]


# def find_uppercase_blocks_with_details(pdf_path):
#     uppercase_blocks_with_details = []
#
#     pdf_document = fitz.open(pdf_path)
#
#     for page_num in range(pdf_document.page_count):
#         page = pdf_document.load_page(page_num)
#
#         blocks = page.get_text("dict")["blocks"]
#
#         for block in blocks:
#             if block["type"] == 0:
#                 block_text = " ".join(
#                     span["text"] for line in block["lines"] for span in line["spans"]
#                 ).strip()
#
#                 if any(ignore_word in block_text for ignore_word in ["©", "УДК", "ISSN"]):
#                     continue
#
#                 if block_text and block_text.isupper():
#                     bbox = block["bbox"]
#                     left_margin = bbox[0]
#                     uppercase_blocks_with_details.append({
#                         "page_num": page_num + 1,
#                         "bbox": bbox,
#                         "left_margin": left_margin,
#                         "block_text": block_text
#                     })
#
#     pdf_document.close()
#     return uppercase_blocks_with_details

def find_uppercase_blocks_with_details(pdf_path):
    uppercase_blocks_with_details = []

    # ignored_patterns = [
    #     r"^\d*\s*\*?\s*[A-Z]+\s*[\+\-\*\/=]*\s*\(*[A-Z0-9]+\)*$",  # Математическое выражение с возможными пробелами
    #     r"^[A-Z\s\*\+\-=\(\)\d]+$",  # Строки, состоящие из заглавных букв и математических символов
    #     r"^[A-Z0-9\s\+\-=\(\)\*\/]+$",  # Вариант, если формула состоит из букв и чисел
    # ]


    pdf_document = fitz.open(pdf_path)

    first_page = pdf_document.load_page(0)
    blocks = first_page.get_text("dict")["blocks"]

    for block in blocks:
        if block["type"] == 0:
            block_text = " ".join(
                span["text"] for line in block["lines"] for span in line["spans"]
            ).strip()
            # if any(re.search(pattern, block_text) for pattern in ignored_patterns):
            #     continue

            if any(ignore_word in block_text for ignore_word in ["©", "УДК", "ISSN"]):
                continue

            alphanumeric_count = len([word for word in block_text.split() if word.isalnum() and len(word) > 1])

            if alphanumeric_count < 3:
                continue

            cleaned_text = re.sub(r'\b(?:' + '|'.join(re.escape(word) for word in exclude_words) + r')\b', '',
                                  block_text).strip()

            if cleaned_text.isupper():
                bbox = block["bbox"]
                left_margin = bbox[0]
                uppercase_blocks_with_details.append({
                    "page_num": 1,
                    "bbox": bbox,
                    "left_margin": left_margin,
                    "block_text": block_text
                })

    if len(uppercase_blocks_with_details) >= 3:
        pdf_document.close()
        return uppercase_blocks_with_details

    for page_num in range(pdf_document.page_count - 1, -1, -1):
        page = pdf_document.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:
                block_text = " ".join(
                    span["text"] for line in block["lines"] for span in line["spans"]
                ).strip()

                if any(ignore_word in block_text for ignore_word in ["©", "УДК", "ISSN"]):
                    continue

                # if any(re.search(pattern, block_text) for pattern in ignored_patterns):
                #     continue

                alphanumeric_count = len([word for word in block_text.split() if word.isalnum() and len(word) > 1])

                if alphanumeric_count < 3:
                    continue

                cleaned_text = re.sub(r'\b(?:' + '|'.join(re.escape(word) for word in exclude_words) + r')\b', '',
                                      block_text).strip()

                if cleaned_text.isupper() :
                        # and not any(re.search(pattern, block_text) for pattern in ignored_patterns)):
                    bbox = block["bbox"]
                    left_margin = bbox[0]
                    uppercase_blocks_with_details.append({
                        "page_num": page_num + 1,
                        "bbox": bbox,
                        "left_margin": left_margin,
                        "block_text": block_text
                    })

        if len(uppercase_blocks_with_details) >= 3:
            break

    pdf_document.close()
    return uppercase_blocks_with_details


def print_pretty_df(df):
    print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))
def main():
    articles_data = pd.read_json("articles_data.json")
    pdf_urls_string = articles_data.iloc[4]
    finish_result_df = pd.DataFrame(columns=['Parent_Key', 'UDC', 'Title', 'Language', 'Category', 'Authors', 'Annotation'])

    for index, pdf_path in enumerate(pdf_urls_string):
        print("pdf_path" + pdf_path)
        block = find_uppercase_blocks_with_details(pdf_path)
        print("################## First 1 #####################")
        df = pd.DataFrame(block)
        print_pretty_df(df)
        print("################## SECOND 2 #####################")
        data = find_blocks_with_left_margin(pdf_path, target_left_margin=df['left_margin'].drop_duplicates().iloc[0]
                                              , page_numbers=df['page_num'].drop_duplicates().tolist())
        print_pretty_df(data)
        print("################## ENd pdf  #####################")
        finish_result_df = process_data(data, finish_result_df, index)
        print_pretty_df(finish_result_df)

    print("################## ALL DATA END FULL  #####################")
    print_pretty_df(finish_result_df)

def find_blocks_with_left_margin(pdf_path, target_left_margin, page_numbers):

    pdf_document = fitz.open(pdf_path)
    results = {}

    for page_number in page_numbers:

        page = pdf_document.load_page(page_number - 1 )

        blocks = page.get_text("dict")["blocks"]
        found_blocks = []

        for block in blocks:
            if block["type"] == 0:
                bbox = block["bbox"]
                left_margin = bbox[0]

                if abs(left_margin - target_left_margin) < 1e-1:
                    block_text = "\n".join(
                        " ".join(span["text"] for span in line["spans"])
                        for line in block["lines"]
                    ).strip()

                    found_blocks.append((block_text))

        if found_blocks:
            results[page_number] = found_blocks

    if len(results.keys()) > 2:
        results.update({"_".join(map(str, sorted(results.keys())[-2:])): sum([results.pop(k) for k in sorted(results.keys())[-2:]], [])})

    pdf_document.close()
    return results



def process_data(data, df=None, index=0):
    if df is None:
        df = pd.DataFrame(columns=['Parent_Key', 'UDC', 'Title', 'Language', 'Category', 'Authors', 'Annotation'])

    rows = []

    for parent_key, items in data.items():
        if parent_key == next(iter(data)):
            udc = items[0]
            authors = items[1]
            title_language = langid.classify(items[2])
            category = title_language[0]



            rows.append({
                'Parent_Key': index,
                'UDC': udc,
                'Title': items[2],
                'Language': title_language[0],
                'Category': category,
                'Authors': authors,
                'Annotation': None
            })

        elif parent_key == next(reversed(data)):
            chunks = [items[i:i + 3] for i in range(0, len(items), 3)]
            for chunk in chunks:
                authors = chunk[0]
                title = chunk[1]
                annotation = chunk[2]
                title_language = langid.classify(title)
                category = title_language[0]
                if title_language[0] == 'ru' and any(row['Language'] == 'ru' for row in rows):
                    category = 'ukr'
                    title_language = ('ukr', title_language[1])

                rows.append({
                    'Parent_Key': index,
                    'UDC': None,  #
                    'Title': title,
                    'Language': title_language[0],
                    'Category': category,
                    'Authors': authors,
                    'Annotation': annotation
                })

    new_df = pd.DataFrame(rows)
    df = pd.concat([df, new_df], ignore_index=True)

    return df


def debug():
    finish_result_df = pd.DataFrame(
        columns=['Parent_Key', 'UDC', 'Title', 'Language', 'Category', 'Authors', 'Annotation'])

    pdf_path = r"2006\1\18.pdf"
    block = find_uppercase_blocks_with_details(pdf_path)
    df = pd.DataFrame(block)
    print(df)
    print_pretty_df(df)
    print("#############################################")
    data = find_blocks_with_left_margin(pdf_path, target_left_margin=df['left_margin'].drop_duplicates().iloc[0]
                                        , page_numbers=df['page_num'].drop_duplicates().tolist())
    print_pretty_df(data)
    print("################## SECOND 2 #####################")
    finish_result_df = process_data(data, finish_result_df, 1)
    print_pretty_df(finish_result_df)
    print("################## END #####################")


if __name__ == '__main__':
    # url = "https://jais.net.ua/index.php/files/archive"
    # years_to_find = [2006, 2007]
    # process_table(url, years_to_find)
    # download_pdfs_from_urls()

    # main()

    debug()



