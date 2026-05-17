import { apiRequest } from './http'
import type { GenerationJob } from '../types/types'

/** Fetch the current state of a generation job by its ID. */
export async function getJob(jobId: string): Promise<GenerationJob> {
  return apiRequest<GenerationJob>(`/jobs/${jobId}`)
}

/** Return true if the job has reached a final state (completed or failed). */
export function isTerminalJob(job: GenerationJob): boolean {
  if (job.status === 'completed' || job.status === 'failed') {
    return true
  }
  return job.stage === 'completed' || job.stage === 'failed'
}
