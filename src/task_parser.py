"""
Task Parser - Parse research queries into executable browser tasks.

Breaks down a research query into specific URLs and search tasks.
Supports both rule-based and LLM-powered query decomposition.
"""

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

# Import LLMClient at module level (may fail if litellm not installed)
try:
    from .llm_client import LLMClient
except ImportError:
    LLMClient = None  # type: ignore

logger = logging.getLogger(__name__)

# Search engines and their query formats (shared by all parsers)
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}",
    "bing": "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
}


def build_search_url(query: str, engine: str = "duckduckgo") -> str:
    """
    Build search engine URL.
    
    Args:
        query: Search query
        engine: Search engine name
        
    Returns:
        Search URL
    """
    template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["duckduckgo"])
    encoded_query = urllib.parse.quote_plus(query)
    return template.format(query=encoded_query)


# System prompt for LLM query decomposition
LLM_QUERY_DECOMPOSITION_PROMPT = """You are a research query analyzer. Your job is to break down complex research queries into specific, actionable search tasks.

For each query, analyze:
1. The main research objective
2. Key topics and subtopics to investigate
3. Specific search queries that would gather comprehensive information

Output a JSON object with the following structure:
{
    "objective": "Brief description of the research goal",
    "topics": ["topic1", "topic2", ...],
    "search_queries": [
        {
            "query": "specific search query",
            "type": "search|domain|comparison|news",
            "priority": 1-10,
            "domains": ["optional.com", "specific.domains.to.search"]
        }
    ],
    "keywords": ["key", "words", "for", "relevance", "filtering"]
}

Guidelines:
- Generate 3-8 search queries depending on complexity
- Use specific, focused queries rather than broad ones
- Include comparison queries when appropriate
- For technical topics, include domain-specific searches (github.com, stackoverflow.com, etc.)
- For news/trends, include recent date qualifiers
- Keywords should capture the essential terms for relevance filtering"""


@dataclass
class ResearchTask:
    """Represents a single research task."""
    id: str
    query: str
    url: str
    keywords: list[str] = field(default_factory=list)
    task_type: str = "search"  # search, direct, crawl
    priority: int = 0
    parent_id: Optional[str] = None


