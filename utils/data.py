def text_splitting(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits a text into overlapping chunks.

    Args:
        text: The input text to be split.
        chunk_size: The maximum size of each chunk (in characters).
        chunk_overlap: The number of characters to overlap between chunks.

    Returns:
        A list of text chunks.
    """
    if not isinstance(text, str):
        return []

    # 1. First, split the text by paragraphs
    paragraphs = text.split('\n\n')
    all_chunks = []
    
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            # If the paragraph is small enough, add it as a single chunk
            if paragraph.strip(): # Ensure we don't add empty strings
                all_chunks.append(paragraph.strip())
        else:
            # If the paragraph is too long, split it with a sliding window
            start_index = 0
            while start_index < len(paragraph):
                end_index = start_index + chunk_size
                chunk = paragraph[start_index:end_index]
                all_chunks.append(chunk.strip())
                
                # Move the start index for the next chunk
                start_index += (chunk_size - chunk_overlap)
                
    return all_chunks   

def text_chunking(data):
    all_chunks = []

    # 3. Process each document and create chunks
    for doc in data:
        # We only process docs that have meaningful content
        if 'body' in doc and doc['body']:
            # Split the document's body text
            chunks = text_splitting(doc['body'])

            # Add metadata to each chunk
            for i, chunk_text in enumerate(chunks):
                all_chunks.append({
                    'source_url': doc['url'],
                    'title': doc['title'],
                    'content': chunk_text,
                    'chunk_id': f"{doc['url']}-{i}" # A unique ID for each chunk
                })

    print(f"Created {len(all_chunks)} chunks from {len(data)} documents.")
    return all_chunks
