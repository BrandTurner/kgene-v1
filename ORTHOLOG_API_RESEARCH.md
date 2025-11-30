# Ortholog API Research & Recommendations

**Research Date:** November 2024
**Purpose:** Find the best API for discovering gene orthologs across species to replace KEGG SSDB web scraping

---

## Quick Bioinformatics Primer

**What are Orthologs?**
- **Orthologs** are genes in different species that evolved from a common ancestral gene
- Example: Human insulin gene and mouse insulin gene are orthologs
- They typically have the same function across species
- Used to transfer functional knowledge between organisms

**Why Find Orthologs?**
- Predict gene function in newly sequenced genomes
- Study evolutionary relationships
- Identify drug targets that work across species
- Understand disease mechanisms using model organisms

---

## Executive Summary

### MVP Strategy (Phase 2-3)
**Primary:** KEGG KO (KEGG Orthology) API
**Fallback:** OMA Browser API (if needed for genes without KO assignments)

### Post-MVP Enhancement (Pinned for Later)
**Tiered quality-based cascading:**
1. Try KEGG KO API first
2. If ortholog quality < threshold → Try OMA Browser
3. If still < threshold → Try eggNOG
4. If still < threshold → Try OrthoDB
5. Track which API found each ortholog for transparency

**Quality Thresholds (to be defined):**
- Sequence identity % (e.g., minimum 40%)
- E-value or orthology confidence score
- Phylogenetic distance considerations

---

## Detailed API Comparison

### 1. KEGG Orthology (KO) API ⭐ RECOMMENDED FOR MVP

**Website:** https://rest.kegg.jp/
**Documentation:** https://www.kegg.jp/kegg/rest/keggapi.html

**What is KEGG KO?**
- **KO = KEGG Orthology**
- A database of functional orthologs (genes with same function across species)
- Each KO group has a "K number" (e.g., K12524)
- 27,293 orthology groups currently
- Manually curated by KEGG experts

**How It Works:**
1. Multiple genes from different species → Grouped into one KO (K number)
2. All genes in same KO → Perform similar molecular function
3. Example: K12524 = "fused aspartate kinase" found in bacteria, plants, etc.

**Pros:**
- ✅ Already integrated in our KEGG client
- ✅ Free for academic use
- ✅ Same rate limits as gene fetching (3 req/sec)
- ✅ No authentication required
- ✅ Simple TSV response format
- ✅ Well-documented REST API

**Cons:**
- ❌ Only ~73% of genes have KO assignments (tested with E. coli)
- ❌ Doesn't provide "best-best" ortholog pairs directly
- ❌ Requires logic to select the "best" ortholog from KO group
- ❌ Some genes have multiple KO assignments (need to handle)

**Coverage Test Results:**
- E. coli (eco): 3,392 out of 4,639 genes (73%) have KO mappings
- Missing 27% will need fallback strategy

**API Endpoints:**
```bash
# Get KO assignments for all genes in an organism
GET https://rest.kegg.jp/link/ko/{organism_code}
Response: gene_id\tko_id (TSV format)

# Get all genes assigned to a specific KO
GET https://rest.kegg.jp/link/{ko_id}/genes
Response: ko_id\tgene_id (TSV format)

# Example workflow:
# 1. GET /link/ko/eco → Find KO for eco:b0002
# 2. Result: eco:b0002 → ko:K12524
# 3. GET /link/K12524/genes → Get all genes in K12524
# 4. Filter out eco genes → Get orthologs from other species
```

**Implementation Strategy:**
```python
# For each gene:
# 1. Get its KO assignment(s) from /link/ko/{organism}
# 2. For each KO, get all genes in that KO from /link/{ko}/genes
# 3. Filter out genes from same organism
# 4. Select "best" ortholog based on:
#    - Different species (exclude self)
#    - Evolutionary distance (prefer distant species)
#    - Organism quality/model organism status
# 5. Store ortholog data
```

