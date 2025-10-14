import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

FAQ_PATH = '/Users/rzy/Desktop/ChatBot/facebook-chatbot/testAS/testas_data_en.json'

def load_data(path):
    # 1. Load your scraped data
    with open(path, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} documents from the website.")
    return data


# 2. Preprocess the data (if necessary)
# For simplicity, we'll assume the data is already clean and structured.
# 2. Initialize the Text Splitter
# chunk_size: The maximum size of each chunk (in characters).
# chunk_overlap: How many characters to overlap between chunks. This helps
#                maintain context between chunks.
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)

def text_chunking(data):
    all_chunks = []

    # 3. Process each document and create chunks
    for doc in data:
        # We only process docs that have meaningful content
        if 'body' in doc and doc['body']:
            # Split the document's body text
            chunks = text_splitter.split_text(doc['body'])

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
if __name__ == "__main__":
    
    ADD_DATA = True

    if (ADD_DATA):
        data = load_data(FAQ_PATH)
        all_chunks = text_chunking(data)
        # Example: Print the first chunk to see the result
        if all_chunks:
            print("\n--- Example Chunk ---")
            print(f"Source: {all_chunks[0]['source_url']}")
            print(f"Title: {all_chunks[0]['title']}")
            print(f"Content: '{all_chunks[0]['content'][:200]}...'") # Print first 200 chars
        
        
        # Load a pre-trained model. 'all-MiniLM-L6-v2' is a great, fast starting model.
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # We'll get the content from our chunks
        chunk_contents = [chunk['content'] for chunk in all_chunks]

        print("\nCreating embeddings for all chunks...")
        # This will take a moment depending on the number of chunks and your hardware.
        embeddings = model.encode(chunk_contents, show_progress_bar=True)

        print(f"Created {len(embeddings)} embeddings, each with a dimension of {embeddings.shape[1]}.")

    # 5. Store embeddings in a vector database
    # 5.1. Setup a ChromaDB client (it can store data in memory or on disk)
    client = chromadb.PersistentClient(path="/Users/rzy/Desktop/ChatBot/facebook-chatbot/db")

    # 5.2. Create a "collection" which is like a table in a SQL database
    collection = client.get_or_create_collection(name="testas_docs")

    # 5.3. Add your documents to the collection
    # We need to add the embeddings, the text content itself, and the metadata.
    if (ADD_DATA):
        collection.add(
            embeddings=embeddings,
            documents=[chunk['content'] for chunk in all_chunks],
            metadatas=[{'source': chunk['source_url'], 'title': chunk['title']} for chunk in all_chunks],
            ids=[chunk['chunk_id'] for chunk in all_chunks] # Each item needs a unique ID
        )

    print(f"\nIndexed {collection.count()} chunks in ChromaDB.")

    # The user's question
    query = "What is the structure of the digital TestAS exam?"

    # 1. Embed the query
    query_embedding = model.encode([query])[0] # Note: encode expects a list

    # 2. Query the collection to get the 3 most relevant chunks
    results = collection.query(
        query_embeddings=[query_embedding.tolist()], # Query takes a list of embeddings
        n_results=3
    )

    # 3. Prepare the context for the LLM
    context = "\n---\n".join(results['documents'][0])
    metadata = results['metadatas'][0]

    prompt_for_llm = f"""
    Based on the following context, please answer the user's question.
    If the context does not contain the answer, say that you don't know.

    Context:
    {context}

    Question: {query}

    Answer:
    """

    print("\n--- Prompt for LLM ---")
    print(prompt_for_llm)