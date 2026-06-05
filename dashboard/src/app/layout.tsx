import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'

export const metadata: Metadata = {
  title: 'Rubricon',
  description: 'Rubric-based evaluation harness for AI agents',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <nav className="border-b bg-white px-6 py-3 flex items-center gap-6 text-sm">
          <Link href="/" className="font-bold text-lg">Rubricon</Link>
          <Link href="/runs">Runs</Link>
          <Link href="/suites">Suites</Link>
        </nav>
        <main className="max-w-5xl mx-auto p-6">{children}</main>
      </body>
    </html>
  )
}
