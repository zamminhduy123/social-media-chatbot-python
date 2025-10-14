import json
from google import genai

FAQ_PATH = '/Users/rzy/Desktop/ChatBot/facebook-chatbot/testAS/testas_data_en.json'

def load_data(path):
    # 1. Load your scraped data
    with open(path, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} documents from the website.")
    return data

def text_splitting(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
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

# Test Gemini integration
# if __name__ == "__main__":
    
#     ADD_DATA = False
#     API_KEY = os.getenv("GEMINI_API_KEY")
#     client = genai.Client(api_key=API_KEY)
#     model_name = 'models/text-embedding-004'
#     batch_size = 100
#     all_embeddings = []

#     if (ADD_DATA):
#         data = load_data(FAQ_PATH)
#         all_chunks = text_chunking(data)
#         # Example: Print the first chunk to see the result
#         if all_chunks:
#             print("\n--- Example Chunk ---")
#             print(f"Source: {all_chunks[0]['source_url']}")
#             print(f"Title: {all_chunks[0]['title']}")
#             print(f"Content: '{all_chunks[0]['content'][:200]}...'") # Print first 200 chars
        
        
#         # We'll get the content from our chunks
#         chunk_contents = [chunk['content'] for chunk in all_chunks]
#         print(f"\nTotal chunks to embed: {len(chunk_contents)}")

#         print("\nCreating embeddings for all chunks...")
#         # Process the chunks in batches to respect API limits
#         for i in range(0, len(chunk_contents), batch_size):
#             batch = chunk_contents[i:i + batch_size]
#             try:
#                 # Call the Gemini API
#                 result = client.models.embed_content(
#                     model=model_name,
#                     contents=batch,
#                 )
#                 embeddings = [emb.values for emb in result.embeddings]

#                 all_embeddings.extend(embeddings)
#                 print(f"  - Embedded batch {i//batch_size + 1}/{(len(chunk_contents) + batch_size - 1)//batch_size}")
#             except Exception as e:
#                 print(f"An error occurred during embedding batch {i//batch_size + 1}: {e}")
#                 # Optional: Add retry logic here

#     # 5. Store embeddings in a vector database
#     # 5.1. Setup a ChromaDB client (it can store data in memory or on disk)
#     client_db = chromadb.PersistentClient(path="/Users/rzy/Desktop/ChatBot/facebook-chatbot/db")

#     # 5.2. Create a "collection" which is like a table in a SQL database
#     collection = client_db.get_or_create_collection(
#         name="testas_docs"
#     )

#     # 5.3. Add your documents to the collection
#     # We need to add the embeddings, the text content itself, and the metadata.
#     if (ADD_DATA):
#         print(f"Adding {len(all_embeddings)}, {len(all_chunks)} embeddings to the collection.")
#         collection.add(
#             embeddings=all_embeddings,
#             documents=[chunk['content'] for chunk in all_chunks],
#             metadatas=[{'source': chunk['source_url'], 'title': chunk['title']} for chunk in all_chunks],
#             ids=[chunk['chunk_id'] for chunk in all_chunks] # Each item needs a unique ID
#         )

#     print(f"\nIndexed {collection.count()} chunks in ChromaDB.")

#     # The user's question
#     query = "What is the structure of the digital TestAS exam?"

#     # 1. Embed the query
#     query_embedding = client.models.embed_content(
#         model=model_name,
#         contents=[query],
#     ).embeddings[0].values

#     # 2. Query the collection to get the 3 most relevant chunks
#     results = collection.query(
#         query_embeddings=query_embedding, # Query takes a list of embeddings
#         n_results=3
#     )

#     # 3. Prepare the context for the LLM
#     context = "\n---\n".join(results['documents'][0])
#     metadata = results['metadatas'][0]

#     prompt_for_llm = f"""
#     Based on the following context, please answer the user's question.
#     If the context does not contain the answer, say that you don't know.

#     Context:
#     {context}

#     Question: {query}

#     Answer:
#     """

#     print("\n--- Prompt for LLM ---")
#     print(prompt_for_llm)
#     print(results['documents'][0])