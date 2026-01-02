# Security Testing Suite

Comprehensive security testing suite covering penetration testing, dependency scanning, SAST, DAST, infrastructure security, and third-party audits.

## Overview

This security testing suite provides:

1. **Penetration Testing**: OWASP Top 10 vulnerabilities, API security, authentication/authorization bypass
2. **Dependency Scanning**: CVE scanning, license compliance, outdated dependency detection
3. **SAST**: Static code analysis, secret detection, injection vulnerability detection
4. **DAST**: Runtime security testing, fuzzing, session management
5. **Infrastructure Security**: Container scanning, Kubernetes security, network security
6. **Third-Party Audit**: Comprehensive security audit simulation

## Test Structure

```
tests/security/
├── __init__.py
├── conftest.py                    # Pytest fixtures
├── test_penetration.py           # Penetration testing (OWASP Top 10)
├── test_dependency_scanning.py   # Dependency scanning
├── test_sast.py                  # Static Application Security Testing
├── test_dast.py                  # Dynamic Application Security Testing
├── test_infrastructure.py        # Infrastructure security
├── test_audit.py                 # Third-party security audit
├── security_runner.py            # Test runner script
└── README.md                     # This file
```

## Running Tests

### Run All Security Tests

```bash
pytest tests/security/ -v
```

### Run Specific Category

```bash
# Penetration testing
pytest tests/security/test_penetration.py -v

# Dependency scanning
pytest tests/security/test_dependency_scanning.py -v

# SAST
pytest tests/security/test_sast.py -v

# DAST
pytest tests/security/test_dast.py -v

# Infrastructure security
pytest tests/security/test_infrastructure.py -v

# Security audit
pytest tests/security/test_audit.py -v
```

### Run with Security Runner

```bash
python tests/security/security_runner.py
```

## Test Categories

### 1. Penetration Testing (`test_penetration.py`)

Tests OWASP Top 10 vulnerabilities:
- A01:2021 - Broken Access Control (Injection)
- A02:2021 - Cryptographic Failures (Broken Authentication)
- A03:2021 - Injection (Sensitive Data Exposure)
- A04:2021 - Insecure Design (XXE)
- A05:2021 - Security Misconfiguration (Broken Access Control)
- A06:2021 - Vulnerable Components (Security Misconfiguration)
- A07:2021 - Identification and Authentication Failures (XSS)
- A08:2021 - Software and Data Integrity Failures (Insecure Deserialization)
- A09:2021 - Security Logging Failures (Known Vulnerabilities)
- A10:2021 - Server-Side Request Forgery (Logging Failures)

Also includes:
- API security testing
- Authentication bypass attempts
- Authorization bypass attempts

### 2. Dependency Scanning (`test_dependency_scanning.py`)

- CVE scanning for known vulnerabilities
- License compliance checking
- Outdated dependency detection
- Transitive dependency scanning
- Integration with tools like Safety, pip-audit

### 3. SAST (`test_sast.py`)

Static code analysis for:
- Dangerous function detection (eval, exec, etc.)
- Hardcoded secret detection
- Injection vulnerability detection
- Weak cryptography detection
- Severity classification

### 4. DAST (`test_dast.py`)

Dynamic/runtime testing:
- Runtime security testing
- Input fuzzing
- Session management testing
- Error handling verification
- Stack trace exposure checks

### 5. Infrastructure Security (`test_infrastructure.py`)

- Container image scanning
- Dockerfile security best practices
- Kubernetes security (RBAC, secrets, network policies)
- Network security (TLS, firewall, DDoS protection)

### 6. Security Audit (`test_audit.py`)

Third-party security audit simulation:
- Authentication controls
- Authorization controls
- Data protection
- Infrastructure security
- Risk assessment
- Remediation recommendations

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Security Tests

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install safety pip-audit
      
      - name: Run security tests
        run: |
          pytest tests/security/ -v
      
      - name: Run dependency scanning
        run: |
          safety check
          pip-audit
      
      - name: Generate security report
        run: |
          python tests/security/security_runner.py
```

## Tools Integration

### Recommended Tools

1. **Dependency Scanning**:
   - `safety` - CVE scanning
   - `pip-audit` - Dependency vulnerability scanning
   - `pip-licenses` - License compliance

2. **SAST**:
   - `bandit` - Security linter
   - `semgrep` - Static analysis
   - `detect-secrets` - Secret detection

3. **DAST**:
   - `OWASP ZAP` - Web application security testing
   - Custom fuzzing tools

4. **Container Security**:
   - `trivy` - Container image scanning
   - `clair` - Container vulnerability scanner

5. **Infrastructure**:
   - `kube-score` - Kubernetes security scanning
   - `kubeaudit` - Kubernetes security audit

## Security Best Practices

1. **Run security tests regularly** (daily in CI/CD)
2. **Fix high/critical findings immediately**
3. **Review and update security tests** as threats evolve
4. **Integrate with dependency update tools**
5. **Monitor for new CVEs** in dependencies
6. **Conduct regular security audits**

## Reporting

The security test runner generates:
- Console output with test results
- JSON report (`security_test_report.json`)
- Summary statistics

## Notes

- Some tests require external tools (safety, trivy, etc.) - install as needed
- Tests may skip if required files/directories don't exist
- In production, integrate with actual security tools and services
- Regularly update CVE databases and security patterns

