

import os
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
    Ищет блоки текста, которые полностью состоят из заглавных букв.

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

                # Проверяем, состоит ли текст только из заглавных букв (исключая цифры и символы)
                if block_text and block_text.isupper():
                    uppercase_blocks.append(block_text)

    pdf_document.close()
    return uppercase_blocks

if __name__ == '__main__':
    # url = "https://jais.net.ua/index.php/files/archive"
    # years_to_find = [2006, 2007]
    # process_table(url, years_to_find)
    # download_pdfs_from_urls()
    # main()
    # print(find_blocks_by_title(input_title="MATHEMATICS AND LIVING NATURE",pdf_path=r"2006\1\1.pdf" ))
    uppercase_blocks = find_uppercase_blocks(r"2006\1\1.pdf")
    for block in uppercase_blocks:
        print(block)
