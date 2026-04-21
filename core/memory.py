import os
import vecs
import logging
from vecs.adapter import Adapter, ParagraphChunker, TextEmbedding

class MemoryManager:
    def __init__(self):
        self.db_url = os.getenv("SUPABASE_DB_URL")
        self.vx = None
        self.collection = None
        
        if not self.db_url:
            logging.warning("SUPABASE_DB_URL not found. Memory will be disabled.")
            return

        # Clean the URL of any accidental internal spaces or newlines
        self.db_url = "".join(self.db_url.split())

    def get_collection(self):
        """Lazily initializes and returns the Supabase collection."""
        if self.collection is not None:
            return self.collection
        
        if not self.db_url:
            return None

        try:
            logging.info("Connecting to Supabase vector store...")
            # Create vector store client
            self.vx = vecs.create_client(self.db_url)
            
            # Create a collection with a text adapter for automatic embedding
            self.collection = self.vx.get_or_create_collection(
                name="user_facts",
                adapter=Adapter(
                    [
                        ParagraphChunker(skip_during_query=True),
                        TextEmbedding(model='all-MiniLM-L6-v2'),
                    ]
                )
            )
            logging.info("Successfully connected to Supabase vector store.")
            return self.collection
        except Exception as e:
            logging.error(f"Lazy connection to Supabase failed: {e}")
            self.collection = None
            return None

    def add_memory(self, text, metadata=None):
        """Saves a fact to the Supabase vector database."""
        collection = self.get_collection()
        if not collection:
            return

        try:
            import uuid
            memory_id = str(uuid.uuid4())
            collection.upsert(
                records=[
                    (memory_id, text, metadata or {})
                ]
            )
            logging.info(f"Memory added to Supabase: {text}")
        except Exception as e:
            logging.error(f"Error adding memory: {e}")

    def search_memories(self, query_text, n_results=3):
        """Retrieves relevant facts from the Supabase vector database."""
        collection = self.get_collection()
        if not collection:
            logging.warning("Search skipped: Supabase collection not available.")
            return []

        try:
            results = collection.query(
                data=query_text,
                limit=n_results,
                include_value=False,
                include_metadata=False
            )
            return results
        except Exception as e:
            logging.error(f"Error searching memories: {e}")
            return []

    def __del__(self):
        if hasattr(self, 'vx') and self.vx:
            try:
                self.vx.disconnect()
            except Exception:
                pass
