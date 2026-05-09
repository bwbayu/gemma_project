import { apiRequest } from './http'
import type { GenerationJob, QuestionItem, ReviewResult } from '../mock/types'

export interface FormLinks {
  workspaceId: string
  formEditUrl: string
  formResponderUrl: string
}

export interface QuestionDecisionResponse {
  question: QuestionItem
  review: ReviewResult
  formLinks: FormLinks
  job?: GenerationJob | null
}

export async function getQuestionReview(questionId: string): Promise<ReviewResult> {
  return apiRequest<ReviewResult>(`/questions/${questionId}/review`)
}

export async function approveQuestion(questionId: string): Promise<QuestionDecisionResponse> {
  return apiRequest<QuestionDecisionResponse>(`/questions/${questionId}/approve`, {
    method: 'POST',
  })
}

export async function regenerateQuestion(questionId: string): Promise<QuestionDecisionResponse> {
  return apiRequest<QuestionDecisionResponse>(`/questions/${questionId}/regenerate`, {
    method: 'POST',
  })
}

export async function discardQuestion(questionId: string): Promise<QuestionDecisionResponse> {
  return apiRequest<QuestionDecisionResponse>(`/questions/${questionId}/discard`, {
    method: 'POST',
  })
}
