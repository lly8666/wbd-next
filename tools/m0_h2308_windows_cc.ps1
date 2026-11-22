# H2308 Windows2025 signed original product test-only scoped kernel TCP provider.
# Apply only inside ephemeral CI runner, immediately before actual original WBD
# inner-TCP stage. Always restore both templates and confirm actual readback.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet("Setup","Restore")][string]$Action)
$ErrorActionPreference='Stop'
$root='h2308-out'
$beforeFile=Join-Path $root 'windows-cc-before.json'
$names=@('Internet','Datacenter')
$allowed=@('default','cubic','ctcp','dctcp','bbr2','none')
function Inspect-Settings {
  $rows=@()
  foreach($name in $names) {
    $setting=Get-NetTCPSetting -SettingName $name -ErrorAction Stop
    $rows+= [pscustomobject]@{Template=$name;Provider=([string]$setting.CongestionProvider)}
  }
  return $rows
}
if($Action -eq 'Setup') {
  New-Item -ItemType Directory -Force $root | Out-Null
  if(Test-Path $beforeFile){throw 'H2308_SCOPE_PREVIOUS_TCP_CC_SNAPSHOT_NOT_CLEAN'}
  $before=@(Inspect-Settings)
  if($before.Count -ne 2){throw 'H2308_ORIGINAL_TCP_TEMPLATE_READBACK_INCOMPLETE'}
  foreach($entry in $before){
    if($entry.Provider.ToLowerInvariant() -notin $allowed){
      throw 'H2308_UNKNOWN_ORIGINAL_TCP_CC_NO_MUTATION'
    }
  }
  ConvertTo-Json -InputObject $before -Depth 5 | Set-Content -Encoding utf8 $beforeFile
  foreach($entry in $before){
    & netsh.exe interface tcp set supplemental "template=$($entry.Template)" "congestionprovider=bbr2"
    if($LASTEXITCODE -ne 0){throw "H2308_BBR2_UNSUPPORTED_$($entry.Template)"}
  }
  $after=@(Inspect-Settings)
  ConvertTo-Json -InputObject $after -Depth 5 | Set-Content -Encoding utf8 (Join-Path $root 'windows-cc-after.json')
  if($after.Count -ne 2 -or @($after | Where-Object {$_.Provider -ne 'BBR2'}).Count -gt 0){
    throw 'H2308_TCP_CC_BBR2_READBACK_NOT_APPLIED'
  }
  Write-Output 'H2308_WINDOWS2025_OS_BBR2_REAL_READBACK_APPLIED'
} else {
  if(-not (Test-Path $beforeFile)){
    Write-Output 'H2308_NO_TCP_PROVIDER_CHANGE_TO_RESTORE'
    return
  }
  $saved=@(Get-Content $beforeFile -Raw | ConvertFrom-Json)
  if($saved.Count -ne 2){throw 'H2308_TCP_PROVIDER_RESTORE_SNAPSHOT_INCOMPLETE'}
  foreach($entry in $saved){
    $name=[string]$entry.Template
    $provider=([string]$entry.Provider).ToLowerInvariant()
    if($name -notin $names -or $provider -notin $allowed){
      throw 'H2308_REFUSE_UNKNOWN_TCP_PROVIDER_RESTORE'
    }
    & netsh.exe interface tcp set supplemental "template=$name" "congestionprovider=$provider"
    if($LASTEXITCODE -ne 0){throw "H2308_ORIGINAL_TCP_CC_RESTORE_FAILED_$name"}
  }
  $after=@(Inspect-Settings)
  ConvertTo-Json -InputObject $after -Depth 5 | Set-Content -Encoding utf8 (Join-Path $root 'windows-cc-restored.json')
  foreach($entry in $saved){
    $match=@($after | Where-Object {$_.Template -eq $entry.Template})
    if($match.Count -ne 1 -or $match[0].Provider -ne $entry.Provider){
      throw "H2308_ORIGINAL_TCP_CC_NOT_RESTORED_$($entry.Template)"
    }
  }
  Write-Output 'H2308_WINDOWS_ORIGINAL_TCP_CC_RESTORED'
}
