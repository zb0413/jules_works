import asyncio

async def extract_keywords_from_filename_async(filename: str, keywords: list[str]) -> list[str]:
    """
    Extracts keywords from a filename based on a predefined list, case-insensitively.

    Args:
        filename: The filename string to search within.
        keywords: A list of predefined keywords to look for.

    Returns:
        A list of matched keywords found in the filename.
        Returns an empty list if no keywords are found or inputs are invalid.
    """
    if not filename or not keywords:
        return []

    # Normalize filename to lowercase for case-insensitive matching
    lower_filename = filename.lower()

    found_keywords = []
    for keyword in keywords:
        if not keyword: # Skip empty keywords in the list
            continue
        if keyword.lower() in lower_filename:
            # Return the original keyword casing from the list, not the lowercased version
            found_keywords.append(keyword)

    return found_keywords

if __name__ == '__main__':
    async def main():
        print("Testing keyword extraction from filenames:")

        predefined_keywords = ["Report", "Monthly", "Urgent", "Draft", "Final", "ProjectX"]

        # Test case 1: Filename with multiple keywords, mixed casing
        filename1 = "Monthly_Report_ProjectX_final_version.docx"
        extracted1 = await extract_keywords_from_filename_async(filename1, predefined_keywords)
        print(f"\nFilename: '{filename1}'")
        print(f"Predefined Keywords: {predefined_keywords}")
        print(f"Extracted: {extracted1}") # Expected: ['Report', 'Monthly', 'Final', 'ProjectX']

        # Test case 2: Filename with some keywords
        filename2 = "urgent_draft_proposal.pdf"
        extracted2 = await extract_keywords_from_filename_async(filename2, predefined_keywords)
        print(f"\nFilename: '{filename2}'")
        print(f"Extracted: {extracted2}") # Expected: ['Urgent', 'Draft']

        # Test case 3: Filename with no matching keywords
        filename3 = "annual_summary_2023.xlsx"
        extracted3 = await extract_keywords_from_filename_async(filename3, predefined_keywords)
        print(f"\nFilename: '{filename3}'")
        print(f"Extracted: {extracted3}") # Expected: []

        # Test case 4: Empty filename
        filename4 = ""
        extracted4 = await extract_keywords_from_filename_async(filename4, predefined_keywords)
        print(f"\nFilename: '{filename4}'")
        print(f"Extracted: {extracted4}") # Expected: []

        # Test case 5: Empty keyword list
        filename5 = "some_document_name.txt"
        extracted5 = await extract_keywords_from_filename_async(filename5, [])
        print(f"\nFilename: '{filename5}' (Empty keyword list)")
        print(f"Extracted: {extracted5}") # Expected: []

        # Test case 6: Keyword list with empty string
        filename6 = "Report_for_review.doc"
        keywords_with_empty = ["Report", "", "Review"]
        extracted6 = await extract_keywords_from_filename_async(filename6, keywords_with_empty)
        print(f"\nFilename: '{filename6}' (Keywords with empty string: {keywords_with_empty})")
        print(f"Extracted: {extracted6}") # Expected: ['Report'] (should ignore empty keyword and not match "Review")


    asyncio.run(main())
