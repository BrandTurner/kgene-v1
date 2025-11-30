# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

KEGG Explore (KeggExplore) is a Rails 4.2.4 bioinformatics application that fetches gene data from the KEGG REST API and finds orthologous genes across different organisms using web scraping. The application uses background jobs to process organisms and discover gene orthologs.

## Technology Stack

- **Rails**: 4.2.4
- **Ruby**: 2.2.0 (see .ruby-version)
- **Database**: Oracle Enhanced adapter (development/production), SQLite3 (test)
- **Background Jobs**: Sidekiq (with Redis)
- **Authentication**: Devise
- **Parallel Processing**: Parallel gem (10 threads for ortholog fetching)
- **Data Fetching**: RestClient, Nokogiri for web scraping

## Development Commands

### Setup and Dependencies

```bash
# Install Ruby version
rbenv install 2.2.0  # or rvm install 2.2.0

# Install bundler compatible with this app
gem install bundler -v 1.17.3

# Install dependencies
bundle install
```

### Database

```bash
# Setup database (Oracle connection required for dev/prod)
rake db:create
rake db:migrate

# Reset database
rake db:reset

# Run migrations
rake db:migrate

# Rollback migrations
rake db:rollback
```

### Running the Application

```bash
# Development server (Puma)
rails server
# or
bundle exec rails s

# Production uses Passenger (configured in Gemfile)
```

### Background Jobs

```bash
# Start Sidekiq worker
bundle exec sidekiq

# Monitor Sidekiq (production only, accessible at /sidekiq with authentication)
```

### Docker Development

```bash
# Start all services (web, redis, sidekiq)
docker-compose up

# Build containers
docker-compose build

# Access web app at http://localhost:3000
```

### Testing

```bash
# Run all tests
rake test

# Run specific test file
ruby -I test test/models/organism_test.rb

# Run specific test
ruby -I test test/models/organism_test.rb -n test_name
```

### Console

```bash
# Rails console
rails console
# or
bundle exec rails c

# Production console
RAILS_ENV=production rails console
```

## Core Architecture

### Data Flow

1. **Organism Processing** (`ProcessesController#index`):
   - User triggers processing for an organism by code
   - `ProcessJob` is enqueued to Sidekiq
   - Job runs two sequential operations:
     - Fetches all genes for organism from KEGG REST API
     - Fetches orthologs for each gene via web scraping

2. **Gene Fetching** (`Gene.fetch_and_store_from_org`):
   - Calls KEGG REST API: `http://rest.kegg.jp/list/{organism_code}`
   - Parses TSV response to create Gene records
   - Updates organism status to 'pending'

3. **Ortholog Discovery** (`Gene.fetch_and_store_orthologs_for_organism`):
   - Parallel processing (10 threads) across all organism genes
   - Web scraping KEGG SSDB: `https://www.kegg.jp/ssdb-bin/ssdb_best_best?org_gene={gene_name}`
   - Finds best non-self ortholog match
   - Stores ortholog data (name, description, species, length, SW score, identity)
   - Updates organism status to 'complete'

### Models

- **Organism**: Represents a biological organism (code, name, status)
  - Has many genes
  - Tracks job status ('pending', 'complete', 'error')
  - `perc_complete` method calculates ortholog discovery progress

- **Gene**: Represents a gene from KEGG database
  - Belongs to organism
  - Stores gene data (name, description) and ortholog data (ortholog_name, ortholog_description, ortholog_species, ortholog_length, ortholog_sw_score, ortholog_identity)

- **User**: Devise authentication model

### Controllers

- **ProcessesController**: Main workflow controller
  - `index`: List processed organisms, trigger new processing jobs
  - `remove_results`: Delete all genes for an organism and reset status
  - `explore_orthologs`: View genes with orthologs found
  - `explore_no_orthologs`: View genes without orthologs
  - `download`: Export organism gene data to CSV

- **OrganismsController**: CRUD for organisms
- **GenesController**: Display genes for an organism
- **OrthologsController**: View ortholog-specific data

### Background Jobs

- **ProcessJob**: Sidekiq worker that orchestrates gene fetching and ortholog discovery
  - Uses connection pooling for thread safety
  - Processes one organism at a time

### Database Configuration

- **Development/Production**: Oracle Enhanced adapter
  - Database: serenity.bch.msu.edu/main.msu.edu
  - Connection pool: 20
- **Test**: SQLite3
- Oracle Instant Client 19.6 required (configured in Dockerfile)

### Key Patterns

1. **Error Handling**: Both fetching methods use begin/rescue/else/ensure blocks to update organism status and job_error
2. **Thread Safety**: Uses `ActiveRecord::Base.connection_pool.with_connection` for parallel processing
3. **Web Scraping**: Nokogiri parses pre-formatted KEGG SSDB tables for ortholog data
4. **Status Tracking**: Organisms have status field tracking job lifecycle (nil → pending → complete/error)

## Important Notes

- The application scrapes KEGG web pages which may be fragile if page structure changes
- Parallel processing uses 10 threads for ortholog fetching - adjust based on system resources
- Oracle database connection required for development/production environments
- Sidekiq requires Redis to be running
- Job errors are stored in `organism.job_error` field for debugging