class TaskParser:
    """
    Parses research queries into executable browser tasks.

    Supports:
    - Natural language queries -> search engine URLs
    - Direct URL extraction
    - Keyword extraction for relevance filtering
    """

    # Common domain patterns for direct research
    RESEARCH_DOMAINS = [
        "arxiv.org",
        "github.com",
        "stackoverflow.com",
        "wikipedia.org",
        "medium.com",
        "dev.to",
        "reddit.com",
        "news.ycombinator.com",
        "techcrunch.com",
        "wired.com",
        "theverge.com",
    ]

    # Japanese search patterns
    JP_SEARCH_PATTERNS = [
        ("について調べて", "about"),
        ("について", "about"),
        ("の最新情報", "latest"),
        ("の動向", "trends"),
        ("比較", "comparison"),
        ("とは", "what is"),
        ("使い方", "how to use"),
        ("入門", "introduction"),
    ]

    def __init__(self, default_engine: str = "duckduckgo"):
        self.default_engine = default_engine

    async def parse(self, query: str) -> list[ResearchTask]:
        """
        Parse a research query into tasks.

        Args:
            query: Natural language research query

        Returns:
            List of ResearchTask objects
        """
        tasks = []

        # Extract any URLs from the query
        url_tasks = self._extract_urls(query)
        tasks.extend(url_tasks)

        # Extract keywords
        keywords = self._extract_keywords(query)

        # Generate search tasks
        search_tasks = self._generate_search_tasks(query, keywords)
        tasks.extend(search_tasks)

        # Add domain-specific tasks
        domain_tasks = self._generate_domain_tasks(query, keywords)
        tasks.extend(domain_tasks)

        # Deduplicate by URL
        seen_urls = set()
        unique_tasks = []
        for task in tasks:
            if task.url not in seen_urls:
                seen_urls.add(task.url)
                unique_tasks.append(task)

        # Sort by priority
        unique_tasks.sort(key=lambda t: t.priority, reverse=True)

        return unique_tasks

    def _extract_urls(self, query: str) -> list[ResearchTask]:
        """Extract URLs from query text."""
        tasks = []
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

        for match in re.finditer(url_pattern, query):
            url = match.group()
            tasks.append(ResearchTask(
                id=str(uuid4()),
                query=query,
                url=url,
                task_type="direct",
                priority=10  # Direct URLs get highest priority
            ))

        return tasks

    def _extract_keywords(self, query: str) -> list[str]:
        """Extract keywords from query for relevance filtering."""
        # Remove common Japanese particles and stop words
        jp_stopwords = [
            'を', 'に', 'は', 'が', 'の', 'で', 'と', 'も', 'や',
            'から', 'まで', 'より', 'など', 'について', 'とは',
            '調べて', '教えて', '知りたい', '最新', '情報',
        ]

        # Remove common English stop words
        en_stopwords = [
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must',
            'about', 'for', 'with', 'what', 'how', 'why', 'when', 'where',
            'latest', 'new', 'find', 'search', 'look', 'research',
        ]

        # Remove URLs
        text = re.sub(r'https?://\S+', '', query)

        # Tokenize
        words = re.findall(r'[\w\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+', text.lower())

        # Filter
        keywords = []
        for word in words:
            if len(word) < 2:
                continue
            if word in jp_stopwords or word in en_stopwords:
                continue
            keywords.append(word)

        return keywords

    def _generate_search_tasks(
        self,
        query: str,
        keywords: list[str]
    ) -> list[ResearchTask]:
        """Generate search engine tasks."""
        tasks = []

        # Clean query for search
        search_query = self._clean_search_query(query)

        # Main search with default engine
        main_url = self._build_search_url(search_query, self.default_engine)
        tasks.append(ResearchTask(
            id=str(uuid4()),
            query=query,
            url=main_url,
            keywords=keywords,
            task_type="search",
            priority=8
        ))

        # Add variant searches
        variants = self._generate_query_variants(search_query)
        for i, variant in enumerate(variants[:3]):
            url = self._build_search_url(variant, self.default_engine)
            tasks.append(ResearchTask(
                id=str(uuid4()),
                query=variant,
                url=url,
                keywords=keywords,
                task_type="search",
                priority=7 - i
            ))

        return tasks

    def _generate_domain_tasks(
        self,
        query: str,
        keywords: list[str]
    ) -> list[ResearchTask]:
        """Generate domain-specific search tasks."""
        tasks = []
        search_query = self._clean_search_query(query)

        # Detect query type and select relevant domains
        domains = self._select_domains(query)

        for i, domain in enumerate(domains[:5]):
            site_query = f"site:{domain} {search_query}"
            url = self._build_search_url(site_query, self.default_engine)
            tasks.append(ResearchTask(
                id=str(uuid4()),
                query=site_query,
                url=url,
                keywords=keywords,
                task_type="search",
                priority=5 - i
            ))

        return tasks

    def _clean_search_query(self, query: str) -> str:
        """Clean query for search engine use."""
        # Remove URLs
        text = re.sub(r'https?://\S+', '', query)

        # Remove common instruction phrases
        for pattern, _ in self.JP_SEARCH_PATTERNS:
            text = text.replace(pattern, ' ')

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text.strip()

    def _build_search_url(self, query: str, engine: str = "google") -> str:
        """Build search engine URL (delegates to module-level function)."""
        return build_search_url(query, engine)

    def _generate_query_variants(self, query: str) -> list[str]:
        """Generate variant queries for broader coverage."""
        variants = []

        # Add "latest" variant
        if "latest" not in query.lower() and "最新" not in query:
            variants.append(f"{query} latest 2024")

        # Add "tutorial" variant for technical queries
        tech_keywords = ['python', 'javascript', 'api', 'framework', 'library', 'tool']
        if any(kw in query.lower() for kw in tech_keywords):
            variants.append(f"{query} tutorial guide")

        # Add comparison variant
        if "vs" not in query.lower() and "comparison" not in query.lower():
            variants.append(f"{query} comparison alternatives")

        # Add news variant
        variants.append(f"{query} news")

        return variants

    def _select_domains(self, query: str) -> list[str]:
        """Select relevant domains based on query type."""
        query_lower = query.lower()

        # Technical/programming query
        if any(kw in query_lower for kw in ['python', 'javascript', 'code', 'programming', 'api', 'library']):
            return ['github.com', 'stackoverflow.com', 'dev.to', 'medium.com']

        # AI/ML query
        if any(kw in query_lower for kw in ['ai', 'machine learning', 'deep learning', 'llm', 'gpt', 'claude']):
            return ['arxiv.org', 'github.com', 'huggingface.co', 'openai.com']

        # News/trends query
        if any(kw in query_lower for kw in ['news', 'latest', 'trend', '最新', '動向']):
            return ['techcrunch.com', 'wired.com', 'theverge.com', 'news.ycombinator.com']

        # General research
        return ['wikipedia.org', 'medium.com', 'reddit.com']

    def create_crawl_tasks(
        self,
        parent_task: ResearchTask,
        urls: list[str],
        max_depth: int = 1
    ) -> list[ResearchTask]:
        """
        Create follow-up crawl tasks from discovered URLs.

        Args:
            parent_task: Parent task that discovered these URLs
            urls: List of URLs to crawl
            max_depth: Maximum crawl depth

        Returns:
            List of crawl tasks
        """
        tasks = []

        for url in urls[:10]:  # Limit to 10 URLs per parent
            tasks.append(ResearchTask(
                id=str(uuid4()),
                query=parent_task.query,
                url=url,
                keywords=parent_task.keywords,
                task_type="crawl",
                priority=parent_task.priority - 1,
                parent_id=parent_task.id
            ))

        return tasks


