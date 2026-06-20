Write-Host "=== ACBP Truth Compiler API Smoke Test ===" -ForegroundColor Cyan

$base = "http://localhost:8790"
$headers = @{
  "X-ACBP-API-Key" = "acbp_free_demo"
  "Content-Type" = "application/json"
}

Write-Host "`n[0] Checking server..." -ForegroundColor Yellow

try {
    Invoke-RestMethod "$base/v1/health" | Out-Host
} catch {
    Write-Host "API server is not running on $base" -ForegroundColor Red
    Write-Host "Start it with:" -ForegroundColor Yellow
    Write-Host 'powershell.exe -ExecutionPolicy Bypass -File "D:\ACBP\Apps\CompilerAPI\run_compiler_api.ps1"'
    exit 1
}

Write-Host "`n[1] Pricing" -ForegroundColor Yellow
Invoke-RestMethod "$base/v1/pricing"

Write-Host "`n[2] Truth Space Compile" -ForegroundColor Yellow
$body = Get-Content "D:\ACBP\Apps\CompilerAPI\examples\truth_space_compile.json" -Raw
Invoke-RestMethod -Uri "$base/v1/truth-space/compile" -Method Post -Headers $headers -Body $body

Write-Host "`n[3] Compact Features" -ForegroundColor Yellow
$body = Get-Content "D:\ACBP\Apps\CompilerAPI\examples\compact_features.json" -Raw
Invoke-RestMethod -Uri "$base/v1/features/compact" -Method Post -Headers $headers -Body $body

Write-Host "`n[4] Dashboard Compare" -ForegroundColor Yellow
$body = Get-Content "D:\ACBP\Apps\CompilerAPI\examples\dashboard_compare.json" -Raw
Invoke-RestMethod -Uri "$base/v1/dashboard/compare" -Method Post -Headers $headers -Body $body

Write-Host "`nSmoke test complete." -ForegroundColor Green
