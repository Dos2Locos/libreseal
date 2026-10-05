import React from 'react'

interface LogoProps extends React.SVGProps<SVGSVGElement> {}

// LibreSeal mark: a seal-shaped shield with a keyhole (original artwork, see
// public/brand/README.md). Colour comes from the caller's `fill-*` classes.
export const LOGO_MARK_SHIELD_PATH =
  'M32 2 58 12v18c0 16-11 27-26 32C17 57 6 46 6 30V12L32 2Zm0 7.5L13 16.8V30c0 12 8 20.6 19 24.6C43 50.6 51 42 51 30V16.8L32 9.5Z'
export const LOGO_MARK_KEYHOLE_PATH =
  'M32 20.5a6.5 6.5 0 0 1 3.6 11.9L37.8 44H26.2l2.2-11.6A6.5 6.5 0 0 1 32 20.5Z'

export const LogoMark: React.FC<LogoProps> = (props) => {
  return (
    <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LibreSeal" {...props}>
      <path fillRule="evenodd" clipRule="evenodd" d={LOGO_MARK_SHIELD_PATH} />
      <path d={LOGO_MARK_KEYHOLE_PATH} />
    </svg>
  )
}
