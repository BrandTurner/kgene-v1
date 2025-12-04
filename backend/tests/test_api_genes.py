"""
Comprehensive Tests for Genes API Endpoints

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- Bioinformatics-specific filtering (ortholog presence, identity %, species)
- Validation (ortholog_identity 0-100%, SW scores >= 0)
- Error handling
- Edge cases
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.gene import Gene
from app.models.organism import Organism


# =============================================================================
# CREATE Tests - POST /genes
# =============================================================================


@pytest.mark.asyncio
async def test_create_gene_success(test_client: AsyncClient, sample_organism: Organism):
    """Test creating a valid gene."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0001",
            "description": "thrL; thr operon leader peptide",
            "organism_id": sample_organism.id
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "eco:b0001"
    assert data["description"] == "thrL; thr operon leader peptide"
    assert data["organism_id"] == sample_organism.id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_gene_with_ortholog_data(test_client: AsyncClient, sample_organism: Organism):
    """Test creating gene with ortholog information."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0002",
            "description": "thrA; aspartokinase",
            "organism_id": sample_organism.id,
            "ortholog_name": "hsa:5236",
            "ortholog_description": "THRSP",
            "ortholog_species": "Homo sapiens",
            "ortholog_length": 450,
            "ortholog_sw_score": 250,
            "ortholog_identity": 85.5
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ortholog_name"] == "hsa:5236"
    assert data["ortholog_species"] == "Homo sapiens"
    assert data["ortholog_identity"] == 85.5


@pytest.mark.asyncio
async def test_create_gene_nonexistent_organism(test_client: AsyncClient):
    """Test creating gene with non-existent organism returns 404."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0001",
            "description": "test gene",
            "organism_id": 99999
        }
    )

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "ORGANISM_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_gene_invalid_ortholog_identity(test_client: AsyncClient, sample_organism: Organism):
    """Test creating gene with invalid ortholog_identity (> 100%) returns 422."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0001",
            "description": "test",
            "organism_id": sample_organism.id,
            "ortholog_identity": 150.0  # Invalid: > 100%
        }
    )

    assert response.status_code == 422
    data = response.json()
    assert "errors" in data
    # Should mention "100" or "identity"
    error_text = str(data).lower()
    assert "100" in error_text or "identity" in error_text


@pytest.mark.asyncio
async def test_create_gene_negative_ortholog_score(test_client: AsyncClient, sample_organism: Organism):
    """Test creating gene with negative SW score returns 422."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0001",
            "description": "test",
            "organism_id": sample_organism.id,
            "ortholog_sw_score": -50  # Invalid: negative score
        }
    )

    assert response.status_code == 422


# =============================================================================
# READ Tests - GET /genes and GET /genes/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_list_genes_empty(test_client: AsyncClient):
    """Test listing genes when none exist."""
    response = await test_client.get("/api/genes")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_genes(test_client: AsyncClient, organism_with_genes: Organism, sample_genes: list[Gene]):
    """Test listing all genes."""
    response = await test_client.get("/api/genes")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4  # sample_genes fixture creates 4 genes
    assert all("name" in gene for gene in data)


@pytest.mark.asyncio
async def test_get_gene_by_id(test_client: AsyncClient, sample_genes: list[Gene]):
    """Test getting a specific gene by ID."""
    gene = sample_genes[0]
    response = await test_client.get(f"/api/genes/{gene.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == gene.id
    assert data["name"] == gene.name


@pytest.mark.asyncio
async def test_get_gene_not_found(test_client: AsyncClient):
    """Test getting non-existent gene returns 404."""
    response = await test_client.get("/api/genes/99999")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "GENE_NOT_FOUND"


# =============================================================================
# FILTERING Tests - Bioinformatics-Focused Filters
# =============================================================================


@pytest.mark.asyncio
async def test_filter_genes_by_organism(test_client: AsyncClient, db_session: AsyncSession):
    """Test filtering genes by organism_id."""
    # Create two organisms with genes
    org1 = Organism(code="eco", name="E. coli")
    org2 = Organism(code="hsa", name="H. sapiens")
    db_session.add_all([org1, org2])
    await db_session.commit()
    await db_session.refresh(org1)
    await db_session.refresh(org2)

    # Add genes to each organism
    genes_org1 = [
        Gene(name="eco:b0001", description="gene 1", organism_id=org1.id),
        Gene(name="eco:b0002", description="gene 2", organism_id=org1.id),
    ]
    genes_org2 = [
        Gene(name="hsa:1234", description="gene 3", organism_id=org2.id),
    ]
    db_session.add_all(genes_org1 + genes_org2)
    await db_session.commit()

    # Filter by organism 1
    response = await test_client.get(f"/api/genes?organism_id={org1.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(gene["organism_id"] == org1.id for gene in data)

    # Filter by organism 2
    response = await test_client.get(f"/api/genes?organism_id={org2.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["organism_id"] == org2.id


@pytest.mark.asyncio
async def test_filter_genes_has_ortholog_true(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test filtering for genes WITH orthologs (has_ortholog=true)."""
    # Create genes with and without orthologs
    genes = [
        Gene(
            name="eco:b0001",
            description="gene 1",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1234",  # HAS ortholog
            ortholog_species="hsa",
            ortholog_identity=85.0
        ),
        Gene(
            name="eco:b0002",
            description="gene 2",
            organism_id=sample_organism.id,
            ortholog_name="mmu:5678",  # HAS ortholog
            ortholog_species="mmu",
            ortholog_identity=90.0
        ),
        Gene(
            name="eco:b0003",
            description="gene 3",
            organism_id=sample_organism.id,
            ortholog_name=None  # NO ortholog (orphan gene)
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Filter for genes WITH orthologs
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&has_ortholog=true"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(gene["ortholog_name"] is not None for gene in data)


@pytest.mark.asyncio
async def test_filter_genes_has_ortholog_false(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test filtering for genes WITHOUT orthologs (orphan genes)."""
    # Create genes with and without orthologs
    genes = [
        Gene(
            name="eco:b0001",
            description="gene 1",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1234",
            ortholog_identity=85.0
        ),
        Gene(
            name="eco:b0002",
            description="orphan gene 1",
            organism_id=sample_organism.id,
            ortholog_name=None  # NO ortholog
        ),
        Gene(
            name="eco:b0003",
            description="orphan gene 2",
            organism_id=sample_organism.id,
            ortholog_name=None  # NO ortholog
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Filter for genes WITHOUT orthologs (orphan genes)
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&has_ortholog=false"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(gene["ortholog_name"] is None for gene in data)


@pytest.mark.asyncio
async def test_filter_genes_by_identity_range(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test filtering genes by ortholog identity percentage range."""
    # Create genes with different identity percentages
    genes = [
        Gene(name="eco:b0001", description="low identity", organism_id=sample_organism.id,
             ortholog_name="a", ortholog_identity=50.0),
        Gene(name="eco:b0002", description="medium identity", organism_id=sample_organism.id,
             ortholog_name="b", ortholog_identity=75.0),
        Gene(name="eco:b0003", description="high identity", organism_id=sample_organism.id,
             ortholog_name="c", ortholog_identity=95.0),
        Gene(name="eco:b0004", description="no ortholog", organism_id=sample_organism.id,
             ortholog_name=None),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Filter for high-confidence orthologs (>= 70%)
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&min_identity=70.0"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # 75% and 95%
    assert all(gene["ortholog_identity"] >= 70.0 for gene in data)

    # Filter for identity range 60-80%
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&min_identity=60.0&max_identity=80.0"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1  # Only 75%
    assert data[0]["ortholog_identity"] == 75.0


@pytest.mark.asyncio
async def test_filter_genes_by_species(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test filtering genes by ortholog species (case-insensitive partial match)."""
    genes = [
        Gene(name="eco:b0001", description="human ortholog", organism_id=sample_organism.id,
             ortholog_name="hsa:1", ortholog_species="Homo sapiens"),
        Gene(name="eco:b0002", description="mouse ortholog", organism_id=sample_organism.id,
             ortholog_name="mmu:2", ortholog_species="Mus musculus"),
        Gene(name="eco:b0003", description="yeast ortholog", organism_id=sample_organism.id,
             ortholog_name="sce:3", ortholog_species="Saccharomyces cerevisiae"),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Search for human orthologs (case-insensitive)
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&ortholog_species=homo"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Homo" in data[0]["ortholog_species"]

    # Search for "cerevisiae" (partial match)
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&ortholog_species=cerevisiae"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "cerevisiae" in data[0]["ortholog_species"]


@pytest.mark.asyncio
async def test_filter_genes_combined_filters(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test combining multiple filters."""
    genes = [
        Gene(name="eco:b0001", description="gene 1", organism_id=sample_organism.id,
             ortholog_name="hsa:1", ortholog_species="Homo sapiens", ortholog_identity=85.0),
        Gene(name="eco:b0002", description="gene 2", organism_id=sample_organism.id,
             ortholog_name="hsa:2", ortholog_species="Homo sapiens", ortholog_identity=60.0),
        Gene(name="eco:b0003", description="gene 3", organism_id=sample_organism.id,
             ortholog_name="mmu:3", ortholog_species="Mus musculus", ortholog_identity=90.0),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Filter: human orthologs with >= 70% identity
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&ortholog_species=homo&min_identity=70.0"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1  # Only eco:b0001 (85% identity)
    assert data[0]["name"] == "eco:b0001"


# =============================================================================
# SORTING Tests
# =============================================================================


@pytest.mark.asyncio
async def test_sort_genes_by_name(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test sorting genes by name."""
    genes = [
        Gene(name="eco:b0003", description="gene 3", organism_id=sample_organism.id),
        Gene(name="eco:b0001", description="gene 1", organism_id=sample_organism.id),
        Gene(name="eco:b0002", description="gene 2", organism_id=sample_organism.id),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&sort_by=name&order=asc"
    )
    assert response.status_code == 200
    data = response.json()

    names = [gene["name"] for gene in data]
    assert names == ["eco:b0001", "eco:b0002", "eco:b0003"]


@pytest.mark.asyncio
async def test_sort_genes_by_identity(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test sorting genes by ortholog_identity."""
    genes = [
        Gene(name="eco:b0001", description="gene 1", organism_id=sample_organism.id,
             ortholog_name="a", ortholog_identity=50.0),
        Gene(name="eco:b0002", description="gene 2", organism_id=sample_organism.id,
             ortholog_name="b", ortholog_identity=95.0),
        Gene(name="eco:b0003", description="gene 3", organism_id=sample_organism.id,
             ortholog_name="c", ortholog_identity=75.0),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Sort by identity descending (highest first)
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&sort_by=ortholog_identity&order=desc"
    )
    assert response.status_code == 200
    data = response.json()

    identities = [gene["ortholog_identity"] for gene in data]
    assert identities == [95.0, 75.0, 50.0]


# =============================================================================
# UPDATE Tests - PUT /genes/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_update_gene_description(test_client: AsyncClient, sample_genes: list[Gene]):
    """Test updating gene description."""
    gene = sample_genes[0]

    response = await test_client.put(
        f"/api/genes/{gene.id}",
        json={"description": "Updated description"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["name"] == gene.name  # Name unchanged


@pytest.mark.asyncio
async def test_update_gene_add_ortholog_data(test_client: AsyncClient, sample_genes: list[Gene]):
    """Test adding ortholog data to a gene."""
    gene = sample_genes[0]

    response = await test_client.put(
        f"/api/genes/{gene.id}",
        json={
            "ortholog_name": "hsa:5236",
            "ortholog_description": "THRSP",
            "ortholog_species": "Homo sapiens",
            "ortholog_identity": 85.5,
            "ortholog_sw_score": 250
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ortholog_name"] == "hsa:5236"
    assert data["ortholog_identity"] == 85.5


@pytest.mark.asyncio
async def test_update_gene_invalid_identity(test_client: AsyncClient, sample_genes: list[Gene]):
    """Test updating gene with invalid ortholog_identity returns 422."""
    gene = sample_genes[0]

    response = await test_client.put(
        f"/api/genes/{gene.id}",
        json={"ortholog_identity": 150.0}  # Invalid: > 100%
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_gene_not_found(test_client: AsyncClient):
    """Test updating non-existent gene returns 404."""
    response = await test_client.put(
        "/api/genes/99999",
        json={"description": "New description"}
    )

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "GENE_NOT_FOUND"


# =============================================================================
# DELETE Tests - DELETE /genes/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_delete_gene(test_client: AsyncClient, sample_genes: list[Gene], db_session: AsyncSession):
    """Test deleting a gene."""
    gene = sample_genes[0]
    gene_id = gene.id

    response = await test_client.delete(f"/api/genes/{gene_id}")

    assert response.status_code == 204

    # Verify gene no longer exists
    result = await db_session.execute(
        select(Gene).where(Gene.id == gene_id)
    )
    deleted_gene = result.scalar_one_or_none()
    assert deleted_gene is None


@pytest.mark.asyncio
async def test_delete_gene_not_found(test_client: AsyncClient):
    """Test deleting non-existent gene returns 404."""
    response = await test_client.delete("/api/genes/99999")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "GENE_NOT_FOUND"


# =============================================================================
# PAGINATION Tests
# =============================================================================


@pytest.mark.asyncio
async def test_genes_pagination(test_client: AsyncClient, db_session: AsyncSession, sample_organism: Organism):
    """Test pagination (skip and limit)."""
    # Create 20 genes
    genes = [
        Gene(name=f"eco:b{i:04d}", description=f"gene {i}", organism_id=sample_organism.id)
        for i in range(20)
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Get first 5
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&limit=5&skip=0"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

    # Get next 5
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&limit=5&skip=5"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


# =============================================================================
# EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_gene_with_zero_identity(test_client: AsyncClient, sample_organism: Organism):
    """Test gene with 0% identity is valid."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0001",
            "description": "test",
            "organism_id": sample_organism.id,
            "ortholog_identity": 0.0  # Edge case: 0% is valid
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ortholog_identity"] == 0.0


@pytest.mark.asyncio
async def test_gene_with_100_percent_identity(test_client: AsyncClient, sample_organism: Organism):
    """Test gene with 100% identity is valid."""
    response = await test_client.post(
        "/api/genes",
        json={
            "name": "eco:b0001",
            "description": "test",
            "organism_id": sample_organism.id,
            "ortholog_identity": 100.0  # Edge case: 100% is valid
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ortholog_identity"] == 100.0


@pytest.mark.asyncio
async def test_filter_genes_no_results(test_client: AsyncClient, sample_organism: Organism):
    """Test filtering with no matching results returns empty list."""
    response = await test_client.get(
        f"/api/genes?organism_id={sample_organism.id}&ortholog_species=nonexistent"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
