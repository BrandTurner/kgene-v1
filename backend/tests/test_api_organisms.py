"""
Comprehensive Tests for Organisms API Endpoints

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- Filtering and sorting
- Validation (field constraints, custom validators)
- Error handling (404, 400, 422)
- Edge cases
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organism import Organism


# =============================================================================
# CREATE Tests - POST /organisms
# =============================================================================


@pytest.mark.asyncio
async def test_create_organism_success(test_client: AsyncClient):
    """Test creating a valid organism."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "eco", "name": "Escherichia coli K-12 MG1655"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "eco"
    assert data["name"] == "Escherichia coli K-12 MG1655"
    assert data["status"] is None
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_organism_duplicate_code(test_client: AsyncClient, sample_organism: Organism):
    """Test creating organism with duplicate code returns 400."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "eco", "name": "Another E. coli"}
    )

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "DUPLICATE_ORGANISM"
    assert "already exists" in data["message"].lower()


@pytest.mark.asyncio
async def test_create_organism_invalid_code_too_short(test_client: AsyncClient):
    """Test creating organism with code too short (< 3 chars) returns 422."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "ec", "name": "E. coli"}
    )

    assert response.status_code == 422
    data = response.json()
    assert "errors" in data
    # Should have validation error for 'code' field
    errors = data["errors"]
    assert any(err["field"] == "code" for err in errors)


@pytest.mark.asyncio
async def test_create_organism_invalid_code_too_long(test_client: AsyncClient):
    """Test creating organism with code too long (> 4 chars) returns 422."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "ecoli", "name": "E. coli"}
    )

    assert response.status_code == 422
    data = response.json()
    assert "errors" in data


@pytest.mark.asyncio
async def test_create_organism_invalid_code_uppercase(test_client: AsyncClient):
    """Test creating organism with uppercase code returns 422."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "ECO", "name": "E. coli"}
    )

    assert response.status_code == 422
    data = response.json()
    assert "errors" in data
    # Should mention "lowercase" in error message
    error_msg = str(data)
    assert "lowercase" in error_msg.lower()


