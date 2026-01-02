# Docker Build Guide

This directory contains production-ready Dockerfiles for all services in the AutoGen Development Assistant.

## Dockerfiles

- `Dockerfile.app` - Main application
- `Dockerfile.mcp-github` - GitHub MCP Server
- `Dockerfile.mcp-filesystem` - Filesystem MCP Server
- `Dockerfile.mcp-memory` - Memory MCP Server
- `Dockerfile.mcp-codebasebuddy` - CodeBaseBuddy MCP Server
- `Dockerfile.api-gateway` - API Gateway (optional)

## Building Images

### Build All Images

```bash
# From project root
docker build -f docker/Dockerfile.app -t automaton-app:2.0.0 .
docker build -f docker/Dockerfile.mcp-github -t automaton-mcp-github:2.0.0 .
docker build -f docker/Dockerfile.mcp-filesystem -t automaton-mcp-filesystem:2.0.0 .
docker build -f docker/Dockerfile.mcp-memory -t automaton-mcp-memory:2.0.0 .
docker build -f docker/Dockerfile.mcp-codebasebuddy -t automaton-mcp-codebasebuddy:2.0.0 .
```

### Build with Build Arguments

```bash
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=2.0.0 \
  -f docker/Dockerfile.app \
  -t automaton-app:2.0.0 \
  .
```

## Multi-Stage Build Benefits

All Dockerfiles use multi-stage builds for:
- **Smaller image sizes** - Only runtime dependencies in final image
- **Better security** - No build tools in production image
- **Faster deployments** - Smaller images transfer faster

## Image Optimization

### Layer Caching
- Dependencies are copied first for better cache utilization
- Application code is copied last to maximize cache hits

### Security Best Practices
- Non-root user execution
- Minimal base images (python:3.11-slim)
- No unnecessary packages
- Proper file permissions

## Pushing to Registry

```bash
# Tag for registry
docker tag automaton-app:2.0.0 your-registry.com/automaton-app:2.0.0

# Push to registry
docker push your-registry.com/automaton-app:2.0.0
```

## Image Sizes

Expected sizes (approximate):
- `automaton-app`: ~500MB
- `automaton-mcp-github`: ~200MB
- `automaton-mcp-filesystem`: ~200MB
- `automaton-mcp-memory`: ~250MB
- `automaton-mcp-codebasebuddy`: ~800MB (includes vector search libraries)

## Health Checks

All images include health checks:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:PORT/health || exit 1
```

## Testing Images Locally

```bash
# Run container
docker run -d \
  -p 8000:8000 \
  -e OPENROUTER_API_KEY=your-key \
  automaton-app:2.0.0

# Check health
curl http://localhost:8000/health

# View logs
docker logs <container-id>
```

