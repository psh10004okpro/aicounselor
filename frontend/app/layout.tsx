import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '마음이 AI 상담사 - Mindful AI Counselor',
  description: '공감적이고 전문적인 AI 심리상담 도우미. 당신의 마음 건강을 위한 24시간 지원 서비스입니다.',
  keywords: ['AI 상담', '심리상담', '정신건강', '마음건강', 'AI counseling', 'mental health', 'therapy', '우울', '불안'],
  authors: [{ name: 'Mindful AI Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#4caf50',
  openGraph: {
    title: '마음이 AI 상담사',
    description: '공감적이고 전문적인 AI 심리상담 도우미',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
        {children}
      </body>
    </html>
  )
}
