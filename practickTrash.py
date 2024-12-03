import os

import pandas as pd
import re
import fitz
import langid
from ParserLib import process_table, download_pdfs_from_urls

langid.set_languages(['uk', 'en', 'ru'])


def extract_first_three_lines(reader, pdf_path):
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
                print(pdf_path)
            else:
                print(f"Файл {pdf_path} не знайдено.")


def find_titles(pdf_path):
    """
    Ищет блоки текста, которые полностью состоят из заглавных букв.

    :param pdf_path: Путь к PDF файлу
    :return: Список найденных блоков с текстом из заглавных букв
    """
    uppercase_blocks = []

    # Открываем PDF-документ
    pdf_document = fitz.open(pdf_path)
    pattern = re.compile(r"[-.–ЇІЄА-ЯA-Z0-9]+")
    # Проходим по всем страницам
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)

        # Извлекаем текст в виде блоков
        blocks = page.get_text("dict")["blocks"]
        # print(page.get_text())
        for block in blocks:
            if block["type"] == 0:  # Если это текстовый блок
                block_text = " ".join(
                    span["text"] for line in block["lines"] for span in line["spans"]
                ).strip()

                # Проверяем, состоит ли текст только из заглавных букв (исключая цифры и символы)
                if block_text and block_text.isupper():
                    uppercase_blocks.append(block_text)

    pdf_document.close()
    cleaned = []

    for uppercase_block in uppercase_blocks:
        matches = pattern.findall(uppercase_block)
        merged = " ".join(matches).strip()
        if len(merged) > 3:
            cleaned.append(merged)

    filtered_set = []

    for item in cleaned:
        # Check if the string contains 'ISSN' or 'УДК' (case-insensitive)
        if re.search(r'УДК', item, re.IGNORECASE):
            filtered_set.append(item)
        else:
            # Remove leading and trailing whitespace
            stripped_item = item.strip()
            # Remove spaces from the item
            item_no_spaces = stripped_item.replace(' ', '')
            # Define criteria for a title-like string
            if len(stripped_item) > 30:
                # Count the number of letters
                letters = sum(1 for c in item_no_spaces if c.isalpha())
                # Calculate the total number of characters excluding spaces
                total_chars = len(item_no_spaces)
                # Calculate the ratio of letters to total characters
                if total_chars > 0:
                    ratio = letters / total_chars
                    # If the ratio is greater than 80%, consider it a title
                    if ratio > 0.9:
                        filtered_set.append(item)

    uppercase_block = filtered_set
    UDK = None
    titles = []
    for title in uppercase_block:
        if not re.search(r'УДК', title, re.IGNORECASE):
            titles.append(title)
        else:
            UDK = title
    titles = titles if len(titles) == 3 else [titles[0], titles[-1], titles[-2]]
    return titles, UDK


def extract_paragraphs_from_pdf_reverse(pdf_path):
    # Відкрити PDF-документ
    pdf_document = fitz.open(pdf_path)
    paragraphs = []

    # Пройтись по сторінках у зворотному порядку
    for page_num in range(len(pdf_document) - 1, -1, -1):
        page = pdf_document[page_num]
        text = page.get_text("text")  # Витягнути текст зі сторінки
        # Розділити текст на параграфи за новим рядком
        page_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraphs.extend(page_paragraphs)

    pdf_document.close()
    return paragraphs


def extract_text_around_titles(paragraph, translated_titles):
    result = {}

    for lang, title in translated_titles.items():
        if title in paragraph:
            # Знаходимо текст над заголовком (остання строка)
            pattern_above = fr"(.*?)(?={re.escape(title)})"
            match_above = re.search(pattern_above, paragraph, re.DOTALL)
            if match_above:
                lines_above = match_above.group(1).strip().splitlines()
                text_above = lines_above[-1].strip() if lines_above else None
            else:
                text_above = None

            # Знаходимо текст під заголовком (до першої точки)
            pattern_below = fr"(?<={re.escape(title)})(.*?\.)(?!.*\.)"
            match_below = re.search(pattern_below, paragraph, re.DOTALL)
            text_below = match_below.group(1).strip() if match_below else None

            result[lang] = {
                "title": title,
                "above": text_above,
                "below": text_below
            }

    return result


