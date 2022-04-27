# $env:path should contain a path to editbin.exe and signtool.exe

$ErrorActionPreference = "Stop"

mkdir win_build
Set-Location -Path ".\win_build" -PassThru

git status

Write-Output "   ---"
Write-Output "curl miniupnpc"
Write-Output "   ---"
Invoke-WebRequest -Uri "https://pypi.chia.net/simple/miniupnpc/miniupnpc-2.1-cp37-cp37m-win_amd64.whl" -OutFile "miniupnpc-2.1-cp37-cp37m-win_amd64.whl"
Write-Output "Using win_amd64 python 3.7 wheel from https://github.com/miniupnp/miniupnp/pull/475 (2.2.0-RC1)"
# If ($LastExitCode -gt 0){
#     Throw "Failed to download miniupnpc!"
# }
# else
# {
#     Set-Location -Path - -PassThru
#     Write-Output "miniupnpc download successful."
# }

Write-Output "   ---"
Write-Output "Create venv - python3.7 or 3.8 is required in PATH"
Write-Output "   ---"
python -m venv venv
. .\venv\Scripts\Activate.ps1
Write-Output "   -1--"
#python -m pip install --upgrade pip
pip install pip==18.1 --user 
Write-Output "   --2-"
pip install whl pep517
Write-Output "   -3--"
pip install pywin32
pip install pyinstaller==4.5
pip install setuptools_scm

Write-Output "   ---"
Write-Output "Get CRYPTODOGE_INSTALLER_VERSION"
# The environment variable CRYPTODOGE_INSTALLER_VERSION needs to be defined
$env:CRYPTODOGE_INSTALLER_VERSION = python D:\cryptodoge-light-wallet\build_scripts\installer-version.py -win

if (-not (Test-Path env:CRYPTODOGE_INSTALLER_VERSION)) {
  $env:CRYPTODOGE_INSTALLER_VERSION = '0.0.0'
  Write-Output "WARNING: No environment variable CRYPTODOGE_INSTALLER_VERSION set. Using 0.0.0"
  }
Write-Output "Cryptodoge Version is: $env:CRYPTODOGE_INSTALLER_VERSION"
Write-Output "   ---"

Write-Output "   ---"
Write-Output "Build cryptodogelight wheels"
Write-Output "   ---"
pip wheel --use-pep517 --extra-index-url https://pypi.chia.net/simple/ -f . --wheel-dir=.\win_build D:\cryptodoge-light-wallet

Write-Output "   ---"
Write-Output "Install cryptodogelight wheels into venv with pip"
Write-Output "   ---"

Write-Output "pip install miniupnpc"
#Set-Location -Path ".\build_scripts" -PassThru
pip install --no-index --find-links=. miniupnpc
# Write-Output "pip install setproctitle"
# pip install setproctitle==1.2.2

Write-Output "pip install cryptodogelight"
pip install --no-index --find-links=.\win_build\ cryptodogelight

Write-Output "   ---"
Write-Output "Use pyinstaller to create cryptodogelight .exe's"
Write-Output "   ---"
$SPEC_FILE = (python -c 'import cryptodogelight; print(cryptodogelight.PYINSTALLER_SPEC_PATH)') -join "`n"
pyinstaller --log-level INFO $SPEC_FILE

Write-Output "   ---"
Write-Output "Copy cryptodogelight executables to cryptodoge-gui\"
Write-Output "   ---"
Copy-Item "D:\cryptodoge-light-wallet\build_scripts\win_build\dist\daemon" -Destination "D:\cryptodoge-light-wallet\cryptodoge-gui\packages\wallet" -Recurse
Set-Location -Path "D:\cryptodoge-light-wallet\cryptodoge-gui" -PassThru


git status

Write-Output "   ---"
Write-Output "Prepare Electron packager"
Write-Output "   ---"
$Env:NODE_OPTIONS = "--max-old-space-size=3000"
npm install -g electron-winstaller
npm install -g electron-packager
npm install -g lerna

lerna clean -y
npm install

git status

Write-Output "   ---"
Write-Output "Electron package Windows Installer"
Write-Output "   ---"
npm run build
If ($LastExitCode -gt 0){
    Throw "npm run build failed!"
}

Set-Location -Path "D:\cryptodoge-light-wallet\cryptodoge-gui\packages\wallet" -PassThru

Write-Output "   ---"
Write-Output "Increase the stack for cryptodogelight command for (cryptodogelight plots create) chiapos limitations"
# editbin.exe needs to be in the path
D:\cryptodoge-light-wallet\cryptodoge-gui\editbin.exe /STACK:8000000 D:\cryptodoge-light-wallet\cryptodoge-gui\packages\wallet\daemon\cryptodogelight.exe
Write-Output "   ---"

$packageVersion = "$env:CRYPTODOGE_INSTALLER_VERSION"
$packageName = "CryptodogeLight-$packageVersion"

Write-Output "packageName is $packageName"

Write-Output "   ---"
Write-Output "fix version in package.json"
choco install jq
cp package.json package.json.orig
jq --arg VER "$env:CRYPTODOGE_INSTALLER_VERSION" '.version=$VER' package.json > temp.json
rm package.json
mv temp.json package.json
Write-Output "   ---"

Write-Output "   ---"
Write-Output "electron-packager"
electron-packager . "Cryptodoge Light Wallet" --asar.unpack="**\daemon\**" --overwrite --icon=.\src\assets\img\cryptodogelight.ico --app-version=$packageVersion --executable-name=cryptodogelight
Write-Output "   ---"

Write-Output "   ---"
Write-Output "node winstaller.js"
node winstaller.js
Write-Output "   ---"

git status

If ($env:HAS_SECRET) {
   Write-Output "   ---"
   Write-Output "Add timestamp and verify signature"
   Write-Output "   ---"
   signtool.exe timestamp /v /t http://timestamp.comodoca.com/ .\release-builds\windows-installer\CryptodogeSetup-$packageVersion.exe
   signtool.exe verify /v /pa .\release-builds\windows-installer\CryptodogeSetup-$packageVersion.exe
   }   Else    {
   Write-Output "Skipping timestamp and verify signatures - no authorization to install certificates"
}

git status

Write-Output "   ---"
Write-Output "Windows Installer complete"
Write-Output "   ---"

