const createWindowsInstaller = require('electron-winstaller').createWindowsInstaller
const path = require('path')

getInstallerConfig()
  .then(createWindowsInstaller)
  .catch((error) => {
    console.error(error.message || error)
    process.exit(1)
  })

function getInstallerConfig () {
  console.log('Creating windows installer')
  const rootPath = path.join('./')
  const outPath = path.join(rootPath, 'release-builds')

  return Promise.resolve({
    appDirectory: path.join(rootPath, 'Cryptodoge Light Wallet-win32-x64'),
    authors: 'Cryptodoge Network',
    version: process.env.CRYPTODOGE_INSTALLER_VERSION,
    noMsi: true,
    iconUrl: 'https://raw.githubusercontent.com/CryptoDoge-Network/cryptodoge/master/electron-react/src/assets/img/cryptodogelight.ico',
    outputDirectory: path.join(outPath, 'windows-installer'),
    
    
    exe: 'CryptodogeLight.exe',
    setupExe: 'CryptodogeLightSetup-' + process.env.CRYPTODOGE_INSTALLER_VERSION + '.exe',
    setupIcon: path.join(rootPath, 'src', 'assets', 'img', 'cryptodogelight.ico')
  })
}
