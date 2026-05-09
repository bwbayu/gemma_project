import { apiRequest } from './http'
import type { GenerationJob } from '../mock/types'

export async function getJob(jobId: string): Promise<GenerationJob> {
  return apiRequest<GenerationJob>(`/jobs/${jobId}`)
}

export function isTerminalJob(job: GenerationJob): boolean {
  if (job.status === 'completed' || job.status === 'failed') {
    return true
  }
  return job.stage === 'completed' || job.stage === 'failed'
}
