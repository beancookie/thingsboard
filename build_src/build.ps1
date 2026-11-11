$ErrorActionPreference = 'Stop'
$out = '演讲稿-技术汇报.html'
$parts = Get-ChildItem -Path 'build_src' -Filter '*.frag' | Sort-Object Name
$sb = [System.Text.StringBuilder]::new()
foreach ($p in $parts) { [void]$sb.Append([System.IO.File]::ReadAllText($p.FullName, [System.Text.Encoding]::UTF8)) }
[System.IO.File]::WriteAllText((Join-Path (Get-Location) $out), $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
Write-Host ("built -> {0} ({1} bytes, {2} fragments)" -f $out, (Get-Item $out).Length, $parts.Count)
