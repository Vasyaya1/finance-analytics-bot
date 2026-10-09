import json
import os
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

from .nlp_dataset import TRAIN_DATA


DB_FILE = os.getenv('NLP_DATASET_PATH', 'ml_dataset.json')

def load_dataset():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return list(TRAIN_DATA)  # копия: «золотой стандарт» TRAIN_DATA не должен мутировать при дообучении

current_dataset = load_dataset()
nlp_pipeline = make_pipeline(TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 6)), MultinomialNB())

def train_model():
    global nlp_pipeline, current_dataset
    X_train, y_train = zip(*current_dataset)
    nlp_pipeline.fit(X_train, y_train)

train_model()

def process_natural_language_transaction(text):
    clean_text = text.lower()
    while re.search(r'(?<=\d)\s+(?=\d)', clean_text):
        clean_text = re.sub(r'(?<=\d)\s+(?=\d)', '', clean_text)
        
    numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', clean_text)
    if not numbers:
        return None, None
        
    amount = max([float(n.replace(',', '.')) for n in numbers])
    
    text_for_ml = re.sub(r'\d+', '', clean_text)
    text_for_ml = re.sub(r'\b(руб|рубл|рублей|р|тыс|тысяч)\b', '', text_for_ml).strip()
    text_for_ml = re.sub(r'\b(закинул|купил|отдал|оплатил|заплатил|потратил|перевел|скинул|внес)\b', '', text_for_ml).strip()

    if not text_for_ml:
        return amount, "unknown"

    probs = nlp_pipeline.predict_proba([text_for_ml])[0]
    max_prob = max(probs)
    
    if max_prob < 0.40:
        return amount, "unknown"
        
    category = nlp_pipeline.classes_[np.argmax(probs)]
    
    return amount, category

def add_new_phrase_and_retrain(text, category):
    global current_dataset
    
    clean_text = text.lower()
    text_for_ml = re.sub(r'\d+', '', clean_text)
    text_for_ml = re.sub(r'\b(руб|рубл|рублей|р|тыс|тысяч)\b', '', text_for_ml).strip()
    text_for_ml = re.sub(r'\b(закинул|купил|отдал|оплатил|заплатил|потратил|перевел|скинул|внес)\b', '', text_for_ml).strip()
    
    if not text_for_ml:
        return False

    for _ in range(3):
        current_dataset.append([text_for_ml, category])
    
    base_len = len(TRAIN_DATA)
    if len(current_dataset) > 2000:
        current_dataset = TRAIN_DATA + current_dataset[base_len + 300:]
    
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(current_dataset, f, ensure_ascii=False, indent=2)
        
    train_model()
    return True

def reset_nlp_dataset():
    global current_dataset
    current_dataset = list(TRAIN_DATA)
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    train_model()
