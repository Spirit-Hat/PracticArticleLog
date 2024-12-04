import json
import re
from logging import warning

import pandas as pd
import fitz
import langid
from tabulate import tabulate
from utils.pdf_utils import find_uppercase_blocks_with_details, format_and_clean_text, get_literature_count

langid.set_languages(['ru', 'uk', 'en'])


def print_pretty_df(df):
    print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))


def find_blocks_with_left_margin(pdf_path, author_len, target_left_margin, page_numbers):
    pdf_document = fitz.open(pdf_path)
    results = {}
    page_numbers.sort()

    for page_number in page_numbers:

        page = pdf_document.load_page(page_number - 1)
        blocks = page.get_text("dict")["blocks"]
        found_blocks = []

        for block in blocks:
            if block["type"] == 0:
                bbox = block["bbox"]
                left_margin = bbox[0]

                if abs(left_margin - target_left_margin) < 0.5:
                    block_text = "\n".join(
                        " ".join(span["text"] for span in line["spans"])
                        for line in block["lines"]
                    ).strip()
                    found_blocks.append(block_text)

        if found_blocks:
            results[page_number] = found_blocks

    if len(results.keys()) > 2:
        results.update({"_".join(map(str, sorted(results.keys())[-2:])): sum(
            [results.pop(k) for k in sorted(results.keys())[-2:]], [])})

    key = list(results.keys())[1]
    print("LIST:" + str(key))

    if len(results[key]) > 6:
        index = 3
        temp = results[key]
        while index < len(temp):
            print(f"TEMP AUTHOR LEN: {len(temp[index])}")
            if abs(len(temp[index]) - author_len) <= 3:
                part1 = temp[:index]
                part2 = temp[index:]

                combined = ''.join(map(str, part1[2:]))
                combined2 = ''.join(map(str, part2[2:]))
                result1 = part1[:2] + [combined] if combined else part1
                result2 = part2[:2] + [combined] if combined2 else part2

                new_result = result1 + result2
                print(len(new_result))
                results[key] = new_result
                break
            else:
                index = index + 1
        else:
            warning("ERROR!!!")

    pdf_document.close()
    print(len(results[key]))
    return results


