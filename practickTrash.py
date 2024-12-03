

import os
from collections import defaultdict

import pandas as pd
from PyPDF2 import PdfReader
import fitz
from googletrans import Translator
import langid

from ParserLib import process_table, download_pdfs_from_urls

langid.set_languages(['fr', 'en'])
def extract_first_three_lines(reader,pdf_path):
    try:
        text = reader.pages[0].extract_text()
        lines = text.split('\n')[2:6]
        lines = [str(line).strip() for line in lines]
        return "\n".join(lines)
    except Exception as e:
        print(f"Помилка при обробці {pdf_path}: {e}")
        return ""
def main():
    articles_data = pd.read_json("articles_data.json")
    pdf_urls_string = articles_data.iloc[4]

    with open("logs.txt", 'w', encoding="utf-8") as log_file:
        for index, pdf_path in enumerate(pdf_urls_string):
                if os.path.exists(pdf_path):

                    # print("###############################\n" )
                    # pdf_document = fitz.open(pdf_path)
                    # for page_num in range(pdf_document.page_count):
                    #     page = pdf_document.load_page(page_num)
                    #     text = page.get_text("text")
                    #
                    #     print(f"Страница {page_num + 1}:")
                    #     print(text)
                    #     print("\n" + "=" * 50 + "\n")
                    # pdf_document.close()
                    # print("###############################\n" )

                    print(str(index) +" " +  "+" * 35)
                    print(pdf_path)
                    reader = PdfReader(pdf_path)
                    for i in range(-1, -len(reader.pages) - 1, -1):
                        try:
                            last_part = reader.pages[i].extract_text()
                            if last_part.strip():
                                last_part = last_part.split("\n ")[1]
                                break
                        except IndexError:
                            continue
                    if not last_part:
                        last_part = "Немає тексту"
                    extracted_text = extract_first_three_lines(reader,pdf_path)
                    log = (f"###############################\n"
                           f"########## ARTICLE {index + 1} ##########\n"
                           f"###############################\n"
                           f"\n"
                           f"{extracted_text}\n"
                           f"{last_part}\n"
                           f"\n")
                    log_file.writelines(log)
                else:
                    print(f"Файл {pdf_path} не знайдено.")


def find_blocks_by_title(pdf_path, input_title):

    detected_lang, score = langid.classify(input_title)
    print(f"Detected language: {detected_lang}")

    # Переводим title на другие два языка
    translator = Translator()

    # Словарь для переведенных заголовков
    translated_titles = {
        "rus": None,
        "ukr": None,
        "eng": input_title  # Начинаем с исходного тайтла
    }

    if detected_lang != 'en':
        translated_titles['eng'] = translator.translate(input_title, src=detected_lang, dest='en').text

    if detected_lang != 'ru':
        translated_titles['rus'] = translator.translate(input_title, src=detected_lang, dest='ru').text

    if detected_lang != 'uk':
        translated_titles['ukr'] = translator.translate(input_title, src=detected_lang, dest='uk').text

    # Открываем PDF
    pdf_document = fitz.open(pdf_path)

    # Храним блоки для каждого языка
    found_blocks = {
        "ukr": None,
        "rus": None,
        "eng": None
    }

    # Проходим по всем страницам
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)

        # Получаем текст в виде блоков
        # blocks = page.get_text("dict",flags=fitz.TEXTFLAGS_BLOCKS )["blocks"]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Если это текстовый блок
                for line in block["lines"]:
                    for spans in line["spans"]:
                        block_text = spans["text"]

                        # Проверяем на наличие переведенных title
                        for lang, translated_title in translated_titles.items():
                            if translated_title in block_text:
                                found_blocks[lang] = block_text
                                # Если все блоки найдены, можем завершить
                                if all(found_blocks.values()):
                                    pdf_document.close()
                                    return found_blocks

    pdf_document.close()
    return found_blocks


def find_uppercase_blocks(pdf_path):
    """
    Ищет блоки текста, которые полностью состоят из заглавных букв,
    игнорируя блоки, содержащие строки с "©", "УДК", или "ISSN".

    :param pdf_path: Путь к PDF файлу
    :return: Список найденных блоков с текстом из заглавных букв
    """
    uppercase_blocks = []

    # Открываем PDF-документ
    pdf_document = fitz.open(pdf_path)

    # Проходим по всем страницам
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)

        # Извлекаем текст в виде блоков
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # Если это текстовый блок
                block_text = " ".join(
                    span["text"] for line in block["lines"] for span in line["spans"]
                ).strip()

                # Проверяем, нужно ли игнорировать блок
                if any(ignore_word in block_text for ignore_word in ["©", "УДК", "ISSN"]):
                    continue

                # Проверяем, состоит ли текст только из заглавных букв (исключая цифры и символы)
                if block_text and block_text.isupper():
                    uppercase_blocks.append(block_text)

    pdf_document.close()
    return uppercase_blocks



