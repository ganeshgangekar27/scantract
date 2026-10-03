#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <dbname>"
    exit 1
fi

DBNAME=$1

echo "=== DB HASHES FOR: $DBNAME ==="

for table in alembic_version clauses contracts legal_rules reference_clauses risk_findings; do
    # Determine primary key column
    case $table in
        alembic_version)
            pk="version_num"
            ;;
        risk_findings)
            pk="id::text"  # UUID needs text cast
            ;;
        *)
            pk="id"
            ;;
    esac
    
    count=$(psql -U postgres -d "$DBNAME" -tAc "SELECT COUNT(*) FROM $table")
    hash=$(psql -U postgres -d "$DBNAME" -tAc "SELECT MD5(STRING_AGG($table::text, '|' ORDER BY $pk)) FROM $table")
    
    echo "$table|$count|$hash"
done
