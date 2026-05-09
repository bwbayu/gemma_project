import { apiRequest } from './http'
import type { Workspace } from '../mock/types'

export async function getActiveWorkspace(): Promise<Workspace | null> {
  return apiRequest<Workspace | null>('/workspaces/active')
}

export async function createWorkspace(title: string, description: string): Promise<Workspace> {
  return apiRequest<Workspace>('/workspaces', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  })
}

export async function openWorkspace(formRef: string): Promise<Workspace> {
  return apiRequest<Workspace>('/workspaces/open', {
    method: 'POST',
    body: JSON.stringify({ formRef }),
  })
}
