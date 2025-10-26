# ============================
# sanitize-comments.ps1 (PowerShell Safe Final)
# ============================

$exts = @("*.js","*.ts","*.css","*.html","*.py")

function Write-IfChanged($path, $newContent) {
  $oldContent = ""
  if (Test-Path $path) {
    try { $oldContent = Get-Content -Raw -LiteralPath $path -Encoding UTF8 }
    catch { $oldContent = "" }
  }
  if ($null -eq $newContent) { $newContent = "" }
  if ($oldContent -ne $newContent) {
    $newContent | Set-Content -LiteralPath $path -Encoding UTF8
  }
}

Get-ChildItem -Recurse -File -Include $exts | ForEach-Object {
  $p = $_.FullName
  try {
    $txt = Get-Content -Raw -LiteralPath $p -Encoding UTF8
  } catch {
    $txt = ""
  }

  if ($null -eq $txt) { $txt = "" }

  switch -Wildcard ($_.Extension) {

    # JavaScript
    ".js" {
      if ($null -eq $txt) { $txt = "" }
      $txt = [Regex]::Replace($txt, '/\*[\s\S]*?\*/', '', 'Singleline')
      $txt = [Regex]::Replace($txt, '(?<!https?:)\/\/.*$', '', 'Multiline')
    }

    # TypeScript
    ".ts" {
      if ($null -eq $txt) { $txt = "" }
      $txt = [Regex]::Replace($txt, '/\*[\s\S]*?\*/', '', 'Singleline')
      $txt = [Regex]::Replace($txt, '(?<!https?:)\/\/.*$', '', 'Multiline')
    }

    # CSS
    ".css" {
      if ($null -eq $txt) { $txt = "" }
      $txt = [Regex]::Replace($txt, '/\*[\s\S]*?\*/', '', 'Singleline')
    }

    # HTML
    ".html" {
      if ($null -eq $txt) { $txt = "" }
      $txt = [Regex]::Replace($txt, '<!--[\s\S]*?-->', '', 'Singleline')
    }

    # Python
    ".py" {
      if ($null -eq $txt) { $txt = "" }
      # Xóa dòng comment bắt đầu với #
      $txt = [Regex]::Replace($txt, '^[ \t]*#.*$', '', 'Multiline')
      # Xóa docstring """...""" và '''...'''
      $txt = [Regex]::Replace($txt, '^\s*"""[\s\S]*?"""\s*', '', 'Singleline')
      $txt = [Regex]::Replace($txt, "^\s*'''[\s\S]*?'''\s*", '', 'Singleline')
    }

  }

  # Dọn dòng trống thừa
  if ($null -eq $txt) { $txt = "" }
  $txt = [Regex]::Replace($txt, "(\r?\n){3,}", "`r`n`r`n")

  Write-IfChanged $p $txt
}

Write-Host "✅ Done removing comments and docstrings (PowerShell Safe Final)."
