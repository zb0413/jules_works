import asyncio
import csv
import re
from collections import Counter
import aiofiles
import aiofiles.os as aios # Import aios for async os operations
import os # For test file creation/deletion

# Basic English stop words list (can be expanded)
DEFAULT_ENGLISH_STOP_WORDS = [
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "but",
    "if", "or", "and", "of", "at", "by", "for", "from", "in", "out", "on", "to", # added "to"
    "with", "s", "t", "can", "will", "just", "don", "should", "now",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am"
]


async def _clean_text(text: str) -> str:
    """Basic text cleaning: lowercase and remove punctuation/numbers."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\d+', '', text)      # Remove numbers
    return text.strip()


async def _tokenize_text(text: str) -> list[str]:
    """Tokenize text into words."""
    if not text:
        return []
    return text.split()


async def _remove_stopwords(tokens: list[str], stop_words: list[str]) -> list[str]:
    """Remove stop words from a list of tokens."""
    if not tokens:
        return []
    return [token for token in tokens if token not in stop_words]


async def generate_keywords_from_csv_column_async(
    csv_file_path: str,
    text_column_name: str,
    top_n: int = 10,
    custom_stop_words: list[str] | None = None
) -> list[str]:
    """
    Generates keywords from a specified text column in a CSV file.

    Args:
        csv_file_path: Path to the input CSV file.
        text_column_name: The name of the column containing text data.
        top_n: The number of top keywords to return.
        custom_stop_words: Optional list of custom stop words. If None, uses default English list.

    Returns:
        A list of the most frequent words (keywords), or an empty list if errors occur.
    """
    if not await aios.path.exists(csv_file_path): # Corrected here
        # print(f"Error: CSV file not found at {csv_file_path}")
        return []

    stop_words_to_use = custom_stop_words if custom_stop_words is not None else DEFAULT_ENGLISH_STOP_WORDS
    all_tokens = []

    try:
        async with aiofiles.open(csv_file_path, mode='r', encoding='utf-8', newline='') as afp:
            content = await afp.read()
            # The csv module expects an iterator over lines for its reader.
            # We can achieve this by splitting the content by lines.
            csv_reader = csv.DictReader(content.splitlines())

            if text_column_name not in csv_reader.fieldnames:
                # print(f"Error: Column '{text_column_name}' not found in CSV headers: {csv_reader.fieldnames}")
                return []

            for row in csv_reader:
                text = row.get(text_column_name, "")
                cleaned_text = await _clean_text(text)
                tokens = await _tokenize_text(cleaned_text)
                tokens_without_stopwords = await _remove_stopwords(tokens, stop_words_to_use)
                all_tokens.extend(tokens_without_stopwords)

    except Exception as e:
        # print(f"Error processing CSV file: {e}")
        return []

    if not all_tokens:
        return []

    word_counts = Counter(all_tokens)
    most_common_words = [word for word, count in word_counts.most_common(top_n)]

    return most_common_words


if __name__ == '__main__':
    async def main():
        print("Testing CSV Keyword Generation:")
        dummy_csv_path = "test_keywords.csv"
        dummy_data = [
            {"id": "1", "title": "Introduction to Machine Learning", "content": "Machine learning is a field of computer science. This learning process is great."},
            {"id": "2", "title": "Advanced Python Programming", "content": "Python is a versatile programming language. Python programming involves many concepts."},
            {"id": "3", "title": "Data Science Basics", "content": "Data science combines statistics, data analysis, and machine learning. It's a growing field."},
            {"id": "4", "title": "Web Development with Python", "content": "Developing web applications using Python and frameworks like Django or Flask."}
        ]

        # Create dummy CSV
        try:
            async with aiofiles.open(dummy_csv_path, mode='w', encoding='utf-8', newline='') as afp:
                fieldnames = ["id", "title", "content"]

                # Write header manually - THIS IS THE ONLY HEADER WRITE NOW
                await afp.write(",".join(fieldnames) + "\n")

                # Write data rows
                for row_data in dummy_data:
                    # Using .get() for robustness, though dummy_data is complete.
                    await afp.write(",".join([f'"{row_data.get(fn, "")}"' for fn in fieldnames]) + "\n")

            print(f"\nCreated dummy CSV: {dummy_csv_path}")

            # Test 1: Extract from 'content' column
            print("\n--- Test 1: Keywords from 'content' column ---")
            keywords_content = await generate_keywords_from_csv_column_async(dummy_csv_path, "content", top_n=5)
            print(f"Keywords from 'content': {keywords_content}")
            # Expected: ['python', 'machine', 'learning', 'data', 'science'] or similar based on exact processing

            # Test 2: Extract from 'title' column
            print("\n--- Test 2: Keywords from 'title' column ---")
            keywords_title = await generate_keywords_from_csv_column_async(dummy_csv_path, "title", top_n=3)
            print(f"Keywords from 'title': {keywords_title}")
            # Expected: ['python', 'machine', 'learning'] or ['python', 'data', 'science']

            # Test 3: Non-existent column
            print("\n--- Test 3: Non-existent column ---")
            keywords_non_existent_col = await generate_keywords_from_csv_column_async(dummy_csv_path, "summary", top_n=5)
            print(f"Keywords from 'summary' (non-existent): {keywords_non_existent_col}") # Expected: []

            # Test 4: Non-existent CSV file
            print("\n--- Test 4: Non-existent CSV file ---")
            keywords_non_existent_file = await generate_keywords_from_csv_column_async("no_such_file.csv", "content", top_n=5)
            print(f"Keywords from non-existent file: {keywords_non_existent_file}") # Expected: []

            # Test 5: Custom stop words
            print("\n--- Test 5: Custom stop words (removing 'python') ---")
            custom_stops = DEFAULT_ENGLISH_STOP_WORDS + ["python", "machine"]
            keywords_custom_stops = await generate_keywords_from_csv_column_async(dummy_csv_path, "content", top_n=5, custom_stop_words=custom_stops)
            print(f"Keywords from 'content' with custom stop words: {keywords_custom_stops}")
            # Expected: ['learning', 'data', 'science', 'field', 'programming'] (or similar, without python, machine)

        except Exception as e:
            print(f"An error occurred in main test execution: {e}")
        finally:
            # Clean up dummy CSV
            if await aios.path.exists(dummy_csv_path): # Corrected here
                await aios.remove(dummy_csv_path)      # Corrected here
                print(f"\nRemoved dummy CSV: {dummy_csv_path}")

    asyncio.run(main())
