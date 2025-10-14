from sentence_transformers import SentenceTransformer

# Assuming you have a ContextRepository class defined elsewhere, for example:
# from repository.ContextRepository import ContextRepository

class ContextController:
    """
    Manages context-related operations using a sentence transformer model
    and a context repository.
    """

    def __init__(self, context_repository):
        """
        Initializes the ContextController.

        Args:
            context_repository: An object for accessing and storing context data.
        """
        # Load a pre-trained sentence transformer model.
        # 'all-MiniLM-L6-v2' is a popular and efficient model.
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.context_repository = context_repository

    def get_model(self):
        """
        Returns the sentence transformer model instance.
        """
        return self.model

    def get_repository(self):
        """
        Returns the context repository instance.
        """
        return self.context_repository
    
    def query_relavant(self, message: str, n_results: int = 3) -> list[str]:
        """
        Queries the context repository for documents similar to the query text.

        Args:
            query_text (str): The text to query against the stored contexts.
            n_results (int): The number of similar documents to retrieve.
        Returns:
            list[str]: A list of similar context strings.
        """

        query_text = self.model.encode([message])[0]
        return self.context_repository.query_similarity(query_text, n_results)

# Example Usage (optional, for demonstration)
if __name__ == '__main__':
    # This is a mock repository for demonstration purposes.
    # In a real application, this would interact with a database or file system.
    class MockContextRepository:
        def __init__(self):
            self._contexts = {
                "greeting": "Hello! How can I help you today?",
                "goodbye": "Goodbye! Have a great day.",
                "hours": "We are open from 9 AM to 5 PM, Monday to Friday."
            }

        def get_all_contexts(self):
            return self._contexts

    # 1. Instantiate the repository
    repo = MockContextRepository()

    # 2. Instantiate the controller with the repository
    context_controller = ContextController(context_repository=repo)

    # 3. Access the model and repository
    model = context_controller.get_model()
    repository = context_controller.get_repository()

    print("Sentence Transformer Model Loaded:", model is not None)
    print("Context Repository Loaded:", repository is not None)

    # Example of encoding a sentence
    sentence = "What are your opening times?"
    embedding = model.encode(sentence)
    print(f"\nEncoded '{sentence}'")
    print("Embedding shape:", embedding.shape)