**Sources:**
- [KO Database](https://www.genome.jp/kegg/ko.html)
- [KEGG API Manual](https://www.kegg.jp/kegg/rest/keggapi.html)
- [KEGG Orthology Research Paper](https://academic.oup.com/bioinformatics/article/21/19/3787/210373)

---

### 2. OMA Browser API ⭐ RECOMMENDED FALLBACK FOR MVP

**Website:** https://omabrowser.org/
**API Docs:** https://omabrowser.org/api/docs

**What is OMA?**
- **OMA = Orthologous Matrix**
- Algorithm-based orthology predictions (not manual curation)
- Provides **pairwise orthologs** (gene A in species 1 ↔ gene B in species 2)
- Also provides **HOGs** (Hierarchical Orthologous Groups - similar to KO but hierarchical)

**Pros:**
- ✅ Excellent REST API with comprehensive documentation
- ✅ 2024 updates with improved prokaryote coverage
- ✅ Provides **pairwise orthologs directly** (easier than KO groups)
- ✅ Hierarchical Orthologous Groups (HOGs) available
- ✅ Free and open access, no API key required
- ✅ R and Python packages available (OmaDB)
- ✅ Pagination support for large datasets
- ✅ Returns confidence scores for orthology predictions

**Cons:**
- ❌ Additional API to integrate (different endpoints, rate limits)
- ❌ May not cover all KEGG organisms
- ❌ KEGG gene IDs may need mapping to OMA identifiers

**Gene ID Mapping Challenge:**
- KEGG uses IDs like `hsa:10458`
- OMA uses different identifiers (UniProt-based)
- May need KEGG → UniProt → OMA mapping
- KEGG provides `/conv` endpoint for ID conversion

**Implementation Strategy:**
```python
# For genes without KO assignments (~27%):
# 1. Convert KEGG gene ID → UniProt ID (via KEGG /conv endpoint)
# 2. Query OMA API with UniProt ID
# 3. Get pairwise orthologs with confidence scores
# 4. Filter for best ortholog (highest confidence, different species)
# 5. Store ortholog data
```

**Sources:**
- [OMA Browser](https://omabrowser.org/oma/home/)
- [REST API Documentation](https://omabrowser.org/api/docs)
- [2024 OMA Update Paper](https://academic.oup.com/nar/article/52/D1/D513/7420097)
- [Programmatic Interfaces Paper](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6464060/)

---

### 3. eggNOG API 📌 PINNED FOR POST-MVP

**Website:** http://eggnog5.embl.de/
**Mapper:** http://eggnog-mapper.embl.de/

**What is eggNOG?**
- **eggNOG = evolutionary genealogy of genes: Non-supervised Orthologous Groups**
- Builds on original COGs (Clusters of Orthologous Groups) concept
- Uses phylogenetic trees to define ortholog groups
- Includes functional annotations alongside orthology

**Pros:**
- ✅ Massive coverage: 5,090 organisms + 2,502 viruses (as of v5.0)
- ✅ RESTful web service available
- ✅ Provides **functional annotations** alongside orthologs
- ✅ Phylogenetically annotated (knows evolutionary relationships)
- ✅ Free and open access
- ✅ Good for viral and prokaryotic genomes

**Cons:**
- ❌ API documentation not as comprehensive as OMA
- ❌ Primarily designed for functional annotation workflow
- ❌ Pairwise ortholog queries less straightforward
- ❌ May require sequence-based queries (not just gene IDs)
- ❌ Last major version was 2019 (v5.0)

**Use Case for Post-MVP:**
- Third-tier fallback when KEGG KO and OMA don't find high-quality orthologs
- Particularly useful for viral genes or poorly characterized organisms

**Sources:**
- [eggNOG 5.0 Paper](https://academic.oup.com/nar/article/47/D1/D309/5173662)
- [eggNOG Database](http://eggnog5.embl.de/)
- [eggNOG-mapper GitHub](https://github.com/eggnogdb/eggnog-mapper)

---

### 4. OrthoDB API 📌 PINNED FOR POST-MVP

**Website:** https://www.orthodb.org/
**User Guide:** https://www.ezlab.org/orthodb_v12_userguide.html

**What is OrthoDB?**
- Database of orthologous groups across species
- Version 12 (latest) has massive genome coverage
- Provides ortholog groups at different taxonomic levels
- Used by BUSCO (Benchmarking Universal Single-Copy Orthologs)

**Pros:**
- ✅ **Massive coverage:** 5,827 genomes, 162 million genes (v12, 2024)
- ✅ REST API and SPARQL/RDF access
- ✅ Python wrapper (OrthoDB-py)
- ✅ Nearly tripled Eukaryote coverage in v12
- ✅ Interactive web interface
- ✅ Free and open access
- ✅ Excellent for eukaryotic genomes

**Cons:**
- ❌ API documentation less comprehensive than OMA
- ❌ Integration examples are older (references to v9 found)
- ❌ May require sequence-based mapping
- ❌ Less clear integration path compared to KEGG/OMA

**Use Case for Post-MVP:**
- Fourth-tier fallback for maximum coverage
- Particularly strong for eukaryotic organisms
- Could fill gaps where other databases have low confidence

**Sources:**
- [OrthoDB 2024 Update](https://pmc.ncbi.nlm.nih.gov/articles/PMC11701741/)
- [OrthoDB Database](https://www.orthodb.org/)
- [OrthoDB User Guide](https://www.ezlab.org/orthodb_v12_userguide.html)

---

## Comparison: Web Scraping vs. API Approaches

### Original Approach (Rails App - 2015)

**Method:** Web scrape KEGG SSDB (Sequence Similarity Database) pages
**URL:** `https://www.kegg.jp/ssdb-bin/ssdb_best_best?org_gene={gene_name}`

**What is SSDB?**
- **SSDB = Sequence Similarity Database**
- Contains pre-computed sequence similarity scores between genes
- **Best-best ortholog** = genes that are each other's best match across species
- Example: Human gene X's best match is mouse gene Y, AND mouse gene Y's best match is human gene X

**What the scraper did:**
1. Request SSDB page for each gene
2. Parse HTML `<pre>` table
3. Extract best non-self ortholog match
4. Get metrics: SW score (Smith-Waterman alignment score), identity %, length

**Problems with Web Scraping:**
- 🔴 **Fragile** - HTML structure changes break the scraper
- 🔴 **Rate limiting** - Easy to exceed limits
- 🔴 **No official support** - Could be blocked anytime
- 🔴 **Parsing complexity** - Error-prone HTML parsing
- 🔴 **Maintenance burden** - Requires constant monitoring

**Advantages (why it was used):**
- ✅ Provides "best-best" ortholog directly
- ✅ Includes detailed similarity metrics (SW score, identity %, length)
- ✅ Simple one-to-one mapping (gene → best ortholog)

---

## Recommended Implementation Phases

### Phase 2-3: MVP Implementation

#### Step 1: KEGG KO Primary Source (~73% coverage)

**File:** `backend/app/services/ortholog_service.py`

```python
async def find_ortholog_via_ko(
    gene_id: str,
    organism_code: str
) -> Optional[OrthologResult]:
    """
    Find ortholog using KEGG KO API.

    Bioinformatics Concept:
    - Genes in the same KO group perform the same molecular function
    - We find other genes in the same KO from different organisms
    - Select the "best" one based on evolutionary distance and quality

    Steps:
    1. Get KO assignment(s) for this gene
    2. For each KO, get all genes in that KO from other organisms
    3. Filter out same-organism genes
    4. Rank remaining orthologs by:
       - Evolutionary distance (prefer distant species like human/fly)
       - Model organism status (prefer well-studied species)
    5. Return top ortholog with metadata
    """
```

**Expected Coverage:** ~73% (based on E. coli test)

#### Step 2: OMA Fallback (Optional - if 27% gap is problematic)

**File:** `backend/app/services/ortholog_service.py`

```python
async def find_ortholog_via_oma(gene_id: str) -> Optional[OrthologResult]:
    """
    Find ortholog using OMA Browser API.

    Used for genes without KO assignments (~27%).

    Steps:
    1. Convert KEGG gene ID → UniProt ID (if needed)
    2. Query OMA API for pairwise orthologs
    3. Get confidence scores for each ortholog pair
    4. Filter and rank by confidence + evolutionary distance
    5. Return best ortholog
    """
```

**Combined Coverage:** ~95%+ (estimate)

### Post-MVP: Quality-Based Tiered Cascading

#### Enhancement: Multi-API Fallback with Quality Thresholds

**File:** `backend/app/services/ortholog_service.py`

```python
async def find_best_ortholog(
    gene_id: str,
    organism_code: str,
    quality_threshold: float = 40.0  # minimum % identity
) -> OrthologResult:
    """
    Try multiple ortholog databases with quality-based cascading.

    Tries APIs in order until high-quality ortholog found:
    1. KEGG KO API (fastest, already integrated)
    2. OMA Browser API (good coverage, pairwise orthologs)
    3. eggNOG API (excellent for prokaryotes/viruses)
    4. OrthoDB API (maximum coverage, especially eukaryotes)

    Quality Metrics:
    - Sequence identity % (e.g., >40% = high quality)
    - E-value (if available)
    - Orthology confidence score
    - Phylogenetic distance score

    Returns:
    - OrthologResult with:
        - ortholog_gene_id
        - ortholog_species
        - quality_score
        - data_source (which API found it)
        - confidence_metrics
    """

    # Try KEGG KO first
    result = await find_ortholog_via_ko(gene_id, organism_code)
    if result and result.quality_score >= quality_threshold:
        result.data_source = "KEGG_KO"
        return result

    # Try OMA if KO failed or low quality
    result = await find_ortholog_via_oma(gene_id)
    if result and result.quality_score >= quality_threshold:
        result.data_source = "OMA"
        return result

    # Try eggNOG if still no high-quality match
    result = await find_ortholog_via_eggnog(gene_id)
    if result and result.quality_score >= quality_threshold:
        result.data_source = "eggNOG"
        return result

    # Last resort: OrthoDB
    result = await find_ortholog_via_orthodb(gene_id)
    if result:
        result.data_source = "OrthoDB"
        return result

    # No ortholog found in any database
    return None
```

**Benefits:**
- Maximum coverage across all databases
- Quality control ensures good matches
- Transparency (track which API found each ortholog)
- Resilience (if one API down, others compensate)

**Database Schema Addition (Post-MVP):**
```python
# Add to Gene model:
ortholog_data_source: str (nullable)  # "KEGG_KO", "OMA", "eggNOG", "OrthoDB"
ortholog_confidence: float (nullable)  # 0.0-100.0 quality score
```

---

## Decision Matrix

| Criteria | KEGG KO | OMA Browser | eggNOG | OrthoDB |
|----------|---------|-------------|---------|---------|
| **Ease of Integration** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **API Documentation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Coverage** | ⭐⭐⭐ (73%) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Direct Ortholog Pairs** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Free Access** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Maintenance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Rate Limits** | Known (3/sec) | Unknown | Unknown | Unknown |
| **KEGG Gene ID Support** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Prokaryote Coverage** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Eukaryote Coverage** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Implementation Timeline

### Week 2 (Current): MVP Research & Implementation
- ✅ Research completed (KEGG KO, OMA, eggNOG, OrthoDB)
- ✅ Decision: KEGG KO primary + OMA fallback for MVP
- ⏳ Implement KEGG KO ortholog finder
- ⏳ Test with E. coli dataset (4,639 genes)
- ⏳ Measure coverage and quality

### Week 3: Complete MVP Implementation
- ⏳ Implement OMA fallback (if coverage gap significant)
- ⏳ Add caching for KO mappings (improve performance)
- ⏳ Comprehensive testing with multiple organisms
- ⏳ Performance optimization

### Post-MVP (Future Sprint)
- 📌 Implement eggNOG integration
- 📌 Implement OrthoDB integration
- 📌 Build quality-based cascading logic
- 📌 Add database fields for ortholog_data_source and confidence
- 📌 Define quality thresholds based on user feedback
- 📌 Create admin dashboard to view data source statistics

---

## Key Bioinformatics Concepts (Reference)

### Orthology vs. Paralogy
- **Orthologs:** Genes separated by speciation (different species, same function)
  - Example: Human hemoglobin α and mouse hemoglobin α
- **Paralogs:** Genes separated by duplication (same species, related function)
  - Example: Human hemoglobin α and human hemoglobin β

### Best-Best Orthologs
- **Definition:** Reciprocal best matches between species
- Gene A (species 1) → best match is Gene B (species 2)
- Gene B (species 2) → best match is Gene A (species 1)
- **High confidence** that they are true orthologs

### Ortholog Groups (KO, eggNOG, OrthoDB)
- Cluster of genes across multiple species with common ancestor
- All genes in group perform similar molecular function
- Allows many-to-many orthology (not just pairs)

### Quality Metrics
- **Sequence Identity %:** How similar the protein sequences are (higher = more confident)
- **E-value:** Probability match occurred by chance (lower = better)
- **SW Score:** Smith-Waterman alignment score (higher = better alignment)
- **Phylogenetic Distance:** How evolutionarily distant the species are
  - Close species (human-chimp): easier to find orthologs, less functional variation
  - Distant species (human-fly): harder to find, but more interesting for function study

---

## Next Steps

### Immediate (Week 2)
1. ✅ Complete API research
2. ⏳ Implement `ortholog_service.py` with KEGG KO logic
3. ⏳ Add educational comments explaining bioinformatics concepts
4. ⏳ Test with E. coli (eco) - 4,639 genes
5. ⏳ Validate ortholog assignments manually for 10-20 genes

### Week 3
6. ⏳ Decide on OMA fallback based on coverage results
7. ⏳ Implement selected fallback strategy
8. ⏳ Integration testing with background jobs
9. ⏳ Performance optimization and caching

### Future (Post-MVP)
10. 📌 Document tiered quality-based cascading design
11. 📌 Implement eggNOG client
12. 📌 Implement OrthoDB client
13. 📌 Build multi-source orchestration logic
14. 📌 Add quality metrics to database schema
15. 📌 Create admin dashboard for ortholog statistics

---

**Document created:** November 29, 2024
**Last updated:** November 29, 2024
**Status:** Research complete, MVP implementation in progress
