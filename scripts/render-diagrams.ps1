# Render every .mmd under doc/ to a .png in the same folder.
# Run from repository root: .\scripts\render-diagrams.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$diagrams = Get-ChildItem -Path "doc" -Filter "*.mmd" -Recurse -File
if (-not $diagrams) {
    Write-Host "No .mmd files found under doc/"
    exit 0
}

foreach ($mmd in $diagrams) {
    $png = [System.IO.Path]::ChangeExtension($mmd.FullName, ".png")
    Write-Host "Rendering $($mmd.FullName) -> $png"
    npx -y @mermaid-js/mermaid-cli -i $mmd.FullName -o $png -w 1400 -H 900 -b "#0f172a"
}

Write-Host "Done. Rendered $($diagrams.Count) diagram(s)."
