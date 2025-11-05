'use client'

import { useState, useEffect } from 'react'
import { getConsentStatus, setConsentStatus } from '@/lib/auth'

interface ConsentModalProps {
  onConsent: (given: boolean) => void
}

export default function ConsentModal({ onConsent }: ConsentModalProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  useEffect(() => {
    // Check if consent was already given
    const consentGiven = getConsentStatus()
    if (!consentGiven) {
      setIsOpen(true)
    } else {
      onConsent(true)
    }
  }, [onConsent])

  const handleAccept = () => {
    setConsentStatus(true)
    closeModal()
    onConsent(true)
  }

  const handleDecline = () => {
    closeModal()
    onConsent(false)
  }

  const closeModal = () => {
    setIsClosing(true)
    setTimeout(() => {
      setIsOpen(false)
      setIsClosing(false)
    }, 300)
  }

  if (!isOpen) return null

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 bg-black transition-opacity duration-300 ${
        isClosing ? 'bg-opacity-0' : 'bg-opacity-50'
      }`}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          handleDecline()
        }
      }}
    >
      <div
        className={`bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto transition-all duration-300 ${
          isClosing ? 'scale-95 opacity-0' : 'scale-100 opacity-100'
        }`}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-counselor-main to-green-600 text-white p-6 rounded-t-2xl">
          <h2 className="text-2xl font-bold mb-2">마음이 AI 상담사를 시작하기 전에</h2>
          <p className="text-green-100 text-sm">
            서비스 이용 전 반드시 읽어주세요
          </p>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Important Notice */}
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-yellow-600"
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
              <div className="ml-3">
                <h3 className="text-sm font-bold text-yellow-800">중요 안내</h3>
                <p className="mt-1 text-sm text-yellow-700">
                  이 서비스는 <strong>AI 기반 상담 도우미</strong>로, 전문 정신건강 치료나 의료 서비스를
                  <strong className="underline"> 대체할 수 없습니다</strong>.
                </p>
              </div>
            </div>
          </div>

          {/* What is Maum-i */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              💚 마음이는 이런 서비스입니다
            </h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-1">✓</span>
                <span>공감적 경청과 정서적 지지를 제공하는 AI 대화 상대</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-1">✓</span>
                <span>인지행동치료(CBT) 기반의 자기 성찰 도구</span>
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2 mt-1">✓</span>
                <span>24시간 언제든 대화 가능한 심리 지원 서비스</span>
              </li>
            </ul>
          </div>

          {/* Limitations */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              ⚠️ AI의 한계
            </h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start">
                <span className="text-red-500 mr-2 mt-1">✗</span>
                <span>진단, 처방, 치료 등 의료 행위를 할 수 없습니다</span>
              </li>
              <li className="flex items-start">
                <span className="text-red-500 mr-2 mt-1">✗</span>
                <span>응급 상황이나 위기 상황을 직접 처리할 수 없습니다</span>
              </li>
              <li className="flex items-start">
                <span className="text-red-500 mr-2 mt-1">✗</span>
                <span>전문 상담사나 정신건강의학과 전문의를 대체할 수 없습니다</span>
              </li>
            </ul>
          </div>

          {/* Crisis Resources */}
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
            <h3 className="text-sm font-bold text-red-800 mb-2">
              🚨 위기 상황 시 즉시 연락하세요
            </h3>
            <div className="space-y-1 text-sm text-red-700">
              <p>
                <strong>자살예방상담전화:</strong> 1393 (24시간 무료)
              </p>
              <p>
                <strong>청소년전화:</strong> 1388
              </p>
              <p>
                <strong>정신건강위기상담전화:</strong> 1577-0199
              </p>
              <p>
                <strong>응급:</strong> 119
              </p>
            </div>
          </div>

          {/* Privacy */}
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              🔒 개인정보 보호
            </h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start">
                <span className="text-blue-500 mr-2 mt-1">•</span>
                <span>모든 대화는 암호화되어 안전하게 저장됩니다</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2 mt-1">•</span>
                <span>위기 감지 시 안전을 위해 로그가 기록됩니다</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-500 mr-2 mt-1">•</span>
                <span>데이터는 90일 후 자동으로 삭제됩니다</span>
              </li>
            </ul>
          </div>

          {/* Data Usage */}
          <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded">
            <p className="mb-2">
              <strong>AI 처리:</strong> OpenAI GPT-4o-mini 모델을 사용하며, 대화 내용은
              서비스 품질 향상을 위해 처리됩니다.
            </p>
            <p>
              <strong>동의 철회:</strong> 언제든 "새 대화" 버튼으로 대화를 종료하고
              새로 시작할 수 있습니다.
            </p>
          </div>
        </div>

        {/* Footer with Actions */}
        <div className="bg-gray-50 px-6 py-4 rounded-b-2xl flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleDecline}
            className="flex-1 px-6 py-3 bg-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-400 transition-colors"
          >
            나중에 하기
          </button>
          <button
            onClick={handleAccept}
            className="flex-1 px-6 py-3 bg-counselor-main text-white rounded-lg font-medium hover:bg-counselor-dark transition-colors shadow-lg hover:shadow-xl"
          >
            동의하고 시작하기
          </button>
        </div>
      </div>
    </div>
  )
}
