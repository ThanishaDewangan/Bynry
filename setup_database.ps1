# PowerShell script to set up the StockFlow database
# Run this script to create and populate the database

param(
    [string]$Username = "postgres",
    [string]$Database = "stockflow",
    [string]$DbHost = "localhost",
    [int]$Port = 5432
)

Write-Host "Setting up StockFlow database..." -ForegroundColor Green

# Check if psql is available
try {
    $psqlVersion = psql --version 2>&1
    Write-Host "Found PostgreSQL client: $psqlVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: PostgreSQL client (psql) not found in PATH" -ForegroundColor Red
    Write-Host "Please install PostgreSQL or add psql to your PATH" -ForegroundColor Yellow
    exit 1
}

# Check if database exists
Write-Host "Checking if database exists..." -ForegroundColor Yellow
$dbExists = psql -U $Username -h $DbHost -p $Port -lqt 2>&1 | Select-String -Pattern "\b$Database\b"

if (-not $dbExists) {
    Write-Host "Database '$Database' does not exist. Creating..." -ForegroundColor Yellow
    $createDb = "CREATE DATABASE $Database;"
    psql -U $Username -h $DbHost -p $Port -c $createDb
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error creating database. Please check your PostgreSQL connection." -ForegroundColor Red
        exit 1
    }
    Write-Host "Database created successfully!" -ForegroundColor Green
} else {
    Write-Host "Database '$Database' already exists." -ForegroundColor Green
}

# Run schema file
Write-Host "Applying database schema..." -ForegroundColor Yellow
Get-Content database_schema.sql | psql -U $Username -h $DbHost -p $Port -d $Database

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database schema applied successfully!" -ForegroundColor Green
    Write-Host "You can now use the StockFlow application." -ForegroundColor Green
} else {
    Write-Host "Error applying schema. Please check the error messages above." -ForegroundColor Red
    exit 1
}

