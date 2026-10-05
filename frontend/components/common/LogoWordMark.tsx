import React from 'react'
import { LOGO_MARK_KEYHOLE_PATH, LOGO_MARK_SHIELD_PATH } from './LogoMark'

interface LogoProps extends React.SVGProps<SVGSVGElement> {}

export const LogoWordMark: React.FC<LogoProps> = (props) => {
  return (
    <svg viewBox="0 0 290 64" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LibreSeal" {...props}>
      <path fillRule="evenodd" clipRule="evenodd" d={LOGO_MARK_SHIELD_PATH} />
      <path d={LOGO_MARK_KEYHOLE_PATH} />
      <text
        x="76"
        y="46"
        fontFamily="var(--font-inter), Inter, Helvetica, Arial, sans-serif"
        fontSize="44"
        fontWeight="700"
        letterSpacing="-0.5"
      >
        LibreSeal
      </text>
    </svg>
  )
}
