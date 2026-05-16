import { apiRequest } from './http'
import type { GenerationJob, QuestionItem } from '../types/types'

interface CreateQuestionResponse {
  question: QuestionItem
  job: GenerationJob
}

/** Fetch all questions for a workspace, ordered newest first. */
export async function listWorkspaceQuestions(workspaceId: string): Promise<QuestionItem[]> {
  return apiRequest<QuestionItem[]>(`/workspaces/${workspaceId}/questions`)
}

/** Submit a text question to the workspace and start a generation job. */
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

/** Upload an image file as a question source and start a generation job. */
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
