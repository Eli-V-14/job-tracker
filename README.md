# job-tracker
Job application tracker built as a microservices app: a Flask web app for logging applications and updating their status, a stats service that analyzes your job search, and Redis for storage. Containerized with Docker, pushed to Google Artifact Registry, and deployed to Google Kubernetes Engine with Deployments, Services, and a public load balancer. Built for CSC5201 Lab 7.

## Architecture

```
browser -> tracker (LoadBalancer :80) -> stats (ClusterIP :5000)
                    |                             |
                    \-> redis (ClusterIP :6379) <-/
```

| Service | Job | Exposed |
|---|---|---|
| `tracker` | Web UI: add, update, delete, and filter applications | Public (LoadBalancer) |
| `stats` | Computes totals, response rate, offer rate, average salary | Internal (ClusterIP) |
| `redis` | Stores each application as a hash plus a `next_id` counter | Internal (ClusterIP) |

If the stats service is down, the tracker still works and only hides the stats panel.

## Run locally

```
docker compose up --build
```

Open http://localhost:8080.

## Deploy to GKE (PowerShell)

```
gcloud artifacts repositories create job-tracker --repository-format=docker --location=us-central1
gcloud auth configure-docker us-central1-docker.pkg.dev

docker build -t us-central1-docker.pkg.dev/gke-flask-kubernetes/job-tracker/tracker:v1 .
docker build -t us-central1-docker.pkg.dev/gke-flask-kubernetes/job-tracker/stats:v1 ./stats
docker push us-central1-docker.pkg.dev/gke-flask-kubernetes/job-tracker/tracker:v1
docker push us-central1-docker.pkg.dev/gke-flask-kubernetes/job-tracker/stats:v1

gcloud container clusters create-auto job-tracker-cluster --region=us-central1
gcloud container clusters get-credentials job-tracker-cluster --region=us-central1
kubectl apply -f k8s/
kubectl get service tracker --watch
```

## Clean up

```
kubectl delete -f k8s/
gcloud container clusters delete job-tracker-cluster --region=us-central1
```
