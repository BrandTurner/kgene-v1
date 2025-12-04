# KEGG Explore API - Usage Guide

Complete guide for using the KEGG Explore backend API.

## Base URL

```
Development: http://localhost:8000
Production: https://api.kegg-explore.com
```

## Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs` (interactive testing)
- **ReDoc**: `http://localhost:8000/redoc` (pretty documentation)
- **OpenAPI JSON**: `http://localhost:8000/openapi.json` (API specification)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Error Handling](#error-handling)
3. [Organisms API](#organisms-api)
4. [Genes API](#genes-api)
5. [Processes API](#processes-api)
6. [CSV Export](#csv-export)
7. [Pagination & Filtering](#pagination--filtering)
8. [Common Workflows](#common-workflows)
9. [Rate Limiting](#rate-limiting)
10. [Code Examples](#code-examples)

---

## Authentication

**Current Version**: No authentication required (v2.0.0)

**Future**: Authentication will be added in v3.0.0 using JWT tokens.

---

## Error Handling

All errors return JSON with correlation ID for tracking.

### Error Response Format

```json
{
  "code": "ORGANISM_NOT_FOUND",
  "message": "Organism with id 123 not found",
  "timestamp": "2025-12-02T12:00:00Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "organism_id": 123
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Meaning |
|-------------|------------|---------|
| 400 | `DUPLICATE_ORGANISM` | Organism code already exists |
| 400 | `DUPLICATE_ENTRY` | Database integrity violation |
| 404 | `ORGANISM_NOT_FOUND` | Organism doesn't exist |
| 404 | `GENE_NOT_FOUND` | Gene doesn't exist |
| 404 | `PROCESS_NOT_FOUND` | Process/job doesn't exist |
| 422 | `VALIDATION_ERROR` | Invalid input data |
| 500 | `INTERNAL_ERROR` | Server error (contact support) |

---

## Organisms API

Manage organisms (species) in the database.

### List Organisms

**`GET /api/organisms`**

Retrieve all organisms with optional filtering and sorting.

**Query Parameters**:
- `status` (string): Filter by status (`pending`, `complete`, `error`)
- `code_pattern` (string): Filter by code (partial match, case-insensitive)
- `name_pattern` (string): Filter by name (partial match)
- `created_after` (datetime): Filter by creation date
- `created_before` (datetime): Filter by creation date
- `sort_by` (string): Sort field (`name`, `code`, `created_at`, `updated_at`)
- `order` (string): Sort order (`asc`, `desc`)
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Max results (default: 100, max: 1000)

**Example Request**:
```bash
curl "http://localhost:8000/api/organisms?status=complete&sort_by=name&order=asc"
```

**Example Response**:
```json
[
  {
    "id": 1,
    "code": "eco",
    "name": "Escherichia coli K-12 MG1655",
    "status": "complete",
    "job_id": "abc123",
    "job_error": null,
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-01T10:30:00Z"
  }
]
```

### Get Single Organism

**`GET /api/organisms/{organism_id}`**

**Example**:
```bash
curl http://localhost:8000/api/organisms/1
```

### Create Organism

**`POST /api/organisms`**

**Request Body**:
```json
{
  "code": "eco",
  "name": "Escherichia coli K-12 MG1655"
}
```

**Validation Rules**:
- `code`: 3-4 lowercase letters only (e.g., "eco", "hsa")
- `name`: 1-200 characters

**Example**:
```bash
curl -X POST http://localhost:8000/api/organisms \
  -H "Content-Type: application/json" \
  -d '{"code":"hsa","name":"Homo sapiens"}'
```

### Update Organism

**`PUT /api/organisms/{organism_id}`**

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "status": "complete"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/api/organisms/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"complete"}'
```

### Delete Organism

**`DELETE /api/organisms/{organism_id}`**

**Example**:
```bash
curl -X DELETE http://localhost:8000/api/organisms/1
```

---

## Genes API

Manage genes and ortholog data.

### List Genes

**`GET /api/genes`**

**Bioinformatics-Focused Filters**:
- `organism_id` (int): Filter by organism
- `has_ortholog` (bool): Filter by ortholog presence (`true`=has, `false`=orphan)
- `min_identity` (float): Minimum ortholog identity % (0-100)
- `max_identity` (float): Maximum ortholog identity % (0-100)
- `ortholog_species` (string): Filter by ortholog species (partial match)
- `sort_by` (string): Sort field (`name`, `ortholog_identity`, `ortholog_sw_score`, `created_at`)
- `order` (string): Sort order
- `skip`, `limit`: Pagination

**Examples**:

```bash
# Get all genes for organism 1
curl "http://localhost:8000/api/genes?organism_id=1"

# Get orphan genes (no orthologs found)
curl "http://localhost:8000/api/genes?organism_id=1&has_ortholog=false"

# Get high-confidence orthologs (>70% identity)
curl "http://localhost:8000/api/genes?organism_id=1&min_identity=70.0&sort_by=ortholog_identity&order=desc"

# Get genes with human orthologs
curl "http://localhost:8000/api/genes?organism_id=1&ortholog_species=Homo sapiens"
```

**Response**:
```json
[
  {
    "id": 1,
    "name": "eco:b0001",
    "description": "CDS 190..255 thrL; thr operon leader peptide",
    "organism_id": 1,
    "ortholog_name": "hsa:5236",
    "ortholog_description": "THRSP",
    "ortholog_species": "Homo sapiens",
    "ortholog_length": 450,
    "ortholog_sw_score": 250,
    "ortholog_identity": 85.5,
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-01T10:30:00Z"
  }
]
```

### Get Single Gene

**`GET /api/genes/{gene_id}`**

### Create Gene

**`POST /api/genes`**

**Request Body**:
```json
{
  "name": "eco:b0001",
  "description": "Gene description",
  "organism_id": 1,
  "ortholog_name": "hsa:5236",
  "ortholog_description": "Human ortholog",
  "ortholog_species": "Homo sapiens",
  "ortholog_length": 450,
  "ortholog_sw_score": 250,
  "ortholog_identity": 85.5
}
```

**Validation**:
- `ortholog_identity`: Must be 0.0-100.0
- `ortholog_sw_score`: Must be >= 0
- `ortholog_length`: Must be >= 0

### Update Gene

**`PUT /api/genes/{gene_id}`**

### Delete Gene

**`DELETE /api/genes/{gene_id}`**

---

## Processes API

Manage background jobs for gene fetching and ortholog discovery.

### Start Processing Job

**`POST /api/processes`**

Starts background job to fetch genes and discover orthologs.

**Request Body**:
```json
{
  "organism_id": 1
}
```

**Response**:
```json
{
  "job_id": "abc123-def456-789",
  "organism_id": 1,
  "status": "pending",
  "message": "Job started successfully"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/processes \
  -H "Content-Type: application/json" \
  -d '{"organism_id":1}'
```

### Check Job Progress

**`GET /api/processes/{organism_id}/progress`**

**Response**:
```json
{
  "organism_id": 1,
  "status": "pending",
  "progress": {
    "current": 1500,
    "total": 4600,
    "percentage": 32.6
  },
  "job_id": "abc123",
  "started_at": "2025-12-01T10:00:00Z",
  "estimated_completion": "2025-12-01T10:25:00Z"
}
```

**Example**:
```bash
# Poll for progress
while true; do
  curl http://localhost:8000/api/processes/1/progress | jq .
  sleep 5
done
```

### List All Processes

**`GET /api/processes`**

Returns all organisms with their processing status and progress.

---

## CSV Export

Export gene data to CSV format for analysis in Excel, R, Python, etc.

### Export Organism Genes

**`GET /api/processes/{organism_id}/download`**

Download all genes for an organism.

**Query Parameters**:
- `include_no_orthologs` (bool): Include orphan genes (default: `true`)

**CSV Format**:
```
gene_name,gene_description,ortholog_name,ortholog_description,ortholog_species,ortholog_length,ortholog_sw_score,ortholog_identity
eco:b0001,thrL; thr operon leader peptide,hsa:5236,THRSP,Homo sapiens,450,250,85.50
```

**Examples**:

```bash
# Download all genes (including orphans)
curl "http://localhost:8000/api/processes/1/download" -o eco_genes.csv

# Download only genes WITH orthologs
curl "http://localhost:8000/api/processes/1/download?include_no_orthologs=false" -o eco_orthologs_only.csv
```

### Export Filtered Genes

**`GET /api/genes/export`**

Export genes with same filtering as `/api/genes`.

**Query Parameters**: Same as `/api/genes`

**Examples**:

```bash
# Export high-confidence human orthologs
curl "http://localhost:8000/api/genes/export?organism_id=1&ortholog_species=homo&min_identity=70.0" -o high_conf_human.csv

# Export orphan genes only
curl "http://localhost:8000/api/genes/export?organism_id=1&has_ortholog=false" -o orphan_genes.csv
```

---

## Pagination & Filtering

### Pagination

All list endpoints support pagination:

```bash
# Get first 50 results
curl "http://localhost:8000/api/genes?organism_id=1&limit=50&skip=0"

# Get next 50 results
curl "http://localhost:8000/api/genes?organism_id=1&limit=50&skip=50"
```

### Filtering Best Practices

**Combine multiple filters**:
```bash
# High-confidence human orthologs created this week
curl "http://localhost:8000/api/genes?organism_id=1&ortholog_species=homo&min_identity=80&created_after=2025-11-25"
```

**Use sorting for top results**:
```bash
# Top 10 highest identity orthologs
curl "http://localhost:8000/api/genes?organism_id=1&sort_by=ortholog_identity&order=desc&limit=10"
```

---

## Common Workflows

### Workflow 1: Process New Organism

```bash
# 1. Create organism
ORGANISM_ID=$(curl -s -X POST http://localhost:8000/api/organisms \
  -H "Content-Type: application/json" \
  -d '{"code":"eco","name":"E. coli"}' | jq -r '.id')

# 2. Start processing job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/processes \
  -H "Content-Type: application/json" \
  -d "{\"organism_id\":$ORGANISM_ID}" | jq -r '.job_id')

# 3. Monitor progress
while true; do
  STATUS=$(curl -s http://localhost:8000/api/processes/$ORGANISM_ID/progress | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "complete" ] && break
  sleep 10
done

# 4. Download results
curl "http://localhost:8000/api/processes/$ORGANISM_ID/download" -o genes.csv
```

### Workflow 2: Find Conserved Genes

Find genes with high ortholog identity across species.

```bash
# Find genes with >90% identity
curl "http://localhost:8000/api/genes?organism_id=1&min_identity=90.0&sort_by=ortholog_identity&order=desc" | jq .

# Export for analysis
curl "http://localhost:8000/api/genes/export?organism_id=1&min_identity=90.0" -o conserved_genes.csv
```

### Workflow 3: Study Orphan Genes

Find species-specific genes (no orthologs found).

```bash
# Count orphan genes
curl "http://localhost:8000/api/genes?organism_id=1&has_ortholog=false" | jq 'length'

# Export orphan genes
curl "http://localhost:8000/api/genes/export?organism_id=1&has_ortholog=false" -o orphan_genes.csv
```

---

## Rate Limiting

**Current**: 100 requests/minute per IP (configurable)

**Headers**:
- `X-RateLimit-Limit`: Total requests allowed per minute
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

**429 Response** (Rate Limit Exceeded):
```json
{
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Try again in 30 seconds.",
  "retry_after": 30
}
```

---

## Code Examples

### Python (requests)

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# Create organism
response = requests.post(f"{BASE_URL}/api/organisms", json={
    "code": "eco",
    "name": "Escherichia coli K-12 MG1655"
})
organism = response.json()
organism_id = organism["id"]

# Start processing
response = requests.post(f"{BASE_URL}/api/processes", json={
    "organism_id": organism_id
})
job = response.json()

# Monitor progress
while True:
    response = requests.get(f"{BASE_URL}/api/processes/{organism_id}/progress")
    progress = response.json()

    print(f"Status: {progress['status']} - {progress['progress']['percentage']:.1f}%")

    if progress["status"] == "complete":
        break
    elif progress["status"] == "error":
        print(f"Error: {progress.get('error')}")
        break

    time.sleep(5)

# Download CSV
response = requests.get(f"{BASE_URL}/api/processes/{organism_id}/download")
with open("genes.csv", "wb") as f:
    f.write(response.content)
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:8000";

// Create organism
const createOrganism = async () => {
  const response = await fetch(`${BASE_URL}/api/organisms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: "eco",
      name: "Escherichia coli K-12 MG1655"
    })
  });
  return await response.json();
};

// Start processing
const startProcessing = async (organismId) => {
  const response = await fetch(`${BASE_URL}/api/processes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ organism_id: organismId })
  });
  return await response.json();
};

// Monitor progress
const monitorProgress = async (organismId) => {
  while (true) {
    const response = await fetch(`${BASE_URL}/api/processes/${organismId}/progress`);
    const progress = await response.json();

    console.log(`Status: ${progress.status} - ${progress.progress.percentage}%`);

    if (progress.status === "complete") {
      break;
    }

    await new Promise(resolve => setTimeout(resolve, 5000));
  }
};

// Usage
const organism = await createOrganism();
await startProcessing(organism.id);
await monitorProgress(organism.id);
```

### cURL Scripts

**Bash Script** (`process_organism.sh`):

```bash
#!/bin/bash
set -e

ORGANISM_CODE=${1:-eco}
ORGANISM_NAME=${2:-"Escherichia coli"}
API_URL="http://localhost:8000"

echo "Creating organism: $ORGANISM_CODE"
RESPONSE=$(curl -s -X POST "$API_URL/api/organisms" \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"$ORGANISM_CODE\",\"name\":\"$ORGANISM_NAME\"}")

ORGANISM_ID=$(echo $RESPONSE | jq -r '.id')
echo "Organism ID: $ORGANISM_ID"

echo "Starting processing job..."
curl -s -X POST "$API_URL/api/processes" \
  -H "Content-Type: application/json" \
  -d "{\"organism_id\":$ORGANISM_ID}" | jq .

echo "Monitoring progress..."
while true; do
  PROGRESS=$(curl -s "$API_URL/api/processes/$ORGANISM_ID/progress")
  STATUS=$(echo $PROGRESS | jq -r '.status')
  PERCENT=$(echo $PROGRESS | jq -r '.progress.percentage')

  echo "Status: $STATUS ($PERCENT%)"

  [ "$STATUS" = "complete" ] && break
  [ "$STATUS" = "error" ] && echo "Error occurred!" && exit 1

  sleep 10
done

echo "Downloading results..."
curl -s "$API_URL/api/processes/$ORGANISM_ID/download" -o "${ORGANISM_CODE}_genes.csv"
echo "Done! Results saved to ${ORGANISM_CODE}_genes.csv"
```

Usage:
```bash
chmod +x process_organism.sh
./process_organism.sh eco "Escherichia coli K-12 MG1655"
```

---

## Support

- **API Docs**: http://localhost:8000/docs (interactive)
- **Deployment Guide**: See `DEPLOYMENT.md`
- **Quick Start**: See `QUICKSTART.md`
- **Issues**: Report bugs on GitHub

---

**Happy API exploring! 🧬**
