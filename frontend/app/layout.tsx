import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Mindful AI Counselor',
  description: 'Compassionate AI-powered mental health support',
  keywords: ['mental health', 'counseling', 'AI', 'support', 'therapy'],
  authors: [{ name: 'Mindful AI Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#4caf50',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
        {children}
      </body>
    </html>
  )
}