if __name__ == '__main__':
    # url = "https://jais.net.ua/index.php/files/archive"
    # years_to_find = [2006, 2007]
    # process_table(url, years_to_find)
    # download_pdfs_from_urls()
    # main()

    # translator = Translator()
    # text = translator.translate("TO BUILDING OF INTEGRAL MODELS  OF DISTRIBUTED SPACE-TIME PROCESSES", src="en", dest='ru').text
    # print(text)

    pdf_path = r"2006\1\2.pdf"
    titles, UDK = find_titles(pdf_path=pdf_path)
    paragraphs = extract_paragraphs_from_pdf_reverse(pdf_path=pdf_path)

    translated_titles = {
        "ru": titles[0],
        "eng": titles[2],
        "uk": titles[1],
    }

    for title in titles:
        detected_lang, score = langid.classify(title)
        print(detected_lang, score, title)

    print(titles)
    print(UDK)

    paragraph = """
    Проблемы управления и информатики, 2006, № 1–2  
    25 
    ющей по правилам (6), (7), в отдельный уровень. Естественным продолжением 
    этой логической цепочки и оказался вывод об иерархичности системы управления 
    целесообразно управляемого объекта (8). 
    Оценивая предложенный критерий отбора действительных движений в жи-
    вой материи, следует ожидать его принципиального неприятия со стороны иссле-
    дователей, не согласных с трактовкой естественных процессов в живой природе 
    как оптимально управляемых. Достаточно убедительная критика концепции оп-
    тимальности в биологии приведена в монографии [9]. Трудно не признать акту-
    альность тезиса о том, что «понятие оптимальности биосистемы не соответствует 
    постановке задачи об оптимальных системах в теории управления» [9, с. 104]. 
    Прямое свидетельство его справедливости — совершенство биологических си-
    стем управления, a priori недостижимое в системах технических. Тем не менее 
    провозглашенный в процитированной выше концепции всеобщей оптимальности 
    Л. Эйлера поиск критериев оптимальности живого продолжается (см., например, 
    обзор [53]). Особенно важно отметить понимание необходимости перехода уже 
    выполненного количества проб в новое качество: методологически актуальным 
    становится требование «отыскать доводы не к угадыванию, а к выводу самих 
    функционалов, на которых могло бы базироваться вариационное моделирова-
    ние» [54, с. 515].  
    Различие позиций исследователей живого по отношению к оптимальности 
    как раз и есть, на наш взгляд, то внутреннее противоречие, которое стимулирует 
    дальнейший поиск. Эффективным инструментом разрешения этого противоречия 
    представляется АП-принципиальное взаимодействие ученых, идея которого вы-
    сказана выдающимся специалистом в области методологии биологии С.В. Мейе-
    ном еще в 1976 г.: «В мысль мы хотим проникнуть только через мысль, но ведь 
    принятие истинности для каждого лежит и через чувство, через веру в истинность 
    принятых постулатов. Стало быть, настоящее понимание инакомыслящего невоз-
    можно без сочувствия, без того, что можно назвать со-интуицией. Без этого не-
    возможно взаимопонимание, а без последнего немыслимо снятие антиномий. 
    Единомыслию так или иначе должно предшествовать со-чувствие» (цитируется 
    по [55, с. 15], курсив С.В. Мейена).  
     
    Б.М. Кіфоренко, С.І. Кіфоренко 
    ПРИНЦИП АНОХІНА–ПАРЕТО ЯК КРИТЕРІЙ ВІДБОРУ ДІЙСНИХ РУХІВ У ЖИВІЙ ПРИРОДІ 
    Обговорюється принцип мінімуму втрат енергії керування Анохіна–Парето як 
    критерій відбору дійсних рухів з множини допустимих. Принцип запропонова-
    но авторами в 1991 р. як специфічну для живої природи форму загального дос-
    лідного принципу мінімуму дисипації енергії.  
    B.N. Kiforenko, S.I. Kiforenko 
    THE ANOKHIN–PARETO PRINCIPLE AS A CRITERION OF THE REAL MOTION SELECTION IN LIVING NATURE 
    The Anokhin–Pareto principle of control energy loss minimum as a criterion of the 
    real motion selection from the set of admissible ones is discussed. The principle has 
    been proposed by the authors as a specific form of application of the general empiri-
    cal minimum energy dissipation principle to living matter in 1991 year.
    """

    results = extract_text_around_titles(paragraph, translated_titles)
    for lang, content in results.items():
        print(f"Language: {lang}")
        print(f"Title: {content['title']}")
        print(f"Above:\n{content['above']}\n")
        print(f"Below:\n{content['below']}\n")


