import requests
from bs4 import BeautifulSoup
import re
import pymorphy2
import os
from urllib.parse import urljoin
import concurrent.futures
import inspect

# Патч для Python 3.11+
if not hasattr(inspect, 'getargspec'):
    from inspect import getfullargspec
    def getargspec(func):
        argspec = getfullargspec(func)
        return argspec.args, argspec.varargs, argspec.varkw, argspec.defaults
    inspect.getargspec = getargspec

# Инициализация морфологического анализатора
try:
    morph = pymorphy2.MorphAnalyzer()
except Exception as e:
    print(f"Ошибка инициализации pymorphy2: {e}")
    exit(1)

# Список стоп-слов
STOP_WORDS = {'и', 'в', 'на', 'не', 'что', 'это', 'с', 'по'}

# Положительные ключевые слова
KEYWORDS = {
    'вшэ', 'высшая школа экономики', 'ниу вшэ', 'поступление', 'абитуриент', 'приёмная комиссия',
    'егэ', 'олимпиада', 'вступительные испытания', 'баллы', 'проходной балл', 'зачисление',
    'документы', 'сроки подачи', 'бакалавриат', 'магистратура', 'аспирантура', 'программа',
    'факультет', 'образование', 'специальность', 'курсы', 'учебный план', 'дисциплины',
    'двойной диплом', 'международные программы', 'кампус', 'москва', 'санкт-петербург',
    'нижний новгород', 'пермь', 'общежитие', 'библиотека', 'аудитория', 'учёба', 'семестр',
    'сессия', 'экзамен', 'преподаватель', 'лекция', 'семинар', 'практика', 'исследование',
    'наука', 'стоимость обучения', 'бюджетные места', 'платное обучение', 'стипендия', 'грант',
    'скидка', 'финансовая помощь', 'студент', 'студенческая жизнь', 'мероприятия', 'клубы',
    'спорт', 'волонтёрство', 'карьера', 'трудоустройство', 'лицей вшэ', 'минор',
    'международное сотрудничество', 'рейтинг', 'партнёры', 'инновации', 'цифровое обучение'
}

# Негативные ключевые слова
NEGATIVE_KEYWORDS = {
    'cookies', 'куки', 'использование', 'браузер', 'настройка',
    'удобство', 'работа сайт', 'сайт ниу вшэ',
    'персональный данные', 'правило обработка', 'согласный',
    'конфиденциальность', 'политика', 'пользоваться сайт',
    'организационноправовой', 'локальный акт', 'федеральный орган', 'государственный задание',
    'финансовохозяйственный', 'проинформировать',
    'востребовать', 'последний документ'
}

# Заголовки для запросов
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Ненужные теги и классы для очистки
UNWANTED_TAGS = ["script", "style", "meta", "link", "iframe", "noscript"]
UNWANTED_CLASSES = ["sv-control__block", "browser_outdate", "gdpr_bar", "fa-footer", "control_lang2"]

# Функция для парсинга страницы с предварительной очисткой
def fetch_webpage(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем ненужные теги
        for tag in UNWANTED_TAGS:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Удаляем элементы по классам
        for class_name in UNWANTED_CLASSES:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):  # re.I для игнора регистра
                element.decompose()
        
        # Удаляем дополнительные ненужные элементы (footer, nav)
        for element in soup.find_all(["footer", "nav"]):
            element.decompose()
        
        # Извлекаем крупные текстовые блоки
        sections = []
        for tag in soup.find_all(['div', 'section', 'article'], recursive=True):
            text = tag.get_text(separator='\n', strip=True)
            if text and len(text.split()) > 10:
                sections.append(text)
        
        # Собираем ссылки
        links = [urljoin(url, a.get('href')) for a in soup.find_all('a', href=True)]
        return sections, links
    except requests.RequestException as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return [], []

# Функция очистки текста (только для проверки релевантности)
def clean_text_for_check(text):
    text = re.sub(r'[^а-яА-Яa-zA-Z0-9\s]', '', text.lower())
    words = text.split()
    cleaned = [morph.parse(word)[0].normal_form for word in words if word not in STOP_WORDS]
    return ' '.join(cleaned)

# Проверка релевантности блока
def is_relevant_section(text, keywords, negative_keywords):
    cleaned_text = clean_text_for_check(text)
    words = set(cleaned_text.split())
    word_count = len(words)
    
    positive_score = sum(1 for keyword in keywords if keyword.lower() in words)
    negative_score = sum(1 for neg_keyword in negative_keywords if neg_keyword.lower() in words)
    
    return positive_score > 0 and negative_score < positive_score and word_count >= 10

# Сохранение текста в файл (все релевантные блоки в один файл)
def save_to_file(sections, url, output_dir='pages'):
    if not sections:
        return None
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Преобразуем URL в безопасное имя файла
    filename = re.sub(r'[/:?&=]', '_', url.split('https://www.hse.ru')[1]) or 'main'
    filepath = f"{output_dir}/{filename}.txt"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"{url}\n\n")
        for i, section in enumerate(sections):
            # f.write(f"Блок {i + 1}:\n{section}\n\n")
            f.write(f"{section}\n\n") # Для векторизации следует избегать лишних слов
    
    return filepath

# Проверка, является ли страница английской или китайской
def is_excluded_language(url):
    return '/en' in url or \
        '/cn' in url or \
        '/data' in url or \
        '/news' in url or \
        '/staff' in url or \
        '#' in url or \
        'vision=enabled' in url or \
        not 'hse.ru' in url or not 'https' in url or \
        'iri.hse.ru' in url or '/intpartners' in url or '/international' in url

# Обработка одной страницы (возвращает новые ссылки)
def process_page(url, visited):
    if url in visited:
        return set()
    
    sections, links = fetch_webpage(url)
    visited.add(url)
    new_links = set()
    
    # Пропускаем обработку текста для неподходящих страниц
    if not is_excluded_language(url):
        if sections:
            print(f"Обрабатываю: {url} ({len(sections)} блоков)")
            # Фильтруем релевантные блоки
            relevant_sections = [section for section in sections if is_relevant_section(section, KEYWORDS, NEGATIVE_KEYWORDS)]
            
            if relevant_sections:
                saved_file = save_to_file(relevant_sections, url)
                print(f"Сохранён файл для {url}: {saved_file} ({len(relevant_sections)} блоков)")
            else:
                print(f"Нет релевантных блоков на {url}")
        else:
            print(f"Нет блоков на {url}")
    else:
        print(f"Пропущена обработка текста для {url}")

    # Собираем новые ссылки в очередь, даже с en/ и cn/
    for link in links:
        if link.startswith('https://www.hse.ru') and any(kw in link.lower() for kw in ['admissions', 'education', 'campus', 'students']) and link not in visited:
            new_links.add(link)
    
    return new_links

# Основная функция с многопоточностью
def crawl_website(start_url):
    visited = set()
    to_visit = {start_url}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        while to_visit:
            # Берем пачку URL для обработки
            batch = list(to_visit)
            to_visit.clear()
            
            # Параллельно обрабатываем страницы
            future_to_url = {executor.submit(process_page, url, visited): url for url in batch}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    new_links = future.result()
                    to_visit.update(new_links)
                except Exception as e:
                    print(f"Ошибка обработки {url}: {e}")
            
            print(f"Обработано страниц: {len(visited)}, осталось в очереди: {len(to_visit)}")

if __name__ == "__main__":
    start_url = "https://www.hse.ru/"
    crawl_website(start_url)