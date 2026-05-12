import { apiRequest } from './http'
import type { Workspace } from '../mock/types'

/** Return the currently active workspace, or null if none has been created yet. */
export async function getActiveWorkspace(): Promise<Workspace | null> {
  return apiRequest<Workspace | null>('/workspaces/active')
}

/** Create a new Google Form-backed workspace with the given title and description. */
export async function createWorkspace(title: string, description: string): Promise<Workspace> {
  return apiRequest<Workspace>('/workspaces', {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  })
}
