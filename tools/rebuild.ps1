$ErrorActionPreference = 'Stop'
$port = 52370
$root = 'C:\profile'
$dist = Join-Path $root 'dist'
$python = 'C:\Users\teet4\AppData\Local\Programs\Python\Python312\python.exe'

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'http\.server' -and $_.CommandLine -match [regex]::Escape($port.ToString()) -and $_.CommandLine -match [regex]::Escape($dist) } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

& $python (Join-Path $root 'tools\build.py')
if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE" }

$cmd = '"' + $python + '" -m http.server ' + $port + ' --bind 127.0.0.1 --directory "' + $dist + '"'
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $dist }
if ($result.ReturnValue -ne 0) { throw "Start-Process failed: $($result.ReturnValue)" }
Start-Sleep -Seconds 2
Write-Output "Server PID: $($result.ProcessId) - http://127.0.0.1:$port/"
