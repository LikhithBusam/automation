# AutoGen Development Assistant Helm Chart

Production-ready Helm chart for deploying the AutoGen Development Assistant to Kubernetes.

## Installation

### Add Repository (if using chart repository)

```bash
helm repo add automaton https://charts.example.com
helm repo update
```

### Install from Local Chart

```bash
cd helm/automaton
helm install automaton . \
  --namespace automaton-production \
  --create-namespace \
  --set secrets.openrouterApiKey=your-key \
  --set secrets.githubToken=your-token
```

### Install with Custom Values

```bash
helm install automaton . \
  -f values.yaml \
  -f values-production.yaml \
  --namespace automaton-production \
  --create-namespace
```

## Configuration

### Required Values

Set these values via `--set` or in a values file:

```yaml
secrets:
  openrouterApiKey: "your-key"
  githubToken: "your-token"
  postgresPassword: "secure-password"
  redisPassword: "secure-password"
  jwtSecretKey: "secure-random-key"
```

### Common Customizations

#### Resource Limits

```yaml
app:
  resources:
    requests:
      cpu: "1000m"
      memory: "2Gi"
    limits:
      cpu: "4000m"
      memory: "8Gi"
```

#### Replica Count

```yaml
app:
  replicas: 5
  autoscaling:
    minReplicas: 5
    maxReplicas: 20
```

#### Ingress Configuration

```yaml
app:
  ingress:
    enabled: true
    hosts:
      - host: automaton.yourdomain.com
        paths:
          - path: /
            pathType: Prefix
```

## Upgrading

```bash
helm upgrade automaton . \
  --namespace automaton-production \
  --set app.image.tag=2.1.0
```

## Uninstalling

```bash
helm uninstall automaton --namespace automaton-production
```

## Chart Structure

```
helm/automaton/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
├── templates/              # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── pvc.yaml
│   └── _helpers.tpl        # Template helpers
└── README.md
```

## Values Reference

See `values.yaml` for all configurable options.

## Troubleshooting

### Check Release Status

```bash
helm status automaton --namespace automaton-production
```

### View Rendered Templates

```bash
helm template automaton . --debug
```

### Rollback

```bash
helm rollback automaton --namespace automaton-production
```

