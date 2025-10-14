import os
import chromadb
from google import genai

class ContextController:
    """
    Manages the connection to ChromaDB and handles similarity queries
    to retrieve relevant context for the chatbot.
    """
    batch_size = 100

    def __init__(self, path: str = "chroma_db", collection_name: str = "facebook_posts"):
        """
        Initializes the ChromaDB client and gets or creates a collection.

        Args:
            path (str): The path to the directory where ChromaDB data will be stored.
            collection_name (str): The name of the collection to use.
        """
        API_KEY = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=API_KEY)
        self.model_name = 'models/text-embedding-004'
        try:
            # Using a persistent client to store data on disk
            self.client_DB = chromadb.PersistentClient(path=path)

            self.collection = self.client_DB.get_or_create_collection(name=collection_name)

            print(f"Successfully connected to ChromaDB and loaded collection '{collection_name}'.")

        except Exception as e:
            print(f"Error initializing ContextController: {e}")
            self.client = None
            self.collection = None  

    def add_documents(self, documents: list[str], metadatas: list[dict] = None, ids: list[str] = None):
        """
        Adds documents to the ChromaDB collection.

        Args:
            documents (list[str]): A list of document texts to add.
            metadatas (list[dict], optional): A list of metadata dictionaries corresponding to the documents.
            ids (list[str], optional): A list of unique IDs for the documents. If not provided, they will be generated.
        """
        if not self.collection:
            print("Collection is not available. Cannot add documents.")
            return

        if not ids:
            # Generate simple sequential IDs if none are provided
            start_id = self.collection.count()
            ids = [str(i) for i in range(start_id, start_id + len(documents))]

        all_embeddings = []
        chunk_contents = documents
    
        # Process the chunks in batches to respect API limits
        for i in range(0, len(chunk_contents), self.batch_size):
            batch = chunk_contents[i:i + self.batch_size]
            try:
                # Call the Gemini API
                result = self.client.models.embed_content(
                    model=self.model_name,
                    contents=batch,
                )
                embeddings = [emb.values for emb in result.embeddings]

                all_embeddings.extend(embeddings)
                print(f"  - Embedded batch {i//self.batch_size + 1}/{(len(chunk_contents) + self.batch_size - 1)//self.batch_size}")
            except Exception as e:
                print(f"An error occurred during embedding batch {i//self.batch_size + 1}: {e}")
                
        try:
            self.collection.add(
                documents=documents,
                embeddings=all_embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Successfully added {len(documents)} documents to the collection.")
        except Exception as e:
            print(f"Error adding documents: {e}")

    def query_similarity(self, query_text: str, n_results: int = 3) -> list[str]:
        """
        Queries the collection for documents similar to the query text.

        Args:
            query_text (str): The text to find similar documents for.
            n_results (int): The number of similar documents to return.

        Returns:
            list[str]: A list of the most similar document texts.
                       Returns an empty list if an error occurs or no results are found.
        """
        if not self.collection:
            print("Collection is not available. Cannot perform query.")
            return []

        # 1. Embed the query
        query_embedding = self.client.models.embed_content(
            model=self.model_name,
            contents=[query_text],
        ).embeddings[0].values
        print(f"Query embedding: {query_embedding[:5]}... (truncated)")

        try:
            results = self.collection.query(
                query_embeddings=query_embedding, # Query takes a list of embeddings
                n_results=3
            )
            # The result is a dictionary, we are interested in the 'documents' for the first query
            return results.get('documents', [[]])[0]
        except Exception as e:
            print(f"Error during similarity query: {e}")
            return []

    def get_collection_count(self) -> int:
        """
        Returns the total number of items in the collection.
        """
        if not self.collection:
            return 0
        return self.collection.count()

# Example usage:
# if __name__ == '__main__':
#     # 1. Initialize the controller
#     context_controller = ContextController(path="chroma_db", collection_name="facebook_posts")

#     # 2. Add some documents if the collection is empty
#     if context_controller.get_collection_count() == 0:
#         print("Collection is empty. Adding sample documents.")
#         sample_docs = [
#             "Our business hours are Monday to Friday, 9 AM to 5 PM.",
#             "You can reset your password by clicking the 'Forgot Password' link on the login page.",
#             "We offer shipping to the United States and Canada.",
#             "Our return policy allows returns within 30 days of purchase.",
#             "To contact customer support, please email support@example.com."
#         ]
#         sample_metadatas = [
#             {'topic': 'hours'},
#             {'topic': 'account'},
#             {'topic': 'shipping'},
#             {'topic': 'returns'},
#             {'topic': 'support'}
#         ]
#         context_controller.add_documents(documents=sample_docs, metadatas=sample_metadatas)

#     # 3. Perform a similarity search
#     user_query = "What are your opening times?"
#     print(f"\nQuerying for: '{user_query}'")
#     similar_contexts = context_controller.query_similarity(user_query, n_results=2)

#     # 4. Print the results
#     if similar_contexts:
#         print("Found similar contexts:")
#         for i, context in enumerate(similar_contexts):
#             print(f"{i+1}: {context}")
#     else:
#         print("No similar contexts found.")

#     user_query_2 = "How can I change my password?"
#     print(f"\nQuerying for: '{user_query_2}'")
#     similar_contexts_2 = context_controller.query_similarity(user_query_2, n_results=1)
#     if similar_contexts_2:
#         print("Found similar contexts:")
#         for i, context in enumerate(similar_contexts_2):
#             print(f"{i+1}: {context}")
#     else:
#         print("No similar contexts found.")