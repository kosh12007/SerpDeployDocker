import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import nltk
from nltk.corpus import stopwords

# Загружаем стоп-слова (один раз)
nltk.download('stopwords', quiet=True)
STOP_WORDS_RU = stopwords.words('russian') + ['это', 'который', 'очень', 'еще', 'также']

def extract_page_data(url, params=None):
    """
    Извлекает данные со страницы по списку параметров.
    
    Доступные параметры:
        'lsi_words'      → топ LSI-слова (по 5 темам)
        'text_length'    → объём текста без пробелов (в символах)
        'title'          → <title>
        'description'    → meta[name="description"]
        'headings'       → список H1-H6
    
    Возвращает dict только с запрошенными параметрами.
    """
    if params is None:
        params = ['lsi_words', 'text_length', 'title', 'description', 'headings']
    
    result = {}
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; PageAnalyzer/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Не удалось загрузить страницу: {e}"}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # --- 1. Title ---
    if 'title' in params:
        title = soup.find('title')
        result['title'] = title.get_text(strip=True) if title else None
    
    # --- 2. Meta Description ---
    if 'description' in params:
        desc = soup.find('meta', attrs={'name': 'description'}) or \
               soup.find('meta', attrs={'property': 'og:description'})
        result['description'] = desc['content'].strip() if desc and desc.get('content') else None
    
    # --- 3. Заголовки H1-H6 ---
    if 'headings' in params:
        headings = []
        for level in range(1, 7):
            for h in soup.find_all(f'h{level}'):
                text = h.get_text(strip=True)
                if text:
                    headings.append({'level': level, 'text': text})
        result['headings'] = headings if headings else None
    
    # --- 4. Текст для анализа ---
    paragraphs = [p.get_text() for p in soup.find_all('p')]
    clean_paragraphs = []
    full_text = ""
    
    for p in paragraphs:
        cleaned = re.sub(r'\s+', ' ', p.lower())
        cleaned = re.sub(r'[^a-zа-я0-9\s]', '', cleaned)
        cleaned = cleaned.strip()
        if len(cleaned.split()) > 3:  # фильтр мусора
            clean_paragraphs.append(cleaned)
            full_text += cleaned + " "
    
    full_text = full_text.strip()
    
    # --- 5. Объём текста без пробелов ---
    if 'text_length' in params:
        result['text_length'] = len(re.sub(r'\s+', '', full_text))
    
    # --- 6. LSI-слова ---
    if 'lsi_words' in params and clean_paragraphs:
        try:
            vectorizer = TfidfVectorizer(
                stop_words=STOP_WORDS_RU,
                ngram_range=(1, 2),
                max_df=0.85,
                min_df=1,
                token_pattern=r'(?u)\b\w\w+\b'
            )
            X = vectorizer.fit_transform(clean_paragraphs)
            
            # LSI через SVD
            lsi = TruncatedSVD(n_components=5, random_state=42)
            lsi.fit(X)
            
            terms = vectorizer.get_feature_names_out()
            lsi_topics = []
            
            for i, comp in enumerate(lsi.components_):
                terms_comp = zip(terms, comp)
                top_terms = sorted(terms_comp, key=lambda x: x[1], reverse=True)[:10]
                lsi_topics.append([term for term, weight in top_terms])
            
            result['lsi_words'] = lsi_topics
        except Exception as e:
            result['lsi_words'] = f"Ошибка LSI: {e}"
    elif 'lsi_words' in params:
        result['lsi_words'] = None
    
    return result