import logging
import json
import aiohttp
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class GeminiAPI:
    """
    Wrapper for Google's Gemini API to provide embedding generation and other ML services
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.embedding_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent"
        self.embedding_dimension = 768  # Default dimension for embeddings
        
        if not self.api_key:
            logger.warning("Gemini API key not provided. Embedding generation will not be available.")
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using Gemini embedding model
        """
        if not self.api_key:
            logger.warning("Cannot generate embedding: No API key provided")
            return None
        
        try:
            # Truncate text if too long (API limit is 3072 tokens)
            # This is a simple character-based truncation - in production you might 
            # want to use a proper tokenizer to ensure you don't exceed token limits
            text = text[:8000]  # Rough approximation for safety
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "embedding-001",
                "content": {
                    "parts": [
                        {"text": text}
                    ]
                }
            }
            
            url = f"{self.embedding_endpoint}?key={self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error generating embedding: {error_text}")
                        return None
                    
                    result = await response.json()
                    embeddings = result.get("embedding", {}).get("values", [])
                    
                    if not embeddings:
                        logger.warning("Embedding generation returned empty result")
                        return None
                    
                    return embeddings
        
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None
    
    async def similarity_score(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        # Ensure embeddings are of same length
        if len(embedding1) != len(embedding2):
            logger.warning("Embeddings have different dimensions")
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Cosine similarity
        return dot_product / (magnitude1 * magnitude2)
    
    async def search_similar_texts(self, query_text: str, texts_with_embeddings: List[Dict[str, Any]], 
                                  top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar texts based on embedding similarity
        
        Args:
            query_text (str): The query text to search for
            texts_with_embeddings (List[Dict]): List of dicts, each containing at least 
                                               'text' and 'embedding' keys
            top_k (int): Number of most similar results to return
            
        Returns:
            List of dicts with the most similar texts, including similarity scores
        """
        # Generate embedding for query text
        query_embedding = await self.generate_embedding(query_text)
        
        if not query_embedding:
            logger.warning("Could not generate query embedding")
            return []
        
        results = []
        
        # Calculate similarity for each text
        for item in texts_with_embeddings:
            embedding = item.get("embedding")
            
            # Skip items without embeddings
            if not embedding:
                continue
            
            # Convert string representation to list if needed
            if isinstance(embedding, str):
                try:
                    embedding = json.loads(embedding)
                except:
                    logger.warning(f"Could not parse embedding: {embedding}")
                    continue
            
            # Calculate similarity
            similarity = await self.similarity_score(query_embedding, embedding)
            
            # Add to results
            results.append({
                "text": item.get("text", ""),
                "title": item.get("title", ""),
                "metadata": item.get("metadata", {}),
                "similarity": similarity
            })
        
        # Sort by similarity (highest first) and take top_k
        sorted_results = sorted(results, key=lambda x: x["similarity"], reverse=True)
        return sorted_results[:top_k] 