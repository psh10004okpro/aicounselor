import ChatInterface from '@/components/ChatInterface'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Mindful AI Counselor
          </h1>
          <p className="text-gray-600">
            Your compassionate AI companion for mental wellness
          </p>
          <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-gray-700">
            <strong>Important:</strong> This is an AI assistant, not a replacement for professional mental health care.
            If you're in crisis, please contact emergency services or call the Suicide & Crisis Lifeline at 988.
          </div>
        </header>

        <ChatInterface />
      </div>
    </main>
  )
}
