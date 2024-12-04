import re

import pandas as pd
import fitz
import langid

from ParserLib import *
from tabulate import tabulate

langid.set_languages(['ru', 'uk', 'en'])

exclude_words = ["Часть", "Part", "Частина"]


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

                if cleaned_text.isupper():
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
    article_df = pd.read_json("articles_data.json")
    finish_result_df = pd.DataFrame(
        columns=['Parent_Key', 'UDC', 'Title', 'Language', 'Category', 'Authors', 'Annotation'])

    for id_key in article_df.columns:
        pdf_path = article_df.loc['pdf_url', id_key]
        print(f"ID: {id_key}, PDF Path: {pdf_path}")
        print("pdf_path" + pdf_path)

        print("################## FIRST 1 #####################")
        block = find_uppercase_blocks_with_details(pdf_path)
        df = pd.DataFrame(block)
        # print_pretty_df(df)

        print("################## SECOND 2 #####################")
        target_left_margin = df['left_margin'].mode()[0]
        page_numbers = df['page_num'].unique().tolist()

        data = find_blocks_with_left_margin(
            pdf_path,
            target_left_margin=target_left_margin,
            page_numbers=page_numbers
        )
        # print(data)
        # print_pretty_df(data)
        # print("################## ENd pdf  #####################")
        finish_result_df = process_data(data, finish_result_df, id_key)
        # print_pretty_df(finish_result_df)

    # print("################## ALL DATA END FULL  #####################")
    # print_pretty_df(finish_result_df)
    # finish_result_df.to_json('result.json')
    finish_result_df.to_csv("finish_result_df.csv")


def find_blocks_with_left_margin(pdf_path, target_left_margin, page_numbers):
    pdf_document = fitz.open(pdf_path)
    results = {}
    author_len = 0
    page_numbers.sort()

    for page_number in page_numbers:

        page = pdf_document.load_page(page_number - 1)
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
                    if len(found_blocks) == 2:
                        print(found_blocks)
                        author_len = len(found_blocks[1])
                        print(author_len)

        if found_blocks:
            results[page_number] = found_blocks

    if len(results.keys()) > 2:
        results.update({"_".join(map(str, sorted(results.keys())[-2:])): sum(
            [results.pop(k) for k in sorted(results.keys())[-2:]], [])})
    # print(len(results[list(results.keys())[1]]))
    if len(results[list(results.keys())[1]]) > 6:
        index = 3
        temp = results[list(results.keys())[1]]
        while index < len(temp):
            # print(len(temp[index]))
            # print(len(temp[index]) == author_len)
            if len(temp[index]) == author_len:
                part1 = temp[:index]
                part2 = temp[index:]

                combined = ''.join(map(str, part1[2:]))
                combined2 = ''.join(map(str, part2[2:]))
                result1 = part1[:2] + [combined] if combined else part1
                result2 = part2[:2] + [combined] if combined2 else part2

                new_result = result1 + result2
                results[list(results.keys())[1]] = new_result
                break
            else:
                index = index + 1
        else:
            print("error ")

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
    result = []
    df = pd.read_csv('finish_result_df.csv')
    grouped = df.groupby('Parent_Key')
    for parent_key, group in grouped:
        entry = {
            "UDC": group['UDC'].iloc[0] if 'UDC' in group.columns else None,
            "key": parent_key,
            "ru": {
                "title": group[group['Language'] == 'ru']['Title'].iloc[0] if not group[
                    group['Language'] == 'ru'].empty else None,
                "author": group[group['Language'] == 'ru']['Annotation'].iloc[0] if not group[
                    group['Language'] == 'ru'].empty else None,
            },
            "ua": {
                "title": group[group['Language'] == 'ukr']['Title'].iloc[0] if not group[
                    group['Language'] == 'ukr'].empty else None,
                "author": group[group['Language'] == 'ukr']['Authors'].iloc[0] if not group[
                    group['Language'] == 'ukr'].empty else None,
                "annotation": group[group['Language'] == 'ukr']['Annotation'].iloc[0] if not group[
                    group['Language'] == 'ukr'].empty else None,
            },
            "en": {
                "title": group[group['Language'] == 'en']['Title'].iloc[0] if not group[
                    group['Language'] == 'en'].empty else None,
                "author": group[group['Language'] == 'en']['Authors'].iloc[0] if not group[
                    group['Language'] == 'en'].empty else None,
                "annotation": group[group['Language'] == 'en']['Annotation'].iloc[0] if not group[
                    group['Language'] == 'en'].empty else None,
            },
        }
        result.append(entry)

    with open("logs.txt", 'w', encoding="utf-8") as log_file:
        for item in result:
            print(item)
            index = item['key']

            author_ua = item["ua"]["author"]
            author_en = item["en"]["author"]
            author_ru = item["ru"]["author"]

            title_ua = item['ua']['title']
            title_ru = item['ru']['title']
            title_en = item['en']['title']

            annotation_ua = item['ua']['annotation']
            annotation_en = item['en']['annotation']

            udc = item['udc']

            content = (f"###############################\n"
                       f"########## ARTICLE {index} ##########\n"
                       f"###############################\n"
                       f"{index}) {author_en}\n"  # authors
                       f"{author_ua}\n"
                       f"{author_ru}\n"
                       f"\n"
                       f"{title_ua}\n"  # titles 
                       f"{title_en}\n"
                       f"{title_ru}\n"
                       f"\n"
                       f"{udc}\n"  # UDC
                       f"\n"
                       f"{annotation_ua}\n"  # annotation 
                       f"{annotation_en}\n"
                       f"\n"
                       )
            log_file.writelines(content)
