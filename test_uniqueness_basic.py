import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.uniqueness.checker import UniquenessChecker


def test_checker():
    checker = UniquenessChecker()
    text = "Это тестовый пример текста. Он должен быть очищен от стоп-слов и знаков препинания!"
    print(f"Original: {text}")

    cleaned = checker.preprocess_text(text)
    print(f"Cleaned: {cleaned}")

    shingles = checker.get_shingles(text, n=3)
    print(f"Shingles: {shingles}")


if __name__ == "__main__":
    test_checker()
