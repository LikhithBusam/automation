# Kubernetes Deployment Guide

This directory contains all Kubernetes manifests for deploying the AutoGen Development Assistant to a Kubernetes cluster.

## Directory Structure

```
k8s/
├── namespace.yaml                    # Namespace definitions
├── configmaps/                       # Configuration maps
│   ├── app-config.yaml
│   └── mcp-config.yaml
├── secrets/                          # Secret templates
│   └── app-secrets.yaml.template
├── persistent-volumes/               # PVC definitions
│   └── data-volumes.yaml
├── deployments/                      # Deployment manifests
│   ├── app-deployment.yaml
│   ├── mcp-github-deployment.yaml
│   ├── mcp-filesystem-deployment.yaml
│   ├── mcp-memory-deployment.yaml
│   ├── mcp-codebasebuddy-deployment.yaml
│   ├── postgres-deployment.yaml
│   └── redis-deployment.yaml
├── services/                         # Service definitions
│   └── app-services.yaml
├── ingress/                          # Ingress configurations
│   └── app-ingress.yaml
├── hpa/                              # Horizontal Pod Autoscalers
│   └── app-hpa.yaml
├── rbac/                             # RBAC configurations
│   └── service-accounts.yaml
└── network-policies/                 # Network policies
    └── network-policies.yaml
```

## Prerequisites

1. Kubernetes cluster (v1.24+)
2. kubectl configured to access your cluster
3. Ingress controller installed (NGINX, Traefik, etc.)
4. Storage class configured for persistent volumes
5. Cert-manager (optional, for TLS certificates)

## Deployment Steps

### 1. Create Namespaces

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Create Secrets

**IMPORTANT**: Replace placeholder values with actual secrets before applying.

```bash
# Edit the secrets file
cp k8s/secrets/app-secrets.yaml.template k8s/secrets/app-secrets.yaml
# Edit app-secrets.yaml with your actual values
kubectl apply -f k8s/secrets/app-secrets.yaml
```

Or use kubectl to create secrets directly:

```bash
kubectl create secret generic automaton-app-secrets \
  --from-literal=OPENROUTER_API_KEY='your-key' \
  --from-literal=GITHUB_TOKEN='your-token' \
  --namespace=automaton-production
```

### 3. Create ConfigMaps

```bash
kubectl apply -f k8s/configmaps/
```

### 4. Create Persistent Volume Claims

```bash
kubectl apply -f k8s/persistent-volumes/
```

### 5. Deploy Services

```bash
# Deploy database and cache first
kubectl apply -f k8s/deployments/postgres-deployment.yaml
kubectl apply -f k8s/deployments/redis-deployment.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l component=postgres -n automaton-production --timeout=300s

# Deploy MCP servers
kubectl apply -f k8s/deployments/mcp-*.yaml

# Deploy main application
kubectl apply -f k8s/deployments/app-deployment.yaml
```

### 6. Create Services

```bash
kubectl apply -f k8s/services/
```

### 7. Create Ingress

```bash
# Update k8s/ingress/app-ingress.yaml with your domain
kubectl apply -f k8s/ingress/
```

### 8. Create RBAC

```bash
kubectl apply -f k8s/rbac/
```

### 9. Create Network Policies

```bash
kubectl apply -f k8s/network-policies/
```

### 10. Create Horizontal Pod Autoscalers

```bash
kubectl apply -f k8s/hpa/
```

## Verification

Check deployment status:

```bash
# Check all pods
kubectl get pods -n automaton-production

# Check services
kubectl get svc -n automaton-production

# Check ingress
kubectl get ingress -n automaton-production

# View logs
kubectl logs -f deployment/automaton-app -n automaton-production
```

## Using Helm (Recommended)

For easier management, use the Helm chart:

```bash
cd helm/automaton
helm install automaton . -n automaton-production --create-namespace
```

## Resource Requirements

### Minimum Requirements
- 3 nodes with 4 CPU cores and 8GB RAM each
- 150GB storage for persistent volumes

### Recommended Requirements
- 5 nodes with 8 CPU cores and 16GB RAM each
- 300GB storage for persistent volumes

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n automaton-production
kubectl logs <pod-name> -n automaton-production
```

### Database connection issues
```bash
kubectl exec -it deployment/automaton-postgres -n automaton-production -- psql -U automaton_user -d automaton
```

### Storage issues
```bash
kubectl get pvc -n automaton-production
kubectl describe pvc <pvc-name> -n automaton-production
```

## Scaling

### Manual Scaling
```bash
kubectl scale deployment automaton-app --replicas=5 -n automaton-production
```

### Automatic Scaling
HPA is configured to scale based on CPU and memory usage. Check status:

```bash
kubectl get hpa -n automaton-production
```

