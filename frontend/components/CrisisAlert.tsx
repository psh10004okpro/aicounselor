'use client'

import { useState } from 'react'

export default function CrisisAlert() {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div className="bg-crisis-light border-l-4 border-crisis-main p-4 mx-6 mt-4 rounded">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-6 w-6 text-crisis-dark"
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
          <h3 className="text-sm font-medium text-crisis-dark">
            Crisis Resources Available
          </h3>
          <div className="mt-2 text-sm text-gray-700 space-y-1">
            <p className="font-semibold">
              If you're in crisis, please reach out for immediate help:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                <strong>988 Suicide & Crisis Lifeline</strong> - Call or text
                988 (24/7)
              </li>
              <li>
                <strong>Crisis Text Line</strong> - Text HOME to 741741
              </li>
              <li>
                <strong>Emergency</strong> - Call 911
              </li>
            </ul>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="flex-shrink-0 ml-3 text-gray-400 hover:text-gray-600"
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
