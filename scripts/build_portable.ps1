param(
    [string]$DistDir = "dist/BDC_Generator",
    [string]$OutputDir = "release/portable"
)

$ErrorActionPreference = "Stop"

function New-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

New-Directory -Path $OutputDir

Copy-Item -Path $DistDir -Destination (Join-Path $OutputDir "BDC_Generator") -Recurse -Force
Copy-Item -Path "config.json" -Destination $OutputDir -Force

$runBat = "@echo off`r`n" +
"cd /d %~dp0`r`n" +
"start \"\" \"BDC_Generator\\BDC_Generator.exe\" %*`r`n"
Set-Content -Path (Join-Path $OutputDir "RUN.bat") -Value $runBat -Encoding ASCII

$readme = @"
BDC-AUTO - Portable
===================

1. Dézippez l'archive.
2. Placez le template PDF dans le même dossier ou renseignez son chemin complet.
3. Lancez RUN.bat en glissant-déposant le devis PDF sur le fichier ou via la ligne de commande.
4. Le PDF généré sera créé à côté de l'exécutable, sauf si vous fournissez un chemin --output.
"@
Set-Content -Path (Join-Path $OutputDir "README_Installation.txt") -Value $readme -Encoding UTF8

$zipPath = Join-Path (Split-Path $OutputDir) "BDC_Generator_Portable.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Compress-Archive -Path (Join-Path $OutputDir '*') -DestinationPath $zipPath
Write-Output "Archive générée: $zipPath"