def get_specific_block_margin(pdf_path):
    """
    Определяет отступ от левого края для блока с заданным текстом.

    :param pdf_path: Путь к PDF файлу
    :return: Генератор, возвращающий найденные блоки (bbox, left_margin, block_text)
    """
    target_text = "\n".join([
        "УДК 519.68",
        "А.М. Гупал, А.А. Вагис",
        "МАТЕМАТИКА И ЖИВАЯ ПРИРОДА.",
        "УДИВИТЕЛЬНЫЙ МИР ДНК"
    ])

    pdf_document = fitz.open(pdf_path)
    page = pdf_document[0]  # Первая страница

    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if block["type"] == 0:  # Если это текстовый блок
            block_text = "\n".join(
                " ".join(span["text"] for span in line["spans"])
                for line in block["lines"]
            ).strip()

            # Сравниваем текст блока с целевым текстом
            if any(target_part in block_text for target_part in target_text.split("\n")):
                bbox = block["bbox"]  # Ограничивающая рамка блока
                left_margin = bbox[0]  # x0 — координата левого края
                yield bbox, left_margin, block_text  # Возвращаем найденный блок

    pdf_document.close()
def find_blocks_with_left_margin(pdf_path, target_left_margin,page_number):
    """
    Находит все блоки на первой странице с заданным левым отступом.

    :param pdf_path: Путь к PDF файлу
    :param target_left_margin: Левый отступ, который нужно найти
    :return: Список найденных блоков (bbox, left_margin, block_text)
    """
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[page_number]

    blocks = page.get_text("dict")["blocks"]
    found_blocks = []

    for block in blocks:
        if block["type"] == 0:  # Если это текстовый блок
            bbox = block["bbox"]  # Ограничивающая рамка блока
            left_margin = bbox[0]  # x0 — координата левого края

            # Если левый отступ соответствует целевому значению
            if left_margin == target_left_margin:
                block_text = "\n".join(
                    " ".join(span["text"] for span in line["spans"])
                    for line in block["lines"]
                ).strip()

                found_blocks.append((bbox, left_margin, block_text))  # Добавляем найденный блок в список

    pdf_document.close()

    if found_blocks:
        return found_blocks
    else:
        return None

def find_uppercase_blocks_with_details(pdf_path):
    uppercase_blocks_with_details = []

    pdf_document = fitz.open(pdf_path)

    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)

        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:
                block_text = " ".join(
                    span["text"] for line in block["lines"] for span in line["spans"]
                ).strip()

                if any(ignore_word in block_text for ignore_word in ["©", "УДК", "ISSN"]):
                    continue

                if block_text and block_text.isupper():
                    bbox = block["bbox"]
                    left_margin = bbox[0]
                    uppercase_blocks_with_details.append({
                        "page_num": page_num + 1,
                        "bbox": bbox,
                        "left_margin": left_margin,
                        "block_text": block_text
                    })

    pdf_document.close()
    return uppercase_blocks_with_details



if __name__ == '__main__':
    # url = "https://jais.net.ua/index.php/files/archive"
    # years_to_find = [2006, 2007]
    # process_table(url, years_to_find)
    # download_pdfs_from_urls()
    # main()
    # print(find_blocks_by_title(input_title="MATHEMATICS AND LIVING NATURE",pdf_path=r"2006\1\1.pdf" ))

    # uppercase_blocks = find_uppercase_blocks(r"2006\1\1.pdf")
    # for block in uppercase_blocks:
    #     print(block)

    # pdf_path = r"2006\1\1.pdf"
    # found_blocks = find_aligned_blocks(pdf_path)
    #
    # for block in found_blocks:
    #     print(block)

    pdf_path = r"2006\1\1.pdf"
    # for bbox, left_margin, block_text in get_specific_block_margin(pdf_path):
    #     print(bbox, left_margin, block_text)

    # target_left_margin = 182.82000732421875
    # found_blocks = find_blocks_with_left_margin(pdf_path, target_left_margin, 5)
    #
    # if found_blocks:
    #     for bbox, left_margin, block_text in found_blocks:
    #         print(f"Bbox: {bbox}, Left Margin: {left_margin}, Text: {block_text}")
    # else:
    #     print("Не найдено блоков с заданным левым отступом.")

    block = find_uppercase_blocks_with_details(pdf_path)
    df = pd.DataFrame(block)
    unique_pages = df['page_num'].drop_duplicates()
    print(unique_pages)




