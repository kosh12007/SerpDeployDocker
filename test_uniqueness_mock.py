from app.uniqueness.checker import UniquenessChecker
import logging
import sys

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


class MockUniquenessChecker(UniquenessChecker):
    def __init__(self):
        # Skip credentials check
        self.user = "test"
        self.key = "test"
        self.base_url = "http://test"

    def check_shingle_xmlriver(self, shingle: str):
        # Mock: if shingle contains "copied", it's non-unique
        if "copied" in shingle:
            return ["http://example.com/plagarism"]
        return []


def test_mock_logic():
    checker = MockUniquenessChecker()

    # Text: "This is a unique text but here is copied content end"
    # Words: this, is, a, unique, text, but, here, is, copied, content, end (11 words)
    # Shingles (len 3):
    # 1. this is a
    # 2. is a unique
    # 3. a unique text
    # 4. unique text but
    # 5. text but here
    # 6. but here is
    # 7. here is copied (MATCH)
    # 8. is copied content (MATCH)
    # 9. copied content end (MATCH)

    text = "This is a unique text but here is copied content end"

    print("\n--- Test Stride 1 (Check All) ---")
    result = checker.check_text(text, shingle_len=3, stride=1)
    print(f"Score: {result['score']}%")
    print(
        f"Non-unique shingles: {result['non_unique_shingles']} / {result['checked_shingles']}"
    )

    # Expected: 9 shingles. 3 contain "copied".
    # Non-unique: 3.
    # Score: (1 - 3/9)*100 = 66.67%

    print("\n--- Test Stride 3 ---")
    result2 = checker.check_text(text, shingle_len=3, stride=3)
    # Checked shingles indices: 0, 3, 6, ...
    # 0: "this is a" (unique)
    # 3: "unique text but" (unique)
    # 6: "but here is" (unique) (Wait, indices are 0-based in list)
    # List: [0, 1, 2, 3, 4, 5, 6, 7, 8]
    # Stride 3: [0, 3, 6] -> all unique.
    # Mock check: "copied" is in 7, 8 (conceptually, wait).
    # Shingles list:
    # 0: this is a
    # 1: is a unique
    # ...
    # 6: but here is
    # 7: here is copied
    # 8: is copied content
    # 9: copied content end
    # Actually split logic:
    # Words: [this, is, a, unique, text, but, here, is, copied, content, end]
    # 0: this is a
    # 1: is a unique
    # 2: a unique text
    # 3: unique text but
    # 4: text but here
    # 5: but here is
    # 6: here is copied -> MATCH
    # 7: is copied content -> MATCH
    # 8: copied content end -> MATCH

    # Stride 3 slices: [0, 3, 6]
    # 0: "this is a" -> Clean
    # 3: "unique text but" -> Clean
    # 6: "here is copied" -> MATCH!
    # So 1 out of 3 is non-unique.
    # Score: (1 - 1/3)*100 = 66.67%

    print(f"Score: {result2['score']}%")
    print(
        f"Non-unique shingles: {result2['non_unique_shingles']} / {result2['checked_shingles']}"
    )
    print("Matches:", result2["matches"])


if __name__ == "__main__":
    test_mock_logic()
