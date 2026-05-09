import { apiRequest } from './http'
import type { GenerationJob, QuestionItem } from '../mock/types'

interface CreateQuestionResponse {
  question: QuestionItem
  job: GenerationJob
}

export async function listWorkspaceQuestions(workspaceId: string): Promise<QuestionItem[]> {
  return apiRequest<QuestionItem[]>(`/workspaces/${workspaceId}/questions`)
}

export async function createQuestionFromText(workspaceId: string, text: string): Promise<CreateQuestionResponse> {
  const formData = new FormData()
  formData.append('text', text)
  return apiRequest<CreateQuestionResponse>(`/workspaces/${workspaceId}/questions`, {
    method: 'POST',
    body: formData,
    headers: {
      Accept: 'application/json',
    },
  })
}

export async function createQuestionFromImage(workspaceId: string, file: File): Promise<CreateQuestionResponse> {
  const formData = new FormData()
  formData.append('image', file)
  return apiRequest<CreateQuestionResponse>(`/workspaces/${workspaceId}/questions`, {
    method: 'POST',
    body: formData,
    headers: {
      Accept: 'application/json',
    },
  })
}
