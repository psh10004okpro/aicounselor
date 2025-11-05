'use client'

interface LoadingDotsProps {
  size?: 'sm' | 'md' | 'lg'
  color?: string
}

export default function LoadingDots({ size = 'md', color }: LoadingDotsProps) {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
  }

  const dotSize = sizeClasses[size]
  const colorClass = color || 'bg-counselor-main'

  return (
    <div className="flex items-center space-x-1.5">
      <div
        className={`${dotSize} ${colorClass} rounded-full animate-bounce`}
        style={{ animationDelay: '0ms' }}
      />
      <div
        className={`${dotSize} ${colorClass} rounded-full animate-bounce`}
        style={{ animationDelay: '150ms' }}
      />
      <div
        className={`${dotSize} ${colorClass} rounded-full animate-bounce`}
        style={{ animationDelay: '300ms' }}
      />
    </div>
  )
}

/**
 * Typing indicator for chat messages
 */
export function TypingIndicator() {
  return (
    <div className="flex items-center space-x-2 px-4 py-3 bg-gray-100 rounded-2xl rounded-bl-sm max-w-[80px]">
      <LoadingDots size="sm" color="bg-gray-500" />
    </div>
  )
}

/**
 * Full-page loading spinner
 */
export function LoadingSpinner({ text }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] space-y-4">
      <div className="relative">
        <div className="w-12 h-12 border-4 border-counselor-light rounded-full"></div>
        <div className="w-12 h-12 border-4 border-counselor-main border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
      </div>
      {text && <p className="text-sm text-gray-600">{text}</p>}
    </div>
  )
}

/**
 * Inline loading indicator
 */
export function InlineLoader() {
  return (
    <div className="inline-flex items-center space-x-1">
      <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse"></div>
      <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse delay-75"></div>
      <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse delay-150"></div>
    </div>
  )
}
