Client : 
npm install
npm run dev

Server : 
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-dir src

Flow di Docs Backend
- Create workspace : /api/v1/workspaces -> copy workspaceId
- Create question (perlu workspaceId) : /api/v1/workspaces/{workspaces_id}/questions -> upload question dan (opsional) copy jobId (buat ngeliat progress) dan questionItemId (buat approve)
- Melihat progress multi-agent (perlu jobId) : /api/v1/jobs/{job_id} -> bisa juga ngeliat langsung di terminal backend (ambil questionItemId)
- (KHAIRI) approve  question (questionItemId) : /api/v1/questions/{question_id}/approve -> DONE