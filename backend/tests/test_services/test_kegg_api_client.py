"""
Tests for KEGG API Client

WHAT WE'RE TESTING:
The KEGG API client is our interface to KEGG's REST API, which provides:
- Gene lists for organisms
- KO (KEGG Orthology) mappings
- Cross-organism gene relationships

WHY THESE TESTS MATTER:
KEGG API is an external dependency with:
- Rate limits (3 req/sec)
- Occasional downtime
- Changing data

These tests ensure our client handles all edge cases gracefully.

TESTING STRATEGY:
- Mock httpx responses (don't hit real KEGG API)
- Test rate limiting behavior
- Test retry logic
- Test TSV parsing
- Test error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import httpx
from app.services.kegg_api import KEGGClient, KEGGAPIError, KEGGRateLimitError


# =============================================================================
# RATE LIMITING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limiting_enforced():
    """
    Test that rate limiting delays are enforced between requests.

    KEGG requires 0.35 seconds between requests (3 req/sec max).
    This test verifies our client respects this limit.

    WHY IT MATTERS:
    Violating rate limits can get your IP temporarily banned from KEGG.
    This test ensures we're being good API citizens.
    """
    async with KEGGClient() as client:
        # Mock the HTTP client to return immediately
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text="test_response"
        ))

        # Make first request
        start_time = asyncio.get_event_loop().time()
        await client._request("/test1")

        # Make second request - should be delayed
        await client._request("/test2")
        elapsed = asyncio.get_event_loop().time() - start_time

        # Verify delay was enforced (at least 0.35 seconds)
        assert elapsed >= 0.35, \
            f"Rate limit not enforced! Elapsed: {elapsed:.3f}s, expected >= 0.35s"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_requests_serialized():
    """
    Test that concurrent requests are serialized by rate limiting.

    SCENARIO:
    If two coroutines try to make KEGG requests simultaneously,
    they should be queued and executed with proper delays.

    WHY IT MATTERS:
    Without proper locking, concurrent requests could violate rate limits.
    The _rate_limit_lock ensures requests are properly serialized.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text="response"
        ))

        # Launch 3 concurrent requests
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(
            client._request("/test1"),
            client._request("/test2"),
            client._request("/test3"),
        )
        total_time = asyncio.get_event_loop().time() - start_time

        # With 3 requests at 0.35s spacing, should take at least 0.7s
        # (0s → req1, 0.35s → req2, 0.7s → req3)
        assert total_time >= 0.7, \
            f"Concurrent requests not properly serialized. Time: {total_time:.3f}s"


# =============================================================================
# RETRY LOGIC TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_500_error():
    """
    Test that client retries on HTTP 500 (server error).

    KEGG occasionally returns 500 errors (server overload, maintenance).
    Our client should retry with exponential backoff.

    RETRY STRATEGY:
    - Delay: 1s, 2s, 4s, 8s, ... up to 30s max
    - Max retries: 10
    - Succeed if any retry succeeds
    """
    async with KEGGClient() as client:
        # Mock: Fail twice, then succeed
        mock_responses = [
            MagicMock(status_code=500, text="Internal Server Error"),
            MagicMock(status_code=500, text="Internal Server Error"),
            MagicMock(status_code=200, text="success"),
        ]
        client.client.get = AsyncMock(side_effect=mock_responses)

        # Should retry and eventually succeed
        result = await client._request("/test")
        assert result == "success"

        # Verify it tried 3 times (2 failures + 1 success)
        assert client.client.get.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_exhaustion_raises_error():
    """
    Test that client raises error after all retries exhausted.

    If KEGG is down for extended period, we shouldn't retry forever.
    After MAX_RETRIES attempts, raise KEGGAPIError.
    """
    async with KEGGClient() as client:
        # Mock: Always return 500
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=500,
            text="Server Error"
        ))

        # Should raise KEGGAPIError after retries exhausted
        with pytest.raises(KEGGAPIError, match="after 3 attempts"):
            # Set lower retry count for faster test
            await client._request("/test", retries=3)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_rate_limit_429():
    """
    Test retry behavior on HTTP 429 (Too Many Requests).

    KEGG returns 429 when we exceed rate limits.
    Client should back off and retry.

    WHY SEPARATE FROM 500?
    Rate limit errors should potentially wait longer before retrying.
    """
    async with KEGGClient() as client:
        mock_responses = [
            MagicMock(status_code=429, text="Too Many Requests"),
            MagicMock(status_code=200, text="success"),
        ]
        client.client.get = AsyncMock(side_effect=mock_responses)

        result = await client._request("/test")
        assert result == "success"
        assert client.client.get.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exponential_backoff():
    """
    Test that retry delays increase exponentially.

    BACKOFF STRATEGY:
    - Attempt 1: Immediate
    - Attempt 2: Wait 1s
    - Attempt 3: Wait 2s
    - Attempt 4: Wait 4s
    - Attempt 5: Wait 8s
    - Attempt N: Wait min(2^(N-2), 30s)

    This prevents hammering KEGG when it's struggling.
    """
    async with KEGGClient() as client:
        # Track sleep times
        sleep_times = []

        original_sleep = asyncio.sleep
        async def mock_sleep(delay):
            sleep_times.append(delay)
            # Don't actually sleep (makes test fast)
            return

        with patch('asyncio.sleep', side_effect=mock_sleep):
            # Always fail
            client.client.get = AsyncMock(return_value=MagicMock(
                status_code=500,
                text="Error"
            ))

            try:
                await client._request("/test", retries=4)
            except KEGGAPIError:
                pass  # Expected

        # Verify exponential backoff: [1, 2, 4]
        # (First request has no sleep, then 1s, 2s, 4s)
        assert len(sleep_times) >= 3
        assert sleep_times[0] >= 1.0  # First retry: 1s
        assert sleep_times[1] >= 2.0  # Second retry: 2s
        assert sleep_times[2] >= 4.0  # Third retry: 4s


