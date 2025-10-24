import { ReactNode } from 'react'
import { Header } from './Header'
import { Navigation } from './Navigation'
import { Footer } from './Footer'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <Navigation />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
      <Footer />
    </div>
  )
}
