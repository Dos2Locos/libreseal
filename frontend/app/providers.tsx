'use client'

import { ThemeProvider } from '@/contexts/themeContext'
import { UserProvider } from '@/contexts/userContext'
import { ApolloProvider } from '@apollo/client'
import { graphQlClient } from '@/apollo/client'
import { KeyringProvider } from '@/contexts/keyringContext'
import { SidebarProvider } from '@/contexts/sidebarContext'
import { OrganisationProvider } from '@/contexts/organisationContext'
import { printConsoleBranding } from '@/utils/console'
import { useEffect } from 'react'

export default function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    printConsoleBranding()
  }, [])

  return (
    <ThemeProvider>
      <SidebarProvider>
        <UserProvider>
          <ApolloProvider client={graphQlClient}>
            <OrganisationProvider>
              <KeyringProvider>
                {children}
              </KeyringProvider>
            </OrganisationProvider>
          </ApolloProvider>
        </UserProvider>
      </SidebarProvider>
    </ThemeProvider>
  )
}
