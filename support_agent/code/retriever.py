import json
import os
import pickle
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    USE_FAISS = True
except ImportError:
    USE_FAISS = False
    print("FAISS or SentenceTransformers not found. Falling back to keyword search.")

class Retriever:
    def __init__(self, corpus_path=None, index_path=None, fast_mode=False):
        base_dir = os.path.dirname(__file__)
        if corpus_path is None:
            corpus_path = os.path.join(base_dir, "..", "data", "corpus", "corpus.json")
        if index_path is None:
            index_path = os.path.join(base_dir, "..", "data", "corpus", "faiss_index.pkl")
        
        self.corpus_path = os.path.abspath(corpus_path)
        self.index_path = os.path.abspath(index_path)
        self.corpus = []
        self.model = None
        self.index = None
        self.fast_mode = fast_mode
        self.load_corpus()
        
        if USE_FAISS and not self.fast_mode:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.build_index()

    def load_corpus(self):
        if os.path.exists(self.corpus_path):
            with open(self.corpus_path, 'r', encoding='utf-8') as f:
                self.corpus = json.load(f)
        else:
            print(f"Warning: Corpus file not found at {self.corpus_path}")

    def build_index(self):
        if not self.corpus:
            return

        if os.path.exists(self.index_path):
            with open(self.index_path, 'rb') as f:
                self.index_data = pickle.load(f)
                self.index = self.index_data['index']
                return

        print("Building FAISS index...")
        # Combine title and content for embedding
        texts = [f"{doc['title']} {doc['content']}" for doc in self.corpus]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Normalize for cosine similarity (Inner Product on normalized vectors)
        embeddings = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings)
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        
        with open(self.index_path, 'wb') as f:
            pickle.dump({'index': self.index}, f)
        print("Index built and cached.")

    def search(self, query, source_filter=None, top_k=5):
        if not self.corpus:
            return []

        # Filter corpus by source first if needed
        filtered_indices = range(len(self.corpus))
        if source_filter:
            source_filter = source_filter.lower()
            filtered_indices = [i for i, doc in enumerate(self.corpus) if doc['source'].lower() == source_filter]

        if not filtered_indices:
            return []

        if USE_FAISS and self.index:
            query_embedding = self.model.encode([query]).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Since we have a source filter, we might need to search the whole index and then filter,
            # or build separate indices. For simplicity, we'll search the whole and filter.
            # However, for a hackathon, let's just search the whole and filter the results.
            # If the top results aren't in the filter, we'll keep looking.
            
            D, I = self.index.search(query_embedding, len(self.corpus))
            
            results = []
            for idx in I[0]:
                if idx in filtered_indices:
                    results.append(self.corpus[idx])
                if len(results) >= top_k:
                    break
            return results
        else:
            # Fallback keyword search (simple word overlap / TF-IDF style)
            print("Using keyword fallback search...")
            query_words = set(query.lower().split())
            scores = []
            for i in filtered_indices:
                doc = self.corpus[i]
                doc_text = (doc['title'] + " " + doc['content']).lower()
                score = sum(1 for word in query_words if word in doc_text)
                scores.append((score, doc))
            
            scores.sort(key=lambda x: x[0], reverse=True)
            return [doc for score, doc in scores[:top_k]]

if __name__ == "__main__":
    # Test
    retriever = Retriever()
    if retriever.corpus:
        results = retriever.search("reset password", source_filter="claude")
        for res in results:
            print(f"- {res['title']} ({res['source']})")
