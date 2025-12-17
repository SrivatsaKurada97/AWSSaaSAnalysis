## Database Schema

This project uses a **star schema** optimized for analytical queries.

### Tables

- **aws_users** (Dimension) - Customer profiles and metrics (950 rows)
- **aws_events** (Fact) - Transaction activity log (9,994 rows)
- **aws_features** (Dimension) - Product catalog (15 rows)
- **aws_milestones** (Fact) - Customer lifecycle events (3,500+ rows)

### Schema Diagram

![Database Schema](sql/schema/database_diagram.png)

### Setup Instructions

1. Create database: `CREATE DATABASE AWSSaaSDB`
2. Run schema scripts in order:
```
   sql/schema/01_create_tables.sql
   sql/schema/02_create_foreign_keys.sql
   sql/schema/03_create_indexes.sql
```
3. Load data (see `/data` folder)
4. Run stored procedures to generate derived columns
5. Query away! (see sample queries)
