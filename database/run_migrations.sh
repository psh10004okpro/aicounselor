#!/bin/bash
# =============================================================================
# Migration Runner Script
# Runs all database migrations in order
# =============================================================================

set -e  # Exit on error

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-mindful_counselor}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Database Migration Runner${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql command not found${NC}"
    echo "Please install PostgreSQL client or use Docker"
    exit 1
fi

# Check database connection
echo -e "${YELLOW}Checking database connection...${NC}"
if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    echo "Host: $POSTGRES_HOST:$POSTGRES_PORT"
    echo "Database: $POSTGRES_DB"
    echo "User: $POSTGRES_USER"
    exit 1
fi
echo -e "${GREEN}✓ Connected to database${NC}"
echo ""

# Create migrations tracking table if it doesn't exist
echo -e "${YELLOW}Setting up migration tracking...${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
" > /dev/null
echo -e "${GREEN}✓ Migration tracking ready${NC}"
echo ""

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

# Check if migrations directory exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}Error: Migrations directory not found: $MIGRATIONS_DIR${NC}"
    exit 1
fi

# Find all migration files
MIGRATION_FILES=($(ls -1 $MIGRATIONS_DIR/*.sql 2>/dev/null | sort))

if [ ${#MIGRATION_FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}No migration files found${NC}"
    exit 0
fi

echo -e "${YELLOW}Found ${#MIGRATION_FILES[@]} migration files${NC}"
echo ""

# Run each migration
SUCCESS_COUNT=0
SKIP_COUNT=0
ERROR_COUNT=0

for migration_file in "${MIGRATION_FILES[@]}"; do
    # Extract version number from filename (e.g., 001 from 001_initial_schema.sql)
    filename=$(basename "$migration_file")
    version=$(echo "$filename" | grep -oE '^[0-9]+' | sed 's/^0*//')
    name=$(echo "$filename" | sed 's/^[0-9]*_//' | sed 's/.sql$//')

    # Check if migration already applied
    APPLIED=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM schema_migrations WHERE version = $version;" | tr -d ' ')

    if [ "$APPLIED" -gt 0 ]; then
        echo -e "${YELLOW}⊘ Skipping migration $version: $name (already applied)${NC}"
        ((SKIP_COUNT++))
        continue
    fi

    echo -e "${YELLOW}▶ Running migration $version: $name${NC}"

    # Run the migration
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$migration_file" > /dev/null 2>&1; then
        # Record successful migration
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
            INSERT INTO schema_migrations (version, name)
            VALUES ($version, '$name')
            ON CONFLICT (version) DO NOTHING;
        " > /dev/null

        echo -e "${GREEN}✓ Successfully applied migration $version: $name${NC}"
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}✗ Failed to apply migration $version: $name${NC}"
        ((ERROR_COUNT++))

        # Show error details
        echo -e "${RED}Error details:${NC}"
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$migration_file"

        # Exit on first error
        echo ""
        echo -e "${RED}Migration failed. Stopping.${NC}"
        exit 1
    fi
done

# Summary
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Migration Summary${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Total migrations: ${#MIGRATION_FILES[@]}"
echo -e "${GREEN}Applied: $SUCCESS_COUNT${NC}"
echo -e "${YELLOW}Skipped: $SKIP_COUNT${NC}"
if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "${RED}Failed: $ERROR_COUNT${NC}"
else
    echo -e "Failed: 0"
fi
echo ""

if [ $ERROR_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All migrations completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some migrations failed${NC}"
    exit 1
fi
