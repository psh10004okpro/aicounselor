import ChatInterface from '@/components/ChatInterface'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            마음이 AI 상담사 💚
          </h1>
          <p className="text-gray-600 text-lg">
            당신의 마음 건강을 위한 공감적 AI 동반자
          </p>
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-gray-700 leading-relaxed">
            <strong className="text-blue-800">중요:</strong> 이 서비스는 AI 상담 도우미로, 전문 정신건강 치료를 대체할 수 없습니다.
            위기 상황이라면 즉시 <strong className="text-red-700">자살예방상담전화 1393</strong> 또는 <strong className="text-red-700">응급 119</strong>로 연락하세요.
          </div>
        </header>

        <ChatInterface />

        <footer className="mt-6 text-center text-xs text-gray-500">
          <p>🔒 모든 대화는 안전하게 암호화되어 보호됩니다</p>
        </footer>
      </div>
    </main>
  )
}
