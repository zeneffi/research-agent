"""
Semantic Filter - Embedding-based relevance filtering.

Uses sentence transformers to compute semantic similarity between
queries and results for intelligent relevance ranking.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


@dataclass
class ScoredFinding:
    """A finding with semantic relevance score."""
    source: str
    title: str
    summary: str
    keywords: list
    keyword_relevance: float
    semantic_relevance: float
    combined_score: float


class SemanticFilter:
    """
    Embedding-based semantic relevance filter.
    
    Uses sentence transformers to compute cosine similarity
    between the query and findings.
    """
    
    # Default model (small, fast, good quality)
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        relevance_threshold: float = 0.3,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
    ):
        """
        Initialize semantic filter.
        
        Args:
            model_name: Sentence transformer model name
            relevance_threshold: Minimum combined score to keep finding
            keyword_weight: Weight for keyword-based relevance (0-1)
            semantic_weight: Weight for semantic relevance (0-1)
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.relevance_threshold = relevance_threshold
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        
        self._model: Optional[SentenceTransformer] = None
        self._available = SENTENCE_TRANSFORMERS_AVAILABLE and NUMPY_AVAILABLE
    
    @property
    def available(self) -> bool:
        """Check if semantic filtering is available."""
        return self._available
    
    def _load_model(self) -> SentenceTransformer:
        """Lazily load the sentence transformer model."""
        if not self._available:
            raise ImportError(
                "sentence-transformers and numpy are required for semantic filtering. "
                "Install with: pip install sentence-transformers numpy"
            )
        
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        
        return self._model
    
    def _compute_cosine_similarity(
        self,
        embedding1: "np.ndarray",
        embedding2: "np.ndarray",
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def filter_findings(
        self,
        query: str,
        findings: list[dict],
        top_k: Optional[int] = None,
    ) -> list[ScoredFinding]:
        """
        Filter and rank findings by semantic relevance.
        
        Args:
            query: Original research query
            findings: List of finding dictionaries
            top_k: Maximum number of results to return
            
        Returns:
            List of ScoredFinding objects, sorted by combined score
        """
        if not findings:
            return []
        
        if not self._available:
            # Fallback to keyword-only ranking
            return self._keyword_only_ranking(findings, top_k)
        
        # Run embedding computation in thread pool
        loop = asyncio.get_event_loop()
        scored = await loop.run_in_executor(
            None,
            self._compute_scores_sync,
            query,
            findings,
        )
        
        # Filter by threshold
        filtered = [f for f in scored if f.combined_score >= self.relevance_threshold]
        
        # Sort by combined score
        filtered.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Limit to top_k
        if top_k:
            filtered = filtered[:top_k]
        
        return filtered
    
    def _compute_scores_sync(
        self,
        query: str,
        findings: list[dict],
    ) -> list[ScoredFinding]:
        """Compute semantic scores synchronously."""
        model = self._load_model()
        
        # Compute query embedding
        query_embedding = model.encode(query, convert_to_numpy=True)
        
        # Prepare texts for batch encoding
        texts = []
        for finding in findings:
            # Combine title and summary for richer embedding
            text = f"{finding.get('title', '')} {finding.get('summary', '')}"
            texts.append(text)
        
        # Batch encode findings
        finding_embeddings = model.encode(texts, convert_to_numpy=True)
        
        scored_findings = []
        for i, finding in enumerate(findings):
            # Compute semantic similarity
            semantic_score = self._compute_cosine_similarity(
                query_embedding,
                finding_embeddings[i],
            )
            
            # Normalize to 0-1 range (cosine similarity is -1 to 1)
            semantic_score = (semantic_score + 1) / 2
            
            # Get keyword relevance from finding
            keyword_score = finding.get("relevance", 0)
            
            # Compute combined score
            combined = (
                self.keyword_weight * keyword_score +
                self.semantic_weight * semantic_score
            )
            
            scored_findings.append(ScoredFinding(
                source=finding.get("source", ""),
                title=finding.get("title", ""),
                summary=finding.get("summary", ""),
                keywords=finding.get("keywords", []),
                keyword_relevance=keyword_score,
                semantic_relevance=semantic_score,
                combined_score=combined,
            ))
        
        return scored_findings
    
    def _keyword_only_ranking(
        self,
        findings: list[dict],
        top_k: Optional[int] = None,
    ) -> list[ScoredFinding]:
        """Fallback ranking using only keywords."""
        scored = []
        
        for finding in findings:
            keyword_score = finding.get("relevance", 0)
            
            scored.append(ScoredFinding(
                source=finding.get("source", ""),
                title=finding.get("title", ""),
                summary=finding.get("summary", ""),
                keywords=finding.get("keywords", []),
                keyword_relevance=keyword_score,
                semantic_relevance=0.0,
                combined_score=keyword_score,
            ))
        
        # Sort by keyword score
        scored.sort(key=lambda x: x.combined_score, reverse=True)
        
        # Filter by threshold
        filtered = [f for f in scored if f.combined_score >= self.relevance_threshold]
        
        if top_k:
            filtered = filtered[:top_k]
        
        return filtered
    
    def scored_to_dict(self, scored: ScoredFinding) -> dict:
        """Convert ScoredFinding to dictionary."""
        return {
            "source": scored.source,
            "title": scored.title,
            "summary": scored.summary,
            "keywords": scored.keywords,
            "keyword_relevance": scored.keyword_relevance,
            "semantic_relevance": scored.semantic_relevance,
            "relevance": scored.combined_score,
        }