def process_data(data, df=None, index=0, year=2006, magazine_number=1, pages="", article_title="", used_literature=0):
    if df is None:
        df = pd.DataFrame(
            columns=['Parent_Key', 'UDC', 'year', 'pages', 'used_literature', 'Title', 'Language', 'Category',
                     'Authors', 'Annotation'])

    rows = []

    for parent_key, items in data.items():
        if parent_key == next(iter(data)):
            udc = items[0]
            authors = items[1]
            if index == 22:
                print(items)
            title_language = langid.classify(items[2])
            category = title_language[0]

            rows.append({
                'Parent_Key': index,
                'UDC': udc,
                'Title': items[2],
                'Language': title_language[0],
                'Category': category,
                'Authors': authors,
                'Annotation': None,

                'year': year,
                'pages': pages,
                'magazine_number': magazine_number,
                'used_literature': used_literature,
                'article_title': article_title
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
                    category = 'uk'
                    title_language = ('uk', title_language[1])

                rows.append({
                    'Parent_Key': index,
                    'UDC': None,
                    'Title': title,
                    'Language': title_language[0],
                    'Category': category,
                    'Authors': authors,
                    'Annotation': annotation,

                    'year': year,
                    'pages': pages,
                    'magazine_number': magazine_number,
                    'used_literature': used_literature,
                })

    new_df = pd.DataFrame(rows)
    df = pd.concat([df, new_df], ignore_index=True)

    return df


def main(ignore_ids: []):
    article_df = pd.read_json("input/articles_data.json")
    finish_result_df = pd.DataFrame(
        columns=['Parent_Key', 'UDC', 'year', 'pages', 'used_literature', 'Title', 'Language', 'Category', 'Authors',
                 'Annotation'])

    for id_key in article_df.columns:
        if id_key not in ignore_ids:
            pdf_path = article_df.loc['pdf_url', id_key]
            article_title = article_df.loc['article', id_key]
            year = pdf_path[:4]

            pattern = r"\\(\d+)\\"
            magazine_number = re.findall(pattern, pdf_path)[0]

            pages = article_df.loc['pages', id_key]
            link = article_df.loc['link', id_key]
            author_len = article_df.loc['authors', id_key]
            author_len = len(author_len)

            print(f"ID -> {id_key}")
            print(f"LINK -> {link}")
            print(f"pdf_path -> {pdf_path}")

            print("################## FIRST 1 #####################")
            block = find_uppercase_blocks_with_details(pdf_path)
            df = pd.DataFrame(block)
            print_pretty_df(df)

            print("################## SECOND 2 #####################")
            target_left_margin = df['left_margin'].mode()[0]
            page_numbers = df['page_num'].unique().tolist()

            data = find_blocks_with_left_margin(
                pdf_path,
                author_len=author_len,
                target_left_margin=target_left_margin,
                page_numbers=page_numbers
            )
            # print(data)
            print_pretty_df(data)
            # print("################## ENd pdf  #####################")
            used_literature = get_literature_count(pdf_path)
            finish_result_df = process_data(data,
                                            finish_result_df,
                                            id_key,
                                            year=year,
                                            magazine_number=magazine_number,
                                            pages=pages,
                                            article_title=article_title,
                                            used_literature=used_literature)

    # print("################## ALL DATA END FULL  #####################")
    # print_pretty_df(finish_result_df)
    # finish_result_df.to_json('result.json')
    finish_result_df.to_csv("result/finish_result_df.csv")


def debug(id):
    with open('input/articles_data.json', 'r') as file:
        start_data = json.load(file)

    start_data = start_data[str(id)]
    pdf_path = start_data["pdf_url"]
    author_len = start_data["authors"]
    author_len = len(author_len)
    print(f"author_len: {author_len}")
    pages = start_data["pages"]

    finish_result_df = pd.DataFrame(
        columns=['Parent_Key', 'UDC', 'Title', 'Language', 'Category', 'Authors', 'Annotation'])

    print("################### CODE PART 0 ##########################")
    block = find_uppercase_blocks_with_details(pdf_path)
    df = pd.DataFrame(block)
    print_pretty_df(df)
    print("################### CODE PART 1 ##########################")
    data = find_blocks_with_left_margin(pdf_path,
                                        author_len=author_len,
                                        target_left_margin=df['left_margin'].drop_duplicates().iloc[0],
                                        page_numbers=df['page_num'].drop_duplicates().tolist())

    print_pretty_df(data)
    print("################## CODE PART 2 #####################")
    finish_result_df = process_data(data, finish_result_df, 1)
    print_pretty_df(finish_result_df)
    print("################## END #####################")


def create_txt_log(input_file="result/finish_result_df.csv", output_file="result/logs.txt"):
    df = pd.read_csv(input_file)
    grouped = df.groupby('Parent_Key')
    with open(output_file, 'w', encoding="utf-8") as log_file:
        for parent_key, group in grouped:
            udc = group['UDC'].iloc[0] if 'UDC' in group.columns else None
            udc = udc[4:]

            article_title = group['article_title'].iloc[0] if 'article_title' in group.columns else None
            magazine_number = group['magazine_number'].iloc[0] if 'magazine_number' in group.columns else None
            used_literature = group['used_literature'].iloc[0] if 'used_literature' in group.columns else None
            year = group['year'].iloc[0] if 'year' in group.columns else None
            pages = group['pages'].iloc[0] if 'pages' in group.columns else None

            key = parent_key

            title_en = group[group['Language'] == 'en']['Title'].iloc[0] if not group[
                group['Language'] == 'en'].empty else None

            title_ua = group[group['Language'] == 'uk']['Title'].iloc[0] if not group[
                group['Language'] == 'uk'].empty else None

            title_ru = group[group['Language'] == 'ru']['Title'].iloc[0] if not group[
                group['Language'] == 'ru'].empty else None

            title_en = format_and_clean_text(title_en)
            title_ua = format_and_clean_text(title_ua)
            title_ru = format_and_clean_text(title_ru)

            author_ua = group[group['Language'] == 'uk']['Authors'].iloc[0] if not group[
                group['Language'] == 'uk'].empty else None

            author_en = group[group['Language'] == 'en']['Authors'].iloc[0] if not group[
                group['Language'] == 'en'].empty else None

            author_ru = group[group['Language'] == 'ru']['Authors'].iloc[0] if not group[
                group['Language'] == 'ru'].empty else None

            annotation_ua = group[group['Language'] == 'uk']['Annotation'].iloc[0] if not group[
                group['Language'] == 'uk'].empty else None

            annotation_en = group[group['Language'] == 'en']['Annotation'].iloc[0] if not group[
                group['Language'] == 'en'].empty else None

            author_ru_formated = format_and_clean_text(author_ru, format_text=False)

            template_desc = (f"{title_ru} / {author_ru_formated} // Проблемы управления и информатики. — {year}."
                             f" — № {magazine_number}. — С. {pages}. — Бібліогр.: {used_literature} назв. — рос.")

            padding = "#" * 40
            key_padding = "#" * len(str(key))
            content = (f"{padding}############{key_padding}{padding}\n"
                       f"{padding}# ARTICLE {key} #{padding}\n"
                       f"{padding}############{key_padding}{padding}\n"
                       f"\n"
                       f"{key}) {author_en}\n"  # authors
                       f"{author_ua}\n"
                       f"{author_ru}\n"
                       f"\n"
                       f"{title_ua}\n"  # titles
                       f"{title_ru}\n"
                       f"{title_en}\n"
                       f"\n"
                       f"{template_desc}\n"
                       f"\n"
                       f"{article_title}\n"
                       f"\n"
                       f"{udc}\n"  # UDC
                       f"\n"
                       f"{annotation_ua}\n"  # annotation 
                       f"\n"
                       f"{annotation_en}\n"
                       f"\n"
                       )

            log_file.writelines(content)


if __name__ == '__main__':
    # debug(id=107)
    # ignore_ids = [76, 77, 107, 137]
    # main(ignore_ids=ignore_ids)
    create_txt_log()
