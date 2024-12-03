import pandas as pd
import langid
langid.set_languages(['eng', 'uk','rus'])

# Исходные данные
data = {
    1: ['УДК 519.68', 'А.М. Гупал, А.А. Вагис', 'МАТЕМАТИКА И ЖИВАЯ ПРИРОДА. \nУДИВИТЕЛЬНЫЙ МИР ДНК'],
    6: [
        'А.М. Гупал, О.А. Вагіс',
        'МАТЕМАТИКА ТА ЖИВА ПРИРОДА. \nДИВОВИЖНИЙ СВІТ ДНК',
        'Обгрунтовано, що жива природа розвивається на основі індуктивних механіз-\nмів. У геномі людини в зашифрованому вигляді містяться ефективні індуктивні \nпроцедури, що керують генами і модифікують їх.',
        'A.M. Gupal, A.A. Vagis',
        'MATHEMATICS AND LIVING NATURE. \nTHE WONDERFUL WORLD OF DNA',
        'It is justified that the living nature is progressing on the basis of inductive mecha-\nnisms. In the encoded form, effective inductive procedures, which control genes and \nmodify them, are contained in human genom.'
    ]
}


# Создаем функцию обработки
def process_data(data):
    rows = []

    for key, values in data.items():
        row = {'UDK': None, 'author_rus': None, 'author_ukr': None, 'author_eng': None,
               'title_rus': None, 'title_ukr': None, 'title_eng': None,
               'annotation_rus': None, 'annotation_ukr': None, 'annotation_eng': None}

        for value in values:
            lang, _ = langid.classify(value)
            if value.startswith('УДК'):
                row['UDK'] = value
            elif lang == 'ru':
                if not row['author_rus']:
                    row['author_rus'] = value
                elif not row['title_rus']:
                    row['title_rus'] = value
                else:
                    row['annotation_rus'] = value
            elif lang == 'uk':
                if not row['author_ukr']:
                    row['author_ukr'] = value
                elif not row['title_ukr']:
                    row['title_ukr'] = value
                else:
                    row['annotation_ukr'] = value
            elif lang == 'en':
                if not row['author_eng']:
                    row['author_eng'] = value
                elif not row['title_eng']:
                    row['title_eng'] = value
                else:
                    row['annotation_eng'] = value

        rows.append(row)

    return pd.DataFrame(rows)


df = process_data(data)

print(df)
