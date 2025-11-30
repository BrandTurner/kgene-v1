"""
KEGG REST API Client

This module provides an async client for interacting with the KEGG REST API.
Documentation: https://www.kegg.jp/kegg/rest/keggapi.html

Rate Limit: 3 requests/second for academic use
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class KEGGAPIError(Exception):
    """Base exception for KEGG API errors."""
    pass


class KEGGRateLimitError(KEGGAPIError):
    """Raised when rate limit is exceeded."""
    pass


class KEGGClient:
    """
    Async client for KEGG REST API.

    Implements rate limiting and retry logic for reliable API access.
    """

    # KEGG REST API base URL
    BASE_URL = "https://rest.kegg.jp"

    # Rate limit: 3 requests per second = 0.35 seconds between requests
    RATE_LIMIT_DELAY = 0.35

    # Retry configuration - increased to 10 for critical bioinformatics data
    MAX_RETRIES = 10
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 30.0  # cap exponential backoff at 30 seconds

    def __init__(self):
        """Initialize KEGG client with httpx async client."""
        self.client: Optional[httpx.AsyncClient] = None
        self._last_request_time: Optional[float] = None
        self._rate_limit_lock = asyncio.Lock()

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        async with self._rate_limit_lock:
            if self._last_request_time is not None:
                elapsed = asyncio.get_event_loop().time() - self._last_request_time
                if elapsed < self.RATE_LIMIT_DELAY:
                    await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _request(
        self,
        endpoint: str,
        retries: int = MAX_RETRIES
    ) -> str:
        """
        Make a rate-limited request to KEGG API with retry logic.

        Args:
            endpoint: API endpoint (e.g., "/list/hsa")
            retries: Number of retry attempts

        Returns:
            Response text

        Raises:
            KEGGAPIError: On API errors after all retries exhausted
            KEGGRateLimitError: On persistent rate limit issues
        """
        if not self.client:
            raise KEGGAPIError("Client not initialized. Use 'async with' context manager.")

        await self._rate_limit()

        last_error = None

        for attempt in range(retries):
            try:
                logger.debug(f"KEGG API request: {endpoint} (attempt {attempt + 1}/{retries})")

                response = await self.client.get(endpoint)

                # Check for rate limiting (KEGG returns 403 or 429)
                if response.status_code in [403, 429]:
                    # Calculate exponential backoff delay
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** attempt),
                        self.MAX_RETRY_DELAY
                    )

                    logger.warning(
                        f"⚠️  KEGG API rate limit hit (attempt {attempt + 1}/{retries}). "
                        f"Could not make connection. Trying again in {delay:.1f}s, please be patient..."
                    )

                    if attempt < retries - 1:
                        await asyncio.sleep(delay)
                        continue

                    raise KEGGRateLimitError(
                        f"KEGG API rate limit exceeded after {retries} attempts"
                    )

                # Check for other errors
                if response.status_code >= 400:
                    error_msg = f"KEGG API returned status {response.status_code}"
                    logger.error(f"{error_msg}: {response.text[:200]}")

                    if attempt < retries - 1:
                        delay = min(
                            self.INITIAL_RETRY_DELAY * (2 ** attempt),
                            self.MAX_RETRY_DELAY
                        )
                        logger.warning(
                            f"⚠️  {error_msg} (attempt {attempt + 1}/{retries}). "
                            f"Could not make connection. Trying again in {delay:.1f}s, please be patient..."
                        )
                        await asyncio.sleep(delay)
                        continue

                    raise KEGGAPIError(
                        f"KEGG API returned status {response.status_code} after {retries} attempts: "
                        f"{response.text[:200]}"
                    )

                # Success!
                if attempt > 0:
                    logger.info(f"✓ Connection successful after {attempt + 1} attempts")

                return response.text

            except httpx.RequestError as e:
                last_error = e

                if attempt < retries - 1:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** attempt),
                        self.MAX_RETRY_DELAY
                    )
                    logger.warning(
                        f"⚠️  Network error: {str(e)[:100]} (attempt {attempt + 1}/{retries}). "
                        f"Could not make connection. Trying again in {delay:.1f}s, please be patient..."
                    )
                    await asyncio.sleep(delay)
                    continue

                raise KEGGAPIError(
                    f"Network error after {retries} attempts: {e}"
                )

        # Should never reach here, but just in case
        raise KEGGAPIError(
            f"Max retries ({retries}) exceeded. Last error: {last_error}"
        )

    async def list_organism_genes(self, organism_code: str) -> List[Dict[str, str]]:
        """
        Fetch all genes for an organism from KEGG.

        API: GET /list/{organism_code}
        Example: /list/hsa (Homo sapiens)

        Args:
            organism_code: KEGG organism code (e.g., "hsa", "eco")

        Returns:
            List of dicts with keys: 'name', 'description'
            Example: [
                {'name': 'hsa:10458', 'description': 'BAIAP2; BAI1-associated protein 2'},
                ...
            ]

        Raises:
            KEGGAPIError: On API errors after all retries
        """
        logger.info(f"Fetching gene list for organism: {organism_code}")

        response_text = await self._request(f"/list/{organism_code}")

        genes = []
        for line in response_text.strip().split('\n'):
            if not line:
                continue

            # KEGG returns TSV format: gene_id\tdescription
            parts = line.split('\t', 1)
            if len(parts) == 2:
                genes.append({
                    'name': parts[0].strip(),
                    'description': parts[1].strip()
                })

        logger.info(f"✓ Successfully retrieved {len(genes)} genes for organism {organism_code}")
        return genes

    async def get_gene_info(self, gene_id: str) -> Optional[Dict[str, str]]:
        """
        Get detailed information about a specific gene.

        API: GET /get/{gene_id}
        Example: /get/hsa:10458

        Args:
            gene_id: KEGG gene ID (e.g., "hsa:10458")

        Returns:
            Dict with gene information, or None if not found

        Raises:
            KEGGAPIError: On API errors after all retries
        """
        logger.debug(f"Fetching gene info for: {gene_id}")

        try:
            response_text = await self._request(f"/get/{gene_id}")

            # Parse KEGG flat file format
            # This is a simple parser - can be enhanced as needed
            info = {
                'gene_id': gene_id,
                'raw': response_text
            }

            return info

        except KEGGAPIError as e:
            if "404" in str(e):
                return None
            raise

    async def link_genes_to_ko(self, organism_code: str) -> Dict[str, List[str]]:
        """
        Get gene-to-KO (KEGG Orthology) mappings for an organism.

        API: GET /link/ko/{organism_code}
        Example: /link/ko/hsa

        This is useful for finding orthologs via KO groups.

        Args:
            organism_code: KEGG organism code

        Returns:
            Dict mapping gene IDs to KO IDs
            Example: {'hsa:10458': ['K12345', 'K67890'], ...}

        Raises:
            KEGGAPIError: On API errors after all retries
        """
        logger.info(f"Fetching KO mappings for organism: {organism_code}")

        response_text = await self._request(f"/link/ko/{organism_code}")

        gene_to_ko: Dict[str, List[str]] = {}
        for line in response_text.strip().split('\n'):
            if not line:
                continue

            # Format: gene_id\tko_id
            parts = line.split('\t')
            if len(parts) == 2:
                gene_id = parts[0].strip()
                ko_id = parts[1].strip()

                if gene_id not in gene_to_ko:
                    gene_to_ko[gene_id] = []
                gene_to_ko[gene_id].append(ko_id)

        logger.info(f"✓ Retrieved KO mappings for {len(gene_to_ko)} genes")
        return gene_to_ko

    async def get_organisms_by_ko(self, ko_id: str) -> List[str]:
        """
        Get all organisms that have genes in a specific KO group.

        API: GET /link/genes/{ko_id}
        Example: /link/genes/K12345

        Useful for finding orthologs across species.

        Args:
            ko_id: KEGG Orthology ID (e.g., "K12345" or "ko:K12345")

        Returns:
            List of gene IDs from different organisms

        Raises:
            KEGGAPIError: On API errors after all retries
        """
        logger.debug(f"Fetching organisms for KO: {ko_id}")

        # Remove 'ko:' prefix if present (KEGG API expects just the K number)
        ko_number = ko_id.replace('ko:', '')

        response_text = await self._request(f"/link/genes/{ko_number}")

        genes = []
        for line in response_text.strip().split('\n'):
            if not line:
                continue

            parts = line.split('\t')
            if len(parts) >= 2:
                genes.append(parts[1].strip())

        return genes


# Convenience function for single-use requests
async def fetch_organism_genes(organism_code: str) -> List[Dict[str, str]]:
    """
    Convenience function to fetch genes for an organism.

    Args:
        organism_code: KEGG organism code

    Returns:
        List of gene dicts
    """
    async with KEGGClient() as client:
        return await client.list_organism_genes(organism_code)
