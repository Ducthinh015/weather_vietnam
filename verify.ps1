# Requires PowerShell 5+
$ErrorActionPreference = "Stop"

function Write-Ok($msg){ Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Fail($msg){ Write-Host "[FAIL] $msg" -ForegroundColor Red }
function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }

# 0) Paths
$RepoRoot = (Get-Location).Path
$BackendEnv = Join-Path $RepoRoot "backend\.env"
$FrontendDir = Join-Path $RepoRoot "frontend\src"
$BackendHealth = "http://localhost:5000/health"

$results = @{
  WeatherApiKey = $false
  BackendHealth = $false
  Forecast5     = $false
  FrontendAPI   = $false
  Charts        = $false
}

Write-Info "=== STEP 1: Verify WeatherAPI key ==="
if (-not (Test-Path $BackendEnv)){
  Write-Fail "Không tìm thấy backend\.env"
} else {
  # Load .env WEATHERAPI_KEY
  $envLines = Get-Content $BackendEnv | Where-Object { $_ -match '^\s*WEATHERAPI_KEY\s*=' }
  if ($envLines.Count -eq 0){
    Write-Fail "WEATHERAPI_KEY không có trong backend\.env"
  } else {
    $kv = $envLines -split '=',2
    $key = $kv[1].Trim()
    if (-not $key){
      Write-Fail "WEATHERAPI_KEY rỗng"
    } else {
      try {
        $url = ('https://api.weatherapi.com/v1/forecast.json?key={0}&q=Hanoi&days=1&lang=vi' -f $key)
        $probe = Invoke-RestMethod -Uri $url -TimeoutSec 15
        if ($probe.location -and $probe.forecast){
          Write-Ok "WeatherAPI key hợp lệ"
          $results.WeatherApiKey = $true
        } else {
          Write-Fail "WeatherAPI key không trả dữ liệu mong đợi"
        }
      } catch {
        Write-Fail "Gọi WeatherAPI thất bại: $($_.Exception.Message)"
      }
    }
  }
}

Write-Info "=== STEP 2: Verify backend endpoints ==="
# Kiểm tra backend đang chạy chưa
$backendUp = $false
try {
  $health = Invoke-RestMethod -Uri $BackendHealth -TimeoutSec 5
  $backendUp = $true
} catch {
  Write-Info "Backend chưa chạy. Vui lòng mở 1 cửa sổ mới và chạy: python -m backend.app"
}

if (-not $backendUp){
  Write-Fail "Bỏ qua test endpoint vì backend chưa sẵn sàng."
} else {
  try {
    $health = Invoke-RestMethod -Uri $BackendHealth -TimeoutSec 10
    if ($health.status -eq "ok"){
      Write-Ok "/health OK (weatherapi=$($health.weatherapi))"
      $results.BackendHealth = $true
    } else {
      Write-Fail "/health trả về không OK: $($health | ConvertTo-Json -Compress)"
    }
  } catch {
    Write-Fail "Gọi /health lỗi: $($_.Exception.Response.StatusCode) $($_.Exception.Message)"
  }

  $base = "http://localhost:5000/api"
  $city = "Hanoi"

  function Test-Get($path){
    try {
      $res = Invoke-RestMethod -Uri $path -TimeoutSec 20
      return ,$true,$res
    } catch {
      try {
        $body = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($body)
        $text = $reader.ReadToEnd()
        return ,$false,$text
      } catch {
        return ,$false,$_.Exception.Message
      }
    }
  }

  $ok,$res = Test-Get "$base/weather?city=$city"
  if ($ok){ Write-Ok "/api/weather OK" } else { Write-Fail "/api/weather lỗi: $res" }

  $ok2,$res2 = Test-Get "$base/forecast?city=$city&hours=5"
  if ($ok2){
    Write-Ok "/api/forecast OK"
    $results.Forecast5 = $true
  } else {
    Write-Fail "/api/forecast lỗi: $res2"
  }

  $ok3,$res3 = Test-Get "$base/forecast3?city=$city"
  if ($ok3){ Write-Ok "/api/forecast3 OK" } else { Write-Fail "/api/forecast3 lỗi: $res3" }

  $ok4,$res4 = Test-Get "$base/history?city=$city&limit=50"
  if ($ok4){ Write-Ok "/api/history OK" } else { Write-Fail "/api/history lỗi: $res4" }
}

Write-Info "=== STEP 3: Verify frontend API_BASE and connectivity ==="
# Kiểm tra file api.js
$apiJs = Join-Path $FrontendDir "js\api.js"
if (Test-Path $apiJs){
  $apiContent = Get-Content $apiJs -Raw
  if ($apiContent -match 'window\.API_BASE\s*\|\|\s*"http://localhost:5000/api"'){
    Write-Ok "api.js có fallback API_BASE localhost"
  } else {
    Write-Fail "api.js không có fallback API_BASE localhost"
  }
} else {
  Write-Fail "Không tìm thấy frontend/src/js/api.js"
}

# Kiểm tra forecast.html auto API_BASE snippet
$forecastHtml = Join-Path $FrontendDir "pages\forecast.html"
if (Test-Path $forecastHtml){
  $hit = Select-String -Path $forecastHtml -SimpleMatch "window.API_BASE = 'http://'+ location.hostname" -Quiet
  if ($hit){
    Write-Ok "forecast.html có auto-detect API_BASE cho LAN"
    $results.FrontendAPI = $true
  } else {
    Write-Fail "forecast.html chưa auto-detect API_BASE cho LAN"
  }
} else {
  Write-Fail "Không tìm thấy forecast.html"
}

# Charts render (mang tính quan sát thủ công)
# Ở script tự động, đánh dấu pass nếu forecast endpoint OK và FE config OK
if ($results.Forecast5 -and $results.FrontendAPI){
  $results.Charts = $true
}

Write-Host ""
Write-Info "=== SUMMARY ==="
Write-Host ("WeatherAPI key:       " + ($(if($results.WeatherApiKey){"OK"}else{"FAIL"})))
Write-Host ("Backend health:       " + ($(if($results.BackendHealth){"OK"}else{"FAIL"})))
Write-Host ("Forecast 5h API:      " + ($(if($results.Forecast5){"OK"}else{"FAIL"})))
Write-Host ("Frontend API config:  " + ($(if($results.FrontendAPI){"OK"}else{"FAIL"})))
Write-Host ("Charts render (est.): " + ($(if($results.Charts){"OK"}else{"FAIL"})))

if ($results.WeatherApiKey -and $results.BackendHealth -and $results.Forecast5 -and $results.FrontendAPI){
  Write-Ok "System OK. AgriCast-AI v2 fully operational."
} else {
  Write-Fail "Một số hạng mục chưa đạt. Hãy xem các mục FAIL ở trên để sửa."
}