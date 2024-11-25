import csv
import time

import pandas as pd
import requests
import xml.etree.ElementTree as ET


def fetch_yandex_search_results(query, api_key):
    """Получает результаты поиска Яндекса по заданному запросу."""
    url = f"https://yandex.ru/search/xml?folderid=b1g23j57sahs3ggh02j8&apikey={api_key}&query={query}"
    response = requests.get(url)
    response.raise_for_status()  # Проверка на ошибки HTTP
    return response.text


def parse_yandex_results(xml_response, domains):
    """Парсит XML-ответ Яндекса и извлекает позиции указанных доменов."""
    try:
        root = ET.fromstring(xml_response)
        results = []
        for i, elem in enumerate(root.findall('.//doc')):
            curr_domain = elem.findtext('domain')
            if curr_domain:
                for domain in domains:
                    if domain == curr_domain:
                        query = root.findtext('.//query')
                        results.append({'query': query, 'domain': elem.findtext('domain'), 'position': i + 1})
                        break
        return results
    except ET.ParseError:
        print("Ошибка парсинга XML")
        return []
    except Exception as e:
        print(f"Ошибка: {e}")
        return []


def process_queries(queries, domains, api_key):
    """Обрабатывает список запросов и возвращает позиции доменов."""
    all_results = []
    for query in queries:
        xml_response = fetch_yandex_search_results(query, api_key)
        results = parse_yandex_results(xml_response, domains)
        all_results.extend(results)
        time.sleep(0.5)  # Пауза для допустимого количества запросов в секунду
    return all_results


def write_results_to_file(results_csv, results):
    """Записывает результаты в файл."""
    with open(results_csv, 'w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['query', 'domain', 'position']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def calculate_shares(results_csv):
    """Вычисляет долю доменов"""
    df = pd.read_csv(results_csv)
    if df.empty:
        return False
    shares = {
        'Топ1': df[df['position'] <= 1].groupby('domain').size(),
        'Tоп3': df[df['position'] <= 3].groupby('domain').size(),
        'Топ5': df[df['position'] <= 5].groupby('domain').size(),
        'Топ10': df[df['position'] <= 10].groupby('domain').size()
    }

    shares_df = pd.DataFrame(shares).fillna(0).astype(int)
    shares_df.index.name = 'Домен'
    shares_df.reset_index(inplace=True)
    return shares_df.to_string(index=False)