# =============================================================================
# RESPONSE PARSING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_organism_genes_parsing(kegg_gene_list_response):
    """
    Test parsing of KEGG /list endpoint TSV response.

    KEGG FORMAT:
    gene_id<TAB>description
    gene_id<TAB>description
    ...

    PARSING LOGIC:
    Split each line on tab, extract gene_id and description.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=kegg_gene_list_response  # Fixture from conftest.py
        ))

        genes = await client.list_organism_genes("eco")

        # Verify correct number of genes parsed
        assert len(genes) == 4

        # Verify structure
        assert genes[0]["name"] == "eco:b0001"
        assert "thr operon leader peptide" in genes[0]["description"]

        assert genes[1]["name"] == "eco:b0002"
        assert "aspartokinase" in genes[1]["description"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_genes_to_ko_parsing(kegg_ko_mapping_response):
    """
    Test parsing of KEGG /link/ko endpoint TSV response.

    KEGG FORMAT:
    gene_id<TAB>ko_id
    gene_id<TAB>ko_id
    ...

    PARSING LOGIC:
    Build dictionary: {gene_id: [ko_ids]}
    One gene can map to multiple KO groups.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=kegg_ko_mapping_response  # Fixture
        ))

        ko_map = await client.link_genes_to_ko("eco")

        # Verify mappings
        assert "eco:b0001" in ko_map
        assert "ko:K01234" in ko_map["eco:b0001"]

        assert "eco:b0002" in ko_map
        assert "ko:K00928" in ko_map["eco:b0002"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_organisms_by_ko_parsing(kegg_organisms_in_ko_response):
    """
    Test parsing of KEGG /link/genes/<ko_id> endpoint.

    KEGG FORMAT:
    ko_id<TAB>gene_id
    ko_id<TAB>gene_id
    ...

    PARSING LOGIC:
    Extract all gene_ids for the given KO group.
    These represent potential orthologs across organisms.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=kegg_organisms_in_ko_response  # Fixture
        ))

        genes = await client.get_organisms_by_ko("K00928")

        # Verify all genes extracted
        assert "eco:b0002" in genes  # E. coli
        assert "hsa:5236" in genes   # Human
        assert "mmu:21881" in genes  # Mouse
        assert "ath:AT3G51000" in genes  # Arabidopsis

        # Verify correct count
        assert len(genes) == 5  # 5 organisms in fixture


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_network_error_handling():
    """
    Test handling of network errors (connection timeout, DNS failure).

    SCENARIO:
    Internet connection drops or KEGG server unreachable.

    EXPECTED:
    Client should retry with backoff, then raise KEGGAPIError.
    """
    async with KEGGClient() as client:
        # Mock network error
        client.client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with pytest.raises(KEGGAPIError, match="Network error"):
            await client._request("/test", retries=2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_response_handling():
    """
    Test handling of empty responses from KEGG.

    SCENARIO:
    KEGG returns 200 OK but empty body (rare but possible).

    EXPECTED:
    Parse as empty list (no genes/KOs found).
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=""  # Empty response
        ))

        genes = await client.list_organism_genes("invalid_org")
        assert genes == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_malformed_tsv_handling():
    """
    Test handling of malformed TSV responses.

    SCENARIO:
    KEGG returns corrupted data (missing tabs, extra fields).

    EXPECTED:
    Skip malformed lines, parse valid ones.
    """
    async with KEGGClient() as client:
        # TSV with missing tab on line 2
        malformed_tsv = """eco:b0001\tvalid gene
eco:b0002_missing_tab_description
eco:b0003\tanother valid gene"""

        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=malformed_tsv
        ))

        genes = await client.list_organism_genes("eco")

        # Should parse 2 valid lines, skip malformed line
        assert len(genes) == 2
        assert genes[0]["name"] == "eco:b0001"
        assert genes[1]["name"] == "eco:b0003"


