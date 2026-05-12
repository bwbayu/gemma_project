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

/** Fetch the review payload for a question once its generation job has completed. */
export async function getQuestionReview(questionId: string): Promise<ReviewResult> {
  return apiRequest<ReviewResult>(`/questions/${questionId}/review`)
}

/** Approve the question, appending its animation to the linked Google Form. */
export async function approveQuestion(questionId: string): Promise<QuestionDecisionResponse> {
  return apiRequest<QuestionDecisionResponse>(`/questions/${questionId}/approve`, {
    method: 'POST',
  })
}

/** Request a new generation run for a question that was reviewed but not approved. */
export async function regenerateQuestion(questionId: string): Promise<QuestionDecisionResponse> {
  return apiRequest<QuestionDecisionResponse>(`/questions/${questionId}/regenerate`, {
    method: 'POST',
  })
}

/** Mark a question as discarded so it is excluded from the form. */
export async function discardQuestion(questionId: string): Promise<QuestionDecisionResponse> {
  return apiRequest<QuestionDecisionResponse>(`/questions/${questionId}/discard`, {
    method: 'POST',
  })
}
