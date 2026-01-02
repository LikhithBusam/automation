# Performance Testing Suite

Comprehensive performance testing for the automaton system.

## Test Categories

### 1. Load Testing (`test_load.py`)
- **100 concurrent users**: Basic load test
- **500 concurrent users**: Medium load test
- **1000+ concurrent users**: Heavy load test
- **API endpoint throughput**: Measure requests per second
- **Workflow execution under load**: Test workflow performance
- **Response time measurement**: Measure at different load levels

### 2. Stress Testing (`test_stress.py`)
- **Find breaking point**: Gradually increase load until system breaks
- **System limits**: Test resource limits (CPU, memory, connections)
- **Recovery from overload**: Test system recovery
- **Connection pool exhaustion**: Test connection limits
- **Memory pressure**: Test under memory constraints
- **CPU saturation**: Test under CPU load

### 3. Soak Testing (`test_soak.py`)
- **Short soak (1 hour)**: Basic extended test
- **Medium soak (12 hours)**: Extended stability test
- **Memory leak detection**: Monitor for memory leaks
- **Resource utilization trends**: Track resource usage over time
- **Error rate monitoring**: Track errors during extended runs

### 4. Spike Testing (`test_spike.py`)
- **10x traffic spike**: Sudden 10x increase
- **100x traffic spike**: Massive sudden increase
- **Auto-scaling response**: Test scaling behavior
- **Recovery after spike**: Test post-spike recovery
- **Multiple spikes**: Test consecutive spikes
- **Gradual increase**: Test ramp-up scenarios

### 5. Benchmarks (`test_benchmarks.py`)
- **Agent response times**: Benchmark agent performance
- **Workflow execution times**: Benchmark workflow performance
- **Tool operation times**: Benchmark tool performance
- **Database query performance**: Benchmark database operations
- **Regression testing**: Detect performance regressions
- **Improvement tracking**: Track performance improvements

### 6. Continuous Monitoring (`test_monitoring.py`)
- **Metric recording**: Continuous metric collection
- **Alert generation**: Automatic alerting on thresholds
- **Monitoring loops**: Continuous monitoring
- **Metric aggregation**: Statistical analysis
- **Dashboard metrics**: Dashboard data generation
- **Trend detection**: Performance trend analysis

## Running Tests

### Run All Performance Tests
```bash
pytest tests/performance/ -v
```

### Run Specific Categories
```bash
# Load tests
pytest tests/performance/test_load.py -v

# Stress tests
pytest tests/performance/test_stress.py -v

# Soak tests (may take longer)
pytest tests/performance/test_soak.py -v

# Spike tests
pytest tests/performance/test_spike.py -v

# Benchmarks
pytest tests/performance/test_benchmarks.py -v

# Monitoring
pytest tests/performance/test_monitoring.py -v
```

### Run with Performance Report
```bash
python tests/performance/performance_runner.py
pytest tests/performance/ -v --json-report --json-report-file=performance_report.json
```

## Performance Targets

### Response Times
- **Light load (10 users)**: < 0.1s average, < 0.2s P95
- **Medium load (100 users)**: < 0.5s average, < 1.0s P95
- **Heavy load (1000 users)**: < 2.0s average, < 5.0s P99

### Throughput
- **Health endpoint**: > 1000 req/s
- **Workflow endpoint**: > 50 req/s
- **API endpoints**: > 100 req/s

### Resource Usage
- **Memory**: < 2000 MB peak
- **CPU**: < 90% average
- **Connections**: Handle 1000+ concurrent

### Success Rates
- **Light load**: > 99%
- **Medium load**: > 95%
- **Heavy load**: > 80%

## Continuous Monitoring

The performance monitoring system tracks:
- Response times
- Error rates
- Memory usage
- CPU usage
- Throughput
- Active connections

Alerts are generated when thresholds are exceeded:
- **Warning**: Response time > 1.0s, Error rate > 5%, Memory > 1GB, CPU > 80%
- **Critical**: Response time > 5.0s, Error rate > 20%, Memory > 2GB, CPU > 95%

## Notes

- Soak tests are compressed for CI/CD (1 minute = 1 hour simulation)
- For real 24-72 hour soak tests, run separately with extended durations
- Memory leak detection requires extended monitoring periods
- Spike tests verify system can handle sudden traffic increases
- Benchmarks establish baseline performance metrics

