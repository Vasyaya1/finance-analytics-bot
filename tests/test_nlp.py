import tempfile
from pathlib import Path

from _nlp_holdout import HELD_OUT
from finbot.analytics import nlp


def test_amount_with_spaces_is_parsed():
    amount, _ = nlp.process_natural_language_transaction("оплатили аренду 50 000 руб")
    assert amount == 50000.0


def test_marketing_phrase():
    amount, category = nlp.process_natural_language_transaction("заплатил за рекламу 15000")
    assert (amount, category) == (15000.0, "marketing_budget")


def test_revenue_phrase():
    amount, category = nlp.process_natural_language_transaction("эквайринг пришел 85000")
    assert (amount, category) == (85000.0, "revenue")


def test_no_number_returns_none():
    assert nlp.process_natural_language_transaction("просто текст без суммы") == (None, None)


def test_low_confidence_phrase_is_unknown():
    # незнакомая лексика -> уверенность ниже порога 0.40 -> запрос категории у пользователя
    _, category = nlp.process_natural_language_transaction("штраф гибдд 1500")
    assert category == "unknown"


def test_active_learning_teaches_new_phrase():
    old_file = nlp.DB_FILE
    with tempfile.TemporaryDirectory() as tmp:
        nlp.DB_FILE = str(Path(tmp) / "ml_dataset.json")
        try:
            assert nlp.add_new_phrase_and_retrain("штраф гибдд 1500", "fixed_costs")
            _, category = nlp.process_natural_language_transaction("штраф гибдд 1500")
            assert category == "fixed_costs"
        finally:
            nlp.reset_nlp_dataset()  # возвращаем «заводской» датасет
            nlp.DB_FILE = old_file


def test_active_learning_does_not_mutate_golden_standard():
    size_before = len(nlp.TRAIN_DATA)
    old_file = nlp.DB_FILE
    with tempfile.TemporaryDirectory() as tmp:
        nlp.DB_FILE = str(Path(tmp) / "ml_dataset.json")
        try:
            nlp.add_new_phrase_and_retrain("оплата хостинга", "fixed_costs")
            assert len(nlp.TRAIN_DATA) == size_before
        finally:
            nlp.reset_nlp_dataset()
            nlp.DB_FILE = old_file
    assert len(nlp.TRAIN_DATA) == size_before


def test_training_set_is_balanced_and_clean():
    from collections import Counter

    counts = Counter(cat for _, cat in nlp.TRAIN_DATA)
    assert set(counts) == {"fixed_costs", "variable_costs", "marketing_budget", "revenue"}
    assert min(counts.values()) >= 40
    assert max(counts.values()) <= 1.5 * min(counts.values())
    phrases = [p for p, _ in nlp.TRAIN_DATA]
    assert len(phrases) == len(set(phrases))  # без дубликатов


def test_held_out_phrases_have_no_leakage():
    train = {p for p, _ in nlp.TRAIN_DATA}
    assert not [p for ps in HELD_OUT.values() for p in ps if p in train]


def test_held_out_accuracy():
    # Фразы не входят в обучение. Порог с запасом: при замере было 34/40 верно, 6 «спросит», 0 ошибок.
    ok = wrong = 0
    for category, phrases in HELD_OUT.items():
        for phrase in phrases:
            _, predicted = nlp.process_natural_language_transaction(phrase + " 10000")
            if predicted == category:
                ok += 1
            elif predicted != "unknown":
                wrong += 1
    total = sum(len(v) for v in HELD_OUT.values())
    assert ok >= 0.75 * total
    assert wrong <= 0.05 * total  # молчаливых ошибок почти нет
