# PowerShell script to create test accounts via API

Write-Host "🚀 Creating test accounts..." -ForegroundColor Cyan

# Customer
Write-Host "`n📝 Creating Customer..." -ForegroundColor Yellow
$customer = @{
    email      = "customer@altayar.com"
    password   = "Customer123"
    first_name = "Sara"
    last_name  = "Customer"
    language   = "ar"
} | ConvertTo-Json -Compress

try {
    Invoke-RestMethod -Uri "http://localhost:8001/api/auth/register" -Method POST -Body $customer -ContentType "application/json" | Out-Null
    Write-Host "✅ Customer created!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Admin (will be customer first, then we update role)
Write-Host "`n📝 Creating Admin..." -ForegroundColor Yellow
$admin = @{
    email      = "admin@altayar.com"
    password   = "Admin123"
    first_name = "Admin"
    last_name  = "User"
    language   = "ar"
} | ConvertTo-Json -Compress

try {
    Invoke-RestMethod -Uri "http://localhost:8001/api/auth/register" -Method POST -Body $admin -ContentType "application/json" | Out-Null
    Write-Host "✅ Admin created!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

# Employee (will be customer first, then we update role)
Write-Host "`n📝 Creating Employee..." -ForegroundColor Yellow
$employee = @{
    email      = "employee@altayar.com"
    password   = "Employee123"
    first_name = "Employee"
    last_name  = "User"
    language   = "ar"
} | ConvertTo-Json -Compress

try {
    Invoke-RestMethod -Uri "http://localhost:8001/api/auth/register" -Method POST -Body $employee -ContentType "application/json" | Out-Null
    Write-Host "✅ Employee created!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

Write-Host "`n✅ Done! Now updating roles in database..." -ForegroundColor Cyan