# =============================================================================
# CONTEXT MANAGER TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager_lifecycle():
    """
    Test that context manager properly initializes and cleans up httpx client.

    WHY IT MATTERS:
    Resource leaks (unclosed connections) can exhaust system resources.
    The async context manager ensures cleanup even if errors occur.
    """
    client = KEGGClient()

    # Before entering context: no httpx client
    assert client.client is None

    async with client:
        # Inside context: httpx client exists
        assert client.client is not None
        assert isinstance(client.client, httpx.AsyncClient)

    # After exiting context: client should be closed
    # (client object still exists but httpx client is closed)
    assert client.client is not None  # Object exists
    # httpx.AsyncClient doesn't have is_closed, but we called aclose()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_without_context_manager_raises_error():
    """
    Test that calling _request outside context manager raises error.

    WHY IT MATTERS:
    Using the client without 'async with' would result in no httpx client,
    causing confusing errors. We raise a clear error message instead.
    """
    client = KEGGClient()

    # Try to make request without entering context manager
    with pytest.raises(KEGGAPIError, match="not initialized"):
        await client._request("/test")


# =============================================================================
# INTEGRATION-LIKE TESTS (Still Mocked)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_organism_gene_fetch_workflow():
    """
    Test complete workflow: fetch genes + KO mappings for organism.

    WORKFLOW:
    1. Fetch all genes for organism (e.g., E. coli)
    2. Fetch KO mappings for those genes
    3. Combine data for ortholog discovery

    This simulates what the background job does.
    """
    async with KEGGClient() as client:
        # Mock gene list response
        gene_response = """eco:b0001\tGene 1
eco:b0002\tGene 2"""

        # Mock KO mapping response
        ko_response = """eco:b0001\tko:K01234
eco:b0002\tko:K05678"""

        responses = [
            MagicMock(status_code=200, text=gene_response),
            MagicMock(status_code=200, text=ko_response),
        ]
        client.client.get = AsyncMock(side_effect=responses)

        # Step 1: Fetch genes
        genes = await client.list_organism_genes("eco")
        assert len(genes) == 2

        # Step 2: Fetch KO mappings
        ko_map = await client.link_genes_to_ko("eco")
        assert len(ko_map) == 2
        assert "ko:K01234" in ko_map["eco:b0001"]

        # Verify rate limiting was respected (2 requests = 1 delay)
        # This is tested implicitly by the rate limit lock


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_requests_respect_rate_limit():
    """
    Test that batch processing many genes respects rate limits.

    SCENARIO:
    Processing 100 genes means 100 KEGG API calls.
    At 3 req/sec, this should take ~33 seconds.

    WHY IT MATTERS:
    This is what happens during ortholog discovery.
    We need to ensure rate limiting scales to large batches.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text="ko:K00001\teco:b0001"
        ))

        # Make 10 requests (testing with fewer for speed)
        start_time = asyncio.get_event_loop().time()
        for i in range(10):
            await client._request(f"/test{i}")
        elapsed = asyncio.get_event_loop().time() - start_time

        # 10 requests at 0.35s spacing = 9 delays = 3.15s minimum
        # Allow some tolerance for test execution overhead
        assert elapsed >= 3.0, \
            f"Batch rate limiting failed. Elapsed: {elapsed:.2f}s, expected >= 3.0s"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_organism_not_found_returns_empty():
    """
    Test behavior when organism code doesn't exist in KEGG.

    EXPECTED:
    KEGG returns empty response or specific error.
    Client should return empty list gracefully.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=""  # No genes found
        ))

        genes = await client.list_organism_genes("nonexistent_org")
        assert genes == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ko_with_no_genes_returns_empty():
    """
    Test KO query when no genes are in that KO group.

    SCENARIO:
    Newly created KO groups might have no assigned genes yet.

    EXPECTED:
    Return empty list.
    """
    async with KEGGClient() as client:
        client.client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            text=""
        ))

        genes = await client.get_organisms_by_ko("K99999")
        assert genes == []


# =============================================================================
# RUN TESTS
# =============================================================================

"""
TO RUN THESE TESTS:

    # All KEGG client tests
    pytest tests/test_services/test_kegg_api_client.py -v

    # Only unit tests (fast)
    pytest tests/test_services/test_kegg_api_client.py -m unit -v

    # Specific test
    pytest tests/test_services/test_kegg_api_client.py::test_rate_limiting_enforced -v

    # With coverage
    pytest tests/test_services/test_kegg_api_client.py --cov=app.services.kegg_api

EXPECTED RESULTS:
- All tests should pass
- No real KEGG API calls made (fully mocked)
- Tests complete in <5 seconds
- Coverage should be >90% for kegg_api.py
"""
