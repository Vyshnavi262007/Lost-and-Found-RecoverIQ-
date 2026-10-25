$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\frontend"
npm install
Write-Host "Frontend ready. Start it with: npm run dev"
