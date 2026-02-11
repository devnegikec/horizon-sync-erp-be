# Script to set up search permissions in the identity service
# Usage: .\setup_permissions.ps1 -AdminToken "YOUR_ADMIN_TOKEN"

param(
    [Parameter(Mandatory=$true)]
    [string]$AdminToken
)

$IdentityUrl = "http://localhost:8000"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Setting up Search Service Permissions" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Create search.global permission
Write-Host "Creating search.global permission..." -ForegroundColor Yellow

$globalPermission = @{
    code = "search.global"
    name = "Global Search"
    description = "Perform global search across all entity types"
    resource = "search"
    action = "global"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$IdentityUrl/api/v1/identity/permissions" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Authorization" = "Bearer $AdminToken"
        } `
        -Body $globalPermission `
        -ErrorAction Stop

    if ($response.StatusCode -eq 201 -or $response.StatusCode -eq 200) {
        Write-Host "✓ search.global permission created successfully" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "✓ search.global permission already exists" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to create search.global permission" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""

# Create search.local permission
Write-Host "Creating search.local permission..." -ForegroundColor Yellow

$localPermission = @{
    code = "search.local"
    name = "Local Search"
    description = "Perform local search within specific entity types"
    resource = "search"
    action = "local"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$IdentityUrl/api/v1/identity/permissions" `
        -Method POST `
        -Headers @{
            "Content-Type" = "application/json"
            "Authorization" = "Bearer $AdminToken"
        } `
        -Body $localPermission `
        -ErrorAction Stop

    if ($response.StatusCode -eq 201 -or $response.StatusCode -eq 200) {
        Write-Host "✓ search.local permission created successfully" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "✓ search.local permission already exists" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to create search.local permission" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Permissions created successfully!" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Get your role ID:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/api/v1/identity/me -H 'Authorization: Bearer YOUR_TOKEN'" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Assign permissions to your role:" -ForegroundColor White
Write-Host "   curl -X POST http://localhost:8000/api/v1/identity/roles/{ROLE_ID}/permissions \" -ForegroundColor Gray
Write-Host "     -H 'Content-Type: application/json' \" -ForegroundColor Gray
Write-Host "     -H 'Authorization: Bearer $AdminToken' \" -ForegroundColor Gray
Write-Host "     -d '{\"permission_codes\": [\"search.global\", \"search.local\"]}'" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test the search endpoint:" -ForegroundColor White
Write-Host "   curl -X POST http://localhost:8002/api/v1/search/global \" -ForegroundColor Gray
Write-Host "     -H 'Content-Type: application/json' \" -ForegroundColor Gray
Write-Host "     -H 'Authorization: Bearer YOUR_USER_TOKEN' \" -ForegroundColor Gray
Write-Host "     -d '{\"query\": \"test\", \"page\": 1, \"page_size\": 20}'" -ForegroundColor Gray
