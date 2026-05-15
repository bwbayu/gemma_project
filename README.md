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

firebase deploy

-------

asia-southeast2-docker.pkg.dev/asas-demo/physicsanimator

physicsanimator-backend@asas-demo.iam.gserviceaccount.com

docker build -t asia-southeast2-docker.pkg.dev/asas-demo/physicsanimator/backend:latest .
docker push asia-southeast2-docker.pkg.dev/asas-demo/physicsanimator/backend:latest

gcloud secrets create physicsanimator-google-credentials --data-file=server/credentials.json
projects/42918010232/secrets/physicsanimator-google-credentials

gcloud secrets create physicsanimator-google-token --data-file=server/token.json
projects/42918010232/secrets/physicsanimator-google-token