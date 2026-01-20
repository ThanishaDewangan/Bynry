#!/bin/bash
# Bash script to set up the StockFlow database
# Run this script to create and populate the database

USERNAME=${1:-postgres}
DATABASE=${2:-stockflow}
HOST=${3:-localhost}
PORT=${4:-5432}

echo "Setting up StockFlow database..."

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "Error: PostgreSQL client (psql) not found"
    echo "Please install PostgreSQL or add psql to your PATH"
    exit 1
fi

# Check if database exists
if psql -U "$USERNAME" -h "$HOST" -p "$PORT" -lqt | cut -d \| -f 1 | grep -qw "$DATABASE"; then
    echo "Database '$DATABASE' already exists."
else
    echo "Database '$DATABASE' does not exist. Creating..."
    psql -U "$USERNAME" -h "$HOST" -p "$PORT" -c "CREATE DATABASE $DATABASE;"
    if [ $? -ne 0 ]; then
        echo "Error creating database. Please check your PostgreSQL connection."
        exit 1
    fi
    echo "Database created successfully!"
fi

# Run schema file
echo "Applying database schema..."
psql -U "$USERNAME" -h "$HOST" -p "$PORT" -d "$DATABASE" -f database_schema.sql

if [ $? -eq 0 ]; then
    echo "Database schema applied successfully!"
    echo "You can now use the StockFlow application."
else
    echo "Error applying schema. Please check the error messages above."
    exit 1
fi

