import re
import fitz


def find_uppercase_blocks_with_details(pdf_path):
    exclude_words = ["Часть", "Part", "Частина", "h-", "h-ВИКЛИКІВ", "h", "h-ВЫЗОВОВ", "МЕТОДЫ ОБРАБОТКИ ИНФОРМАЦИИ"]

    uppercase_blocks_with_details = []
    pdf_document = fitz.open(pdf_path)

    first_page = pdf_document.load_page(0)
    blocks = first_page.get_text("dict")["blocks"]

    for block in blocks:
        if block["type"] == 0:
            block_text = " ".join(
                span["text"] for line in block["lines"] for span in line["spans"]
            ).strip()

            if any(ignore_word in block_text for ignore_word in ["©", "УДК", "ISSN"]):
                continue

            alphanumeric_count = len([word for word in block_text.split() if word.isalnum() and len(word) > 1])

            if alphanumeric_count < 3:
                continue

            bbox = block["bbox"]
            if bbox[0] <= 150:
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

                alphanumeric_count = len([word for word in block_text.split() if word.isalnum() and len(word) > 1])

                if alphanumeric_count < 3:
                    continue

                cleaned_text = re.sub(r'\b(?:' + '|'.join(re.escape(word) for word in exclude_words) + r')\b', '',
                                      block_text).strip()

                if cleaned_text.isupper():
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


def get_literature_count(pdf_path):
    pdf_document = fitz.open(pdf_path)
    last_page_number = pdf_document.page_count - 1
    last_page = pdf_document.load_page(last_page_number)
    blocks = last_page.get_text("dict")["blocks"]
    pattern = r"^\d+\.$"
    matching_numbers = []
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()

                    if re.match(pattern, text):
                        matching_numbers.append(text)
    return matching_numbers[-1][:-1]

def format_and_clean_text(input_text, format_text=True):
    if not input_text:
        return ""
    lines = input_text.strip().split("\n")
    formatted_lines = []
    capitalize_flag = False
    for index, line in enumerate(lines, start=0):
        line = line.strip()

        if format_text:
            if capitalize_flag or index == 0:
                line = line.capitalize()
            else:
                line = line.lower()

        capitalize_flag = line.endswith(".")
        formatted_lines.append(line)

    return " ".join(formatted_lines)