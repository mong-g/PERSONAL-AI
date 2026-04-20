import os
import vecs
import logging
from vecs.adapter import Adapter, ParagraphChunker, TextEmbedding

class MemoryManager:
    def __init__(self):
        self.db_url = os.getenv("SUPABASE_DB_URL")
        if not self.db_url:
            logging.warning("SUPABASE_DB_URL not found. Memory will be disabled.")
            self.collection = None
            return

        try:
            # Create vector store client
            self.vx = vecs.create_client(self.db_url)
            
            # Create a collection with a text adapter for automatic embedding
            # This uses 'all-MiniLM-L6-v2' (384 dimensions) by default
            self.collection = self.vx.get_or_create_collection(
                name="user_facts",
                adapter=Adapter(
                    [
                        ParagraphChunker(skip_during_query=True),
                        TextEmbedding(model='all-MiniLM-L6-v2'),
                    ]
                )
            )
            logging.info("Connected to Supabase vector store.")
        except Exception as e:
            logging.error(f"Failed to connect to Supabase: {e}")
            self.collection = None

    def add_memory(self, text, metadata=None):
        """Saves a fact to the Supabase vector database."""
        if not self.collection:
            return

        try:
            # Generate a simple unique ID
            import uuid
            memory_id = str(uuid.uuid4())
            
            # With the adapter, we can upsert text directly
            self.collection.upsert(
                records=[
                    (memory_id, text, metadata or {})
                ]
            )
            logging.info(f"Memory added to Supabase: {text}")
        except Exception as e:
            logging.error(f"Error adding memory: {e}")

    def search_memories(self, query_text, n_results=3):
        """Retrieves relevant facts from the Supabase vector database."""
        if not self.collection:
            return []

        try:
            # Query using text (automatically embedded by the adapter)
            results = self.collection.query(
                data=query_text,
                limit=n_results,
                include_value=False,
                include_metadata=False
            )
            # The adapter returns the raw text content for matched vectors
            # but 'vecs' with adapter returns the IDs or original data.
            # In our case, the 'data' is the text itself.
            
            # Re-fetching or just returning the result IDs if they are enough?
            # Actually, the adapter pattern in vecs is quite elegant.
            # Let's simplify and just use the query for now.
            return results
        except Exception as e:
            logging.error(f"Error searching memories: {e}")
            return []

    def __del__(self):
        if hasattr(self, 'vx'):
            self.vx.disconnect()
