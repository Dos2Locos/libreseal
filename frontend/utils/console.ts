export const printConsoleBranding = () => {
  console.log('%cLibreSeal', 'color: #10b981; font-size: 28px; font-weight: bold')
  console.log('%cStop!', 'color: #ff4444; font-size: 24px; font-weight: bold')
  console.log(
    '%cThis is a browser feature intended for developers. Do not paste any code or scripts here — it could compromise your account.',
    'color: #ffaa00; font-size: 14px'
  )
  console.log(
    '%cIssues and feature requests: %chttps://github.com/Dos2Locos/libreseal/issues',
    'color: #888; font-size: 12px',
    'color: #58a6ff; font-size: 12px'
  )
}
