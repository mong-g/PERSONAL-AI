import chromadb
from chromadb.utils import embedding_functions

class MemoryManager:
    def __init__(self, db_path="./lucio_memory"):
        self.client = chromadb.PersistentClient(path=db_path)
        # Using default embedding function (all-MiniLM-L6-v2)
        self.collection = self.client.get_or_create_collection(
            name="user_facts",
            metadata={"hnsw:space": "cosine"}
        )

    def add_memory(self, text, metadata=None):
        """Saves a fact to the vector database."""
        # Generating a simple ID based on count for now
        count = self.collection.count()
        self.collection.add(
            documents=[text],
            metadatas=[metadata] if metadata else [{}],
            ids=[f"id_{count}"]
        )
        print(f"Memory added: {text}")

    def search_memories(self, query_text, n_results=3):
        """Retrieves relevant facts from the vector database."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results['documents'][0] if results['documents'] else []

if __name__ == "__main__":
    # Quick test
    memory = MemoryManager()
    memory.add_memory("The user's favorite color is blue.")
    print(memory.search_memories("What is the user's favorite color?"))
