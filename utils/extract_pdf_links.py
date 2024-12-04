import os
import json
from collections import defaultdict
from typing import List
from utils.util import get_full_page_content, find_rows_by_years, parse_row_to_links


def extract_pdf_links(url: str, years: List[int], passed = False) -> None:
    """
    Processes the table, fetches the page content, and writes unique URLs for each year to a JSON file.
    """
    if passed:
        return

    json_filename = "all_years_data.json"
    existing_data = {}

    bs = get_full_page_content(url)
    rows = find_rows_by_years(bs, years)
    year_data = defaultdict(list)

    for row in rows:
        year_links = parse_row_to_links(row)
        for year, links in year_links.items():
            if year in years:
                for link in links:
                    if link not in year_data[year]:
                        year_data[year].append(link)


    existing_data.update(year_data)
    sorted_data = dict(sorted(existing_data.items()))

    with open(json_filename, 'w') as f:
        json.dump(sorted_data, f, indent=4)

    print(f"All data saved to {json_filename}")