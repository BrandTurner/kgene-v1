"""
Comprehensive Tests for CSV Export Endpoints

Tests cover:
- Organism gene download (GET /processes/{organism_id}/download)
- Filtered gene export (GET /genes/export)
- CSV format validation
- Filtering options
- Edge cases (empty results, orphan genes)
"""

import pytest
import csv
import io
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organism import Organism
from app.models.gene import Gene


# =============================================================================
# Helper Functions
# =============================================================================


def parse_csv_response(csv_content: str) -> list[dict]:
    """Parse CSV content into list of dictionaries."""
    reader = csv.DictReader(io.StringIO(csv_content))
    return list(reader)


# =============================================================================
# Organism Download Tests - GET /processes/{organism_id}/download
# =============================================================================


@pytest.mark.asyncio
async def test_download_organism_genes_success(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test downloading genes for an organism as CSV."""
    # Add genes with orthologs
    genes = [
        Gene(
            name="eco:b0001",
            description="thrL; thr operon leader peptide",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1234",
            ortholog_description="Human ortholog",
            ortholog_species="Homo sapiens",
            ortholog_length=450,
            ortholog_sw_score=250,
            ortholog_identity=85.5
        ),
        Gene(
            name="eco:b0002",
            description="thrA; aspartokinase",
            organism_id=sample_organism.id,
            ortholog_name="mmu:5678",
            ortholog_description="Mouse ortholog",
            ortholog_species="Mus musculus",
            ortholog_length=420,
            ortholog_sw_score=230,
            ortholog_identity=90.0
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Download CSV
    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download?include_no_orthologs=true"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert "eco_genes.csv" in response.headers["content-disposition"]

    # Parse CSV
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 2

    # Verify first gene
    row = csv_data[0]
    assert row["gene_name"] == "eco:b0001"
    assert row["ortholog_name"] == "hsa:1234"
    assert row["ortholog_species"] == "Homo sapiens"
    assert row["ortholog_identity"] == "85.50"


@pytest.mark.asyncio
async def test_download_organism_genes_with_orphans(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test downloading includes orphan genes (genes without orthologs)."""
    genes = [
        Gene(
            name="eco:b0001",
            description="gene with ortholog",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1234",
            ortholog_identity=85.0
        ),
        Gene(
            name="eco:b0002",
            description="orphan gene",
            organism_id=sample_organism.id,
            ortholog_name=None  # NO ortholog
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Download with orphans included
    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download?include_no_orthologs=true"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 2

    # Verify orphan gene has empty ortholog fields
    orphan = next(row for row in csv_data if row["gene_name"] == "eco:b0002")
    assert orphan["ortholog_name"] == ""
    assert orphan["ortholog_species"] == ""
    assert orphan["ortholog_identity"] == ""


@pytest.mark.asyncio
async def test_download_organism_genes_exclude_orphans(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test downloading excludes orphan genes when include_no_orthologs=false."""
    genes = [
        Gene(
            name="eco:b0001",
            description="gene with ortholog",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1234",
            ortholog_identity=85.0
        ),
        Gene(
            name="eco:b0002",
            description="orphan gene",
            organism_id=sample_organism.id,
            ortholog_name=None
        ),
        Gene(
            name="eco:b0003",
            description="another orphan",
            organism_id=sample_organism.id,
            ortholog_name=None
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Download without orphans
    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download?include_no_orthologs=false"
    )

    assert response.status_code == 200
    assert "orthologs_only.csv" in response.headers["content-disposition"]

    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 1  # Only gene with ortholog
    assert csv_data[0]["gene_name"] == "eco:b0001"


@pytest.mark.asyncio
async def test_download_organism_not_found(test_client: AsyncClient):
    """Test downloading for non-existent organism returns 404."""
    response = await test_client.get("/api/processes/99999/download")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "ORGANISM_NOT_FOUND"


@pytest.mark.asyncio
async def test_download_empty_organism(
    test_client: AsyncClient,
    sample_organism: Organism
):
    """Test downloading organism with no genes returns empty CSV (header only)."""
    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 0  # No genes


@pytest.mark.asyncio
async def test_download_csv_header_format(
    test_client: AsyncClient,
    sample_organism: Organism
):
    """Test CSV has correct header columns."""
    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download"
    )

    assert response.status_code == 200

    # Check header row
    lines = response.text.split("\n")
    header = lines[0]

    expected_columns = [
        "gene_name",
        "gene_description",
        "ortholog_name",
        "ortholog_description",
        "ortholog_species",
        "ortholog_length",
        "ortholog_sw_score",
        "ortholog_identity"
    ]

    for column in expected_columns:
        assert column in header


# =============================================================================
# Filtered Export Tests - GET /genes/export
# =============================================================================


@pytest.mark.asyncio
async def test_export_filtered_genes(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test exporting filtered genes to CSV."""
    genes = [
        Gene(
            name="eco:b0001",
            description="high identity",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1",
            ortholog_species="Homo sapiens",
            ortholog_identity=95.0
        ),
        Gene(
            name="eco:b0002",
            description="low identity",
            organism_id=sample_organism.id,
            ortholog_name="hsa:2",
            ortholog_species="Homo sapiens",
            ortholog_identity=50.0
        ),
        Gene(
            name="eco:b0003",
            description="mouse ortholog",
            organism_id=sample_organism.id,
            ortholog_name="mmu:3",
            ortholog_species="Mus musculus",
            ortholog_identity=85.0
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Export only high-confidence human orthologs (>= 70%)
    response = await test_client.get(
        f"/api/genes/export?organism_id={sample_organism.id}"
        "&ortholog_species=homo&min_identity=70.0"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 1
    assert csv_data[0]["gene_name"] == "eco:b0001"
    assert csv_data[0]["ortholog_identity"] == "95.00"


@pytest.mark.asyncio
async def test_export_orphan_genes_only(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test exporting only orphan genes (has_ortholog=false)."""
    genes = [
        Gene(
            name="eco:b0001",
            description="has ortholog",
            organism_id=sample_organism.id,
            ortholog_name="hsa:1",
            ortholog_identity=85.0
        ),
        Gene(
            name="eco:b0002",
            description="orphan 1",
            organism_id=sample_organism.id,
            ortholog_name=None
        ),
        Gene(
            name="eco:b0003",
            description="orphan 2",
            organism_id=sample_organism.id,
            ortholog_name=None
        ),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Export only orphan genes
    response = await test_client.get(
        f"/api/genes/export?organism_id={sample_organism.id}&has_ortholog=false"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 2
    assert all(row["ortholog_name"] == "" for row in csv_data)


@pytest.mark.asyncio
async def test_export_genes_with_identity_range(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test exporting genes within identity range."""
    genes = [
        Gene(name="eco:b0001", description="low", organism_id=sample_organism.id,
             ortholog_name="a", ortholog_identity=40.0),
        Gene(name="eco:b0002", description="medium", organism_id=sample_organism.id,
             ortholog_name="b", ortholog_identity=70.0),
        Gene(name="eco:b0003", description="high", organism_id=sample_organism.id,
             ortholog_name="c", ortholog_identity=95.0),
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Export genes with 60-80% identity
    response = await test_client.get(
        f"/api/genes/export?organism_id={sample_organism.id}"
        "&min_identity=60.0&max_identity=80.0"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 1
    assert csv_data[0]["gene_name"] == "eco:b0002"


@pytest.mark.asyncio
async def test_export_genes_limit(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test export respects limit parameter."""
    # Create 20 genes
    genes = [
        Gene(
            name=f"eco:b{i:04d}",
            description=f"gene {i}",
            organism_id=sample_organism.id,
            ortholog_name=f"hsa:{i}",
            ortholog_identity=80.0
        )
        for i in range(20)
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Export with limit=5
    response = await test_client.get(
        f"/api/genes/export?organism_id={sample_organism.id}&limit=5"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 5


@pytest.mark.asyncio
async def test_export_no_results(
    test_client: AsyncClient,
    sample_organism: Organism
):
    """Test exporting with filter that matches no genes returns empty CSV."""
    response = await test_client.get(
        f"/api/genes/export?organism_id={sample_organism.id}"
        "&ortholog_species=nonexistent"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 0  # No genes match


# =============================================================================
# CSV Format Validation
# =============================================================================


@pytest.mark.asyncio
async def test_csv_special_characters(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test CSV properly escapes special characters (commas, quotes)."""
    gene = Gene(
        name="eco:b0001",
        description='Gene with "quotes" and, commas',
        organism_id=sample_organism.id,
        ortholog_description='Ortholog with "special" chars, and commas'
    )
    db_session.add(gene)
    await db_session.commit()

    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)

    # CSV parser should handle special characters correctly
    assert csv_data[0]["gene_description"] == 'Gene with "quotes" and, commas'


@pytest.mark.asyncio
async def test_csv_numeric_formatting(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test numeric fields are properly formatted in CSV."""
    gene = Gene(
        name="eco:b0001",
        description="test",
        organism_id=sample_organism.id,
        ortholog_name="hsa:1",
        ortholog_length=450,
        ortholog_sw_score=250,
        ortholog_identity=85.555  # Should round to 2 decimals
    )
    db_session.add(gene)
    await db_session.commit()

    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)

    row = csv_data[0]
    assert row["ortholog_length"] == "450"
    assert row["ortholog_sw_score"] == "250"
    # Identity should be formatted to 2 decimal places
    assert row["ortholog_identity"] == "85.56"


# =============================================================================
# Performance / Large Dataset Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_large_dataset(
    test_client: AsyncClient,
    db_session: AsyncSession,
    sample_organism: Organism
):
    """Test exporting large number of genes (streaming works correctly)."""
    # Create 500 genes
    genes = [
        Gene(
            name=f"eco:b{i:04d}",
            description=f"gene {i}",
            organism_id=sample_organism.id,
            ortholog_name=f"hsa:{i}",
            ortholog_species="Homo sapiens",
            ortholog_identity=float(i % 100)
        )
        for i in range(500)
    ]
    db_session.add_all(genes)
    await db_session.commit()

    # Download should work without memory issues (streaming)
    response = await test_client.get(
        f"/api/processes/{sample_organism.id}/download"
    )

    assert response.status_code == 200
    csv_data = parse_csv_response(response.text)
    assert len(csv_data) == 500