class LLMTaskParser:
    """
    LLM-powered task parser for intelligent query decomposition.
    
    Uses an LLM to analyze complex queries and generate targeted search tasks.
    Falls back to rule-based TaskParser on failure.
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        default_engine: str = "duckduckgo",
        fallback_to_rules: bool = True,
    ):
        """
        Initialize LLM task parser.
        
        Args:
            llm_client: LLM client instance (creates default if not provided)
            default_engine: Default search engine
            fallback_to_rules: Whether to fallback to rule-based parsing on failure
        """
        self.llm_client = llm_client
        self.default_engine = default_engine
        self.fallback_to_rules = fallback_to_rules
        self._rule_parser = TaskParser(default_engine=default_engine)
    
    async def _get_llm_client(self) -> LLMClient:
        """Get or create LLM client lazily."""
        if self.llm_client is None:
            if LLMClient is None:
                raise ImportError("LLMClient not available. Install litellm.")
            self.llm_client = LLMClient()
        return self.llm_client
    
    async def parse(self, query: str) -> list[ResearchTask]:
        """
        Parse a research query into tasks using LLM.
        
        Args:
            query: Natural language research query
            
        Returns:
            List of ResearchTask objects
        """
        try:
            llm = await self._get_llm_client()
            
            # Call LLM for query decomposition
            result = await llm.parse_json(
                prompt=f"Analyze and decompose this research query:\n\n{query}",
                system=LLM_QUERY_DECOMPOSITION_PROMPT,
            )
            
            # Convert LLM output to ResearchTasks
            tasks = self._convert_to_tasks(query, result)
            
            if tasks:
                return tasks
            
        except Exception as e:
            # Log the exception to understand why LLM parsing failed
            logger.warning(f"LLM query parsing failed, falling back to rules: {e}", exc_info=True)
            if not self.fallback_to_rules:
                raise
            # Fall through to rule-based parsing
        
        # Fallback to rule-based parsing
        if self.fallback_to_rules:
            return await self._rule_parser.parse(query)
        
        return []
    
    def _convert_to_tasks(self, original_query: str, llm_result: dict) -> list[ResearchTask]:
        """Convert LLM decomposition result to ResearchTask objects."""
        tasks = []
        keywords = llm_result.get("keywords", [])
        
        for search_item in llm_result.get("search_queries", []):
            search_query = search_item.get("query", "")
            if not search_query:
                continue
            
            task_type = search_item.get("type", "search")
            priority = search_item.get("priority", 5)
            domains = search_item.get("domains", [])
            
            if task_type == "domain" and domains:
                # Domain-specific searches
                for i, domain in enumerate(domains[:3]):
                    site_query = f"site:{domain} {search_query}"
                    url = self._build_search_url(site_query)
                    tasks.append(ResearchTask(
                        id=str(uuid4()),
                        query=site_query,
                        url=url,
                        keywords=keywords,
                        task_type="search",
                        priority=priority - i
                    ))
            else:
                # Regular search
                url = self._build_search_url(search_query)
                tasks.append(ResearchTask(
                    id=str(uuid4()),
                    query=search_query,
                    url=url,
                    keywords=keywords,
                    task_type="search",
                    priority=priority
                ))
        
        # Sort by priority
        tasks.sort(key=lambda t: t.priority, reverse=True)
        
        return tasks
    
    def _build_search_url(self, query: str) -> str:
        """Build search engine URL (delegates to module-level function)."""
        return build_search_url(query, self.default_engine)


def create_parser(use_llm: bool = False, **kwargs) -> TaskParser | LLMTaskParser:
    """
    Factory function to create appropriate parser.
    
    Args:
        use_llm: Whether to use LLM-powered parsing
        **kwargs: Additional arguments for parser
        
    Returns:
        TaskParser or LLMTaskParser instance
    """
    if use_llm:
        return LLMTaskParser(**kwargs)
    return TaskParser(**kwargs)