@pytest.mark.asyncio
async def test_create_organism_invalid_code_numbers(test_client: AsyncClient):
    """Test creating organism with numbers in code returns 422."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "ec1", "name": "E. coli"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_organism_empty_name(test_client: AsyncClient):
    """Test creating organism with empty name returns 422."""
    response = await test_client.post(
        "/api/organisms",
        json={"code": "eco", "name": ""}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_organism_missing_required_fields(test_client: AsyncClient):
    """Test creating organism without required fields returns 422."""
    # Missing 'name'
    response = await test_client.post(
        "/api/organisms",
        json={"code": "eco"}
    )
    assert response.status_code == 422

    # Missing 'code'
    response = await test_client.post(
        "/api/organisms",
        json={"name": "E. coli"}
    )
    assert response.status_code == 422


# =============================================================================
# READ Tests - GET /organisms
# =============================================================================


@pytest.mark.asyncio
async def test_list_organisms_empty(test_client: AsyncClient):
    """Test listing organisms when none exist."""
    response = await test_client.get("/api/organisms")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_organisms(test_client: AsyncClient, sample_organism: Organism):
    """Test listing organisms returns all organisms."""
    response = await test_client.get("/api/organisms")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["code"] == "eco"
    assert data[0]["name"] == "Escherichia coli K-12 MG1655"


@pytest.mark.asyncio
async def test_list_organisms_multiple(test_client: AsyncClient, db_session: AsyncSession):
    """Test listing multiple organisms."""
    # Create multiple organisms
    organisms = [
        Organism(code="eco", name="Escherichia coli"),
        Organism(code="hsa", name="Homo sapiens"),
        Organism(code="mmu", name="Mus musculus"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    response = await test_client.get("/api/organisms")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    codes = [org["code"] for org in data]
    assert "eco" in codes
    assert "hsa" in codes
    assert "mmu" in codes


@pytest.mark.asyncio
async def test_get_organism_by_id(test_client: AsyncClient, sample_organism: Organism):
    """Test getting a specific organism by ID."""
    response = await test_client.get(f"/api/organisms/{sample_organism.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_organism.id
    assert data["code"] == "eco"


@pytest.mark.asyncio
async def test_get_organism_not_found(test_client: AsyncClient):
    """Test getting non-existent organism returns 404."""
    response = await test_client.get("/api/organisms/99999")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "ORGANISM_NOT_FOUND"
    assert "99999" in data["message"]


# =============================================================================
# FILTERING Tests - GET /organisms with query params
# =============================================================================


@pytest.mark.asyncio
async def test_filter_organisms_by_status(test_client: AsyncClient, db_session: AsyncSession):
    """Test filtering organisms by status."""
    # Create organisms with different statuses
    organisms = [
        Organism(code="eco", name="E. coli", status="complete"),
        Organism(code="hsa", name="H. sapiens", status="pending"),
        Organism(code="mmu", name="M. musculus", status="error"),
        Organism(code="sce", name="S. cerevisiae", status=None),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    # Filter by status=complete
    response = await test_client.get("/api/organisms?status=complete")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["code"] == "eco"

    # Filter by status=pending
    response = await test_client.get("/api/organisms?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["code"] == "hsa"


@pytest.mark.asyncio
async def test_filter_organisms_by_code_pattern(test_client: AsyncClient, db_session: AsyncSession):
    """Test filtering organisms by code pattern (partial match)."""
    organisms = [
        Organism(code="eco", name="E. coli"),
        Organism(code="ecj", name="E. coli J"),
        Organism(code="hsa", name="H. sapiens"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    # Search for code containing "ec"
    response = await test_client.get("/api/organisms?code_pattern=ec")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    codes = [org["code"] for org in data]
    assert "eco" in codes
    assert "ecj" in codes
    assert "hsa" not in codes


@pytest.mark.asyncio
async def test_filter_organisms_by_name_pattern(test_client: AsyncClient, db_session: AsyncSession):
    """Test filtering organisms by name pattern (case-insensitive)."""
    organisms = [
        Organism(code="eco", name="Escherichia coli"),
        Organism(code="ecj", name="Escherichia coli J"),
        Organism(code="hsa", name="Homo sapiens"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    # Search for name containing "coli" (case-insensitive)
    response = await test_client.get("/api/organisms?name_pattern=coli")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Search for "Homo"
    response = await test_client.get("/api/organisms?name_pattern=Homo")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["code"] == "hsa"


@pytest.mark.asyncio
async def test_filter_organisms_pagination(test_client: AsyncClient, db_session: AsyncSession):
    """Test pagination (skip and limit)."""
    # Create 10 organisms
    for i in range(10):
        org = Organism(code=f"o{i:02d}", name=f"Organism {i}")
        db_session.add(org)
    await db_session.commit()

    # Get first 3
    response = await test_client.get("/api/organisms?limit=3&skip=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Get next 3 (skip first 3)
    response = await test_client.get("/api/organisms?limit=3&skip=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Verify they're different sets
    first_batch = (await test_client.get("/api/organisms?limit=3&skip=0")).json()
    second_batch = (await test_client.get("/api/organisms?limit=3&skip=3")).json()
    assert first_batch[0]["id"] != second_batch[0]["id"]


@pytest.mark.asyncio
async def test_filter_organisms_invalid_limit(test_client: AsyncClient):
    """Test that limit > 1000 returns 422."""
    response = await test_client.get("/api/organisms?limit=2000")
    assert response.status_code == 422


# =============================================================================
# SORTING Tests - GET /organisms with sort params
# =============================================================================


@pytest.mark.asyncio
async def test_sort_organisms_by_name_asc(test_client: AsyncClient, db_session: AsyncSession):
    """Test sorting organisms by name (ascending)."""
    organisms = [
        Organism(code="mmu", name="Mus musculus"),
        Organism(code="eco", name="Escherichia coli"),
        Organism(code="hsa", name="Homo sapiens"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    response = await test_client.get("/api/organisms?sort_by=name&order=asc")
    assert response.status_code == 200
    data = response.json()

    # Should be alphabetical: E, H, M
    assert data[0]["name"] == "Escherichia coli"
    assert data[1]["name"] == "Homo sapiens"
    assert data[2]["name"] == "Mus musculus"


@pytest.mark.asyncio
async def test_sort_organisms_by_name_desc(test_client: AsyncClient, db_session: AsyncSession):
    """Test sorting organisms by name (descending)."""
    organisms = [
        Organism(code="eco", name="Escherichia coli"),
        Organism(code="hsa", name="Homo sapiens"),
        Organism(code="mmu", name="Mus musculus"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    response = await test_client.get("/api/organisms?sort_by=name&order=desc")
    assert response.status_code == 200
    data = response.json()

    # Should be reverse alphabetical: M, H, E
    assert data[0]["name"] == "Mus musculus"
    assert data[1]["name"] == "Homo sapiens"
    assert data[2]["name"] == "Escherichia coli"


@pytest.mark.asyncio
async def test_sort_organisms_by_code(test_client: AsyncClient, db_session: AsyncSession):
    """Test sorting organisms by code."""
    organisms = [
        Organism(code="mmu", name="M"),
        Organism(code="eco", name="E"),
        Organism(code="hsa", name="H"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    response = await test_client.get("/api/organisms?sort_by=code&order=asc")
    assert response.status_code == 200
    data = response.json()

    codes = [org["code"] for org in data]
    assert codes == ["eco", "hsa", "mmu"]


# =============================================================================
# UPDATE Tests - PUT /organisms/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_update_organism_name(test_client: AsyncClient, sample_organism: Organism):
    """Test updating organism name."""
    response = await test_client.put(
        f"/api/organisms/{sample_organism.id}",
        json={"name": "Updated E. coli Name"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated E. coli Name"
    assert data["code"] == "eco"  # Code unchanged


@pytest.mark.asyncio
async def test_update_organism_status(test_client: AsyncClient, sample_organism: Organism):
    """Test updating organism status."""
    response = await test_client.put(
        f"/api/organisms/{sample_organism.id}",
        json={"status": "complete"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"


@pytest.mark.asyncio
async def test_update_organism_invalid_status(test_client: AsyncClient, sample_organism: Organism):
    """Test updating organism with invalid status returns 422."""
    response = await test_client.put(
        f"/api/organisms/{sample_organism.id}",
        json={"status": "invalid_status"}
    )

    assert response.status_code == 422
    data = response.json()
    assert "errors" in data


@pytest.mark.asyncio
async def test_update_organism_not_found(test_client: AsyncClient):
    """Test updating non-existent organism returns 404."""
    response = await test_client.put(
        "/api/organisms/99999",
        json={"name": "New Name"}
    )

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "ORGANISM_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_organism_duplicate_code(test_client: AsyncClient, db_session: AsyncSession):
    """Test updating organism code to duplicate returns 400."""
    # Create two organisms
    org1 = Organism(code="eco", name="E. coli")
    org2 = Organism(code="hsa", name="H. sapiens")
    db_session.add_all([org1, org2])
    await db_session.commit()
    await db_session.refresh(org1)
    await db_session.refresh(org2)

    # Try to update org2's code to "eco" (duplicate)
    response = await test_client.put(
        f"/api/organisms/{org2.id}",
        json={"code": "eco"}
    )

    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "DUPLICATE_ORGANISM"


# =============================================================================
# DELETE Tests - DELETE /organisms/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_delete_organism(test_client: AsyncClient, sample_organism: Organism, db_session: AsyncSession):
    """Test deleting an organism."""
    organism_id = sample_organism.id

    response = await test_client.delete(f"/api/organisms/{organism_id}")

    assert response.status_code == 204

    # Verify organism no longer exists
    result = await db_session.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    deleted_org = result.scalar_one_or_none()
    assert deleted_org is None


@pytest.mark.asyncio
async def test_delete_organism_not_found(test_client: AsyncClient):
    """Test deleting non-existent organism returns 404."""
    response = await test_client.delete("/api/organisms/99999")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "ORGANISM_NOT_FOUND"


# =============================================================================
# EDGE CASES and ERROR HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_create_organism_with_extra_fields(test_client: AsyncClient):
    """Test that extra fields in request are ignored."""
    response = await test_client.post(
        "/api/organisms",
        json={
            "code": "eco",
            "name": "E. coli",
            "extra_field": "should be ignored",
            "another_field": 123
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "extra_field" not in data
    assert "another_field" not in data


@pytest.mark.asyncio
async def test_response_includes_correlation_id(test_client: AsyncClient):
    """Test that error responses include correlation ID for tracing."""
    response = await test_client.get("/api/organisms/99999")

    assert response.status_code == 404
    data = response.json()

    # Should have correlation_id in response body
    assert "correlation_id" in data
    assert data["correlation_id"] is not None

    # Should have X-Request-ID header
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_combined_filters_and_sorting(test_client: AsyncClient, db_session: AsyncSession):
    """Test combining multiple filters with sorting."""
    organisms = [
        Organism(code="eco", name="Escherichia coli", status="complete"),
        Organism(code="ecj", name="Escherichia coli J", status="complete"),
        Organism(code="hsa", name="Homo sapiens", status="complete"),
        Organism(code="mmu", name="Mus musculus", status="pending"),
    ]
    for org in organisms:
        db_session.add(org)
    await db_session.commit()

    # Filter by status=complete AND name_pattern=coli, sorted by code desc
    response = await test_client.get(
        "/api/organisms?status=complete&name_pattern=coli&sort_by=code&order=desc"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Should be ecj, eco (desc order)
    assert data[0]["code"] == "ecj"
    assert data[1]["code"] == "eco"
