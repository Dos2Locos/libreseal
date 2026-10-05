import { Metadata } from 'next'
import { HeroPattern } from '@/components/common/HeroPattern'
import OnboardingNavbar from '@/components/layout/OnboardingNavbar'

export const metadata: Metadata = {
  title: 'LibreSeal Lockbox',
  description: "You've received a secret via LibreSeal Lockbox, secured with Zero-Trust encryption.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <HeroPattern />
      <OnboardingNavbar />
      {children}
    </>
  )
}
