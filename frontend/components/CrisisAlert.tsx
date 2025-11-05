'use client'

import { useState } from 'react'

interface CrisisAlertProps {
  riskLevel?: 'critical' | 'high' | 'medium' | 'low' | 'none'
}

export default function CrisisAlert({ riskLevel = 'high' }: CrisisAlertProps) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed || riskLevel === 'none') return null

  // Determine severity styling based on risk level
  const isCritical = riskLevel === 'critical'
  const borderColor = isCritical ? 'border-red-600' : 'border-crisis-main'
  const bgColor = isCritical ? 'bg-red-50' : 'bg-crisis-light'
  const textColor = isCritical ? 'text-red-900' : 'text-crisis-dark'
  const iconColor = isCritical ? 'text-red-600' : 'text-crisis-dark'

  return (
    <div className={`${bgColor} border-l-4 ${borderColor} p-4 mx-6 mt-4 rounded shadow-md`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className={`h-6 w-6 ${iconColor}`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className={`text-sm font-bold ${textColor}`}>
            {isCritical ? '⚠️ 긴급 위기 상황 지원' : '위기 상황 지원 정보'}
          </h3>
          <div className="mt-2 text-sm text-gray-700 space-y-2">
            <p className="font-semibold">
              {isCritical
                ? '지금 위기 상황이라면, 즉시 전문가의 도움을 받으세요:'
                : '힘든 상황이라면 언제든지 전문가의 도움을 받을 수 있습니다:'}
            </p>
            <ul className="space-y-2 ml-2">
              <li className="flex items-start">
                <span className="mr-2">📞</span>
                <div>
                  <strong className="text-red-700">자살예방상담전화 1393</strong>
                  <span className="text-gray-600 text-xs ml-2">(24시간 무료 상담)</span>
                </div>
              </li>
              <li className="flex items-start">
                <span className="mr-2">💬</span>
                <div>
                  <strong className="text-blue-700">청소년전화 1388</strong>
                  <span className="text-gray-600 text-xs ml-2">(24시간 청소년 상담)</span>
                </div>
              </li>
              <li className="flex items-start">
                <span className="mr-2">🏥</span>
                <div>
                  <strong className="text-purple-700">정신건강위기상담전화 1577-0199</strong>
                  <span className="text-gray-600 text-xs ml-2">(24시간 정신건강 상담)</span>
                </div>
              </li>
              <li className="flex items-start">
                <span className="mr-2">🚨</span>
                <div>
                  <strong className="text-red-700">응급 119</strong>
                  <span className="text-gray-600 text-xs ml-2">(생명이 위급한 경우)</span>
                </div>
              </li>
            </ul>
            {isCritical && (
              <div className="mt-3 p-2 bg-red-100 border border-red-300 rounded">
                <p className="text-xs text-red-800 font-medium">
                  ⚠️ <strong>당신의 생명은 소중합니다.</strong> 지금 바로 위 번호로 전화하시거나,
                  가까운 응급실을 방문해 주세요. 당신 곁에는 도움을 줄 수 있는 사람들이 있습니다.
                </p>
              </div>
            )}
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="flex-shrink-0 ml-3 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="닫기"
        >
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  )
}
