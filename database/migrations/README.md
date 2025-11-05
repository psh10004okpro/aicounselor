# Database Migrations

This directory contains SQL migration scripts for the Mindful AI Counselor database.

## Migration Files

Migrations are numbered and should be executed in order:

1. **001_initial_schema.sql** - Initial database schema
   - Creates users, conversations, and messages tables
   - Sets up basic indexes
   - Enables required extensions (uuid-ossp, pgcrypto, vector)

2. **002_add_memories_table.sql** - Long-term memory system
   - Creates memories table for semantic/episodic/fact storage
   - Adds vector indexes for similarity search
   - Implements importance scoring

3. **003_add_conversation_summaries.sql** - Token efficiency
   - Creates conversation_summaries table
   - Tracks token savings and compression ratios
   - Stores key topics and sentiment analysis

4. **004_add_crisis_logs.sql** - Safety monitoring
   - Creates crisis_logs table
   - Tracks risk levels and interventions
   - Implements follow-up tracking

5. **005_add_utility_functions.sql** - Helper functions
   - Encryption/decryption functions
   - Vector similarity search functions
   - Data cleanup and archival functions
   - GDPR/HIPAA compliance tools

## How to Run Migrations

### Manual Execution

```bash
# Connect to PostgreSQL
psql -U postgres -d mindful_counselor

# Run migrations in order
\i database/migrations/001_initial_schema.sql
\i database/migrations/002_add_memories_table.sql
\i database/migrations/003_add_conversation_summaries.sql
\i database/migrations/004_add_crisis_logs.sql
\i database/migrations/005_add_utility_functions.sql
```

### Using Docker

```bash
# If using Docker Compose, migrations run automatically on first start
docker-compose up -d postgres

# Or run manually
docker exec -i mindful-postgres psql -U postgres -d mindful_counselor < database/migrations/001_initial_schema.sql
```

### Automated Script

```bash
# Run all migrations
./database/run_migrations.sh
```

## Rollback

Currently, migrations don't include rollback scripts. For development:

```bash
# Drop and recreate database
docker-compose down -v
docker-compose up -d
```

For production, create backup before migrations:

```bash
pg_dump -U postgres mindful_counselor > backup_$(date +%Y%m%d).sql
```

## Migration Best Practices

1. **Never modify existing migrations** - Create new ones instead
2. **Test migrations on development** before production
3. **Backup before running** on production
4. **Run migrations during low-traffic** periods
5. **Monitor performance** after index creation

## Schema Versioning

Track applied migrations in your application:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Future Migrations

When creating new migrations:

1. Number them sequentially (006, 007, etc.)
2. Include description in filename
3. Add comments explaining changes
4. Test with sample data
5. Update this README

## Useful Queries

### Check table sizes
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check index usage
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Verify vector indexes
```sql
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE indexdef LIKE '%vector%';
```

## Troubleshooting

### pgvector Extension Not Found
```bash
# Install pgvector extension
docker exec -it mindful-postgres bash
apt-get update && apt-get install -y postgresql-15-pgvector
```

### Migration Fails Partway
```bash
# Check what was created
\dt  # List tables
\di  # List indexes
\df  # List functions

# Clean up if needed
DROP TABLE table_name CASCADE;
```

### Performance Issues After Migration
```bash
# Analyze tables
ANALYZE users;
ANALYZE conversations;
ANALYZE messages;

# Reindex if needed
REINDEX TABLE messages;
```

## Contact

For questions about migrations, contact the database team or check the main README.
