#!/usr/bin/env python3
"""
Production Readiness Assessment
Comprehensive check of all systems for production deployment
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

class ProductionChecker:
    def __init__(self):
        self.results = {
            'critical': [],
            'warnings': [],
            'passed': [],
            'info': []
        }
        
    def check_section(self, title):
        print(f"\n{'='*80}")
        print(f"{title}")
        print('='*80)
        
    def critical(self, item, status, details=""):
        result = f"{'✓' if status else '✗'} {item}"
        if details:
            result += f"\n   {details}"
        if status:
            self.results['passed'].append(item)
        else:
            self.results['critical'].append(item)
        print(f"{'[✓]' if status else '[✗ CRITICAL]'} {item}")
        if details:
            print(f"   {details}")
            
    def warning(self, item, status, details=""):
        result = f"{'✓' if status else '⚠'} {item}"
        if details:
            result += f"\n   {details}"
        if status:
            self.results['passed'].append(item)
        else:
            self.results['warnings'].append(item)
        print(f"{'[✓]' if status else '[⚠ WARNING]'} {item}")
        if details:
            print(f"   {details}")
            
    def info(self, item, details=""):
        self.results['info'].append(item)
        print(f"[ℹ] {item}")
        if details:
            print(f"   {details}")

def main():
    checker = ProductionChecker()
    
    print("\n" + "="*80)
    print("PRODUCTION READINESS ASSESSMENT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 1. CRITICAL INFRASTRUCTURE
    checker.check_section("1. CRITICAL INFRASTRUCTURE")
    
    # Environment files
    env_exists = Path('.env').exists()
    checker.critical(
        "Environment file (.env)",
        env_exists,
        "Contains API keys and configuration" if env_exists else "MISSING - Copy .env.example"
    )
    
    env_example = Path('.env.example').exists()
    checker.warning(
        "Environment template (.env.example)",
        env_example,
        "Template for users to configure their environment"
    )
    
    # Config files
    config_files = [
        'config/autogen_agents.yaml',
        'config/autogen_workflows.yaml',
        'config/config.yaml'
    ]
    for config in config_files:
        exists = Path(config).exists()
        checker.critical(f"Config: {config}", exists)
    
    # MCP Servers
    checker.check_section("2. MCP SERVERS")
    
    server_pids = [
        ('GitHub Server', 'daemon/pids/github_server.pid'),
        ('Filesystem Server', 'daemon/pids/filesystem_server.pid'),
        ('Memory Server', 'daemon/pids/memory_server.pid'),
    ]
    
    for name, pid_file in server_pids:
        if Path(pid_file).exists():
            with open(pid_file) as f:
                pid = f.read().strip()
            try:
                import psutil
                proc = psutil.Process(int(pid))
                checker.info(f"{name}", f"Running (PID: {pid}, Status: {proc.status()})")
            except:
                checker.warning(f"{name}", False, f"PID file exists but process not running")
        else:
            checker.warning(f"{name}", False, "Not running - start with scripts/start_mcp_servers.py")
    
    # 3. DATABASE & STORAGE
    checker.check_section("3. DATABASE & STORAGE")
    
    sqlite_db = Path('data/memory.db')
    checker.info(
        "SQLite Database",
        f"{'Exists' if sqlite_db.exists() else 'Will be created on first use'}"
    )
    
    fallback = Path('data/memory_fallback.json')
    checker.info(
        "Fallback Storage",
        f"{'Active' if fallback.exists() else 'Ready to create'}"
    )
    
    # 4. SECURITY
    checker.check_section("4. SECURITY")
    
    gitignore = Path('.gitignore').exists()
    checker.critical(".gitignore present", gitignore)
    
    if gitignore:
        with open('.gitignore') as f:
            gitignore_content = f.read()
        
        critical_patterns = [
            ('.env', 'Environment variables'),
            ('credentials', 'Credential files'),
            ('__pycache__', 'Python cache'),
            ('.pyc', 'Compiled Python files')
        ]
        for pattern, desc in critical_patterns:
            in_gitignore = pattern in gitignore_content
            checker.critical(
                f"Excludes {desc}",
                in_gitignore,
                "Prevents sensitive data in git"
            )
    
    # Check for exposed secrets
    exposed_files = []
    sensitive_files = ['.env', 'credentials.json', 'config/google_credentials.json']
    for sf in sensitive_files:
        if Path(sf).exists():
            # Check if tracked by git
            import subprocess
            try:
                result = subprocess.run(
                    ['git', 'ls-files', '--error-unmatch', sf],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    exposed_files.append(sf)
            except:
                pass
    
    if exposed_files:
        checker.critical(
            "No sensitive files in git",
            False,
            f"EXPOSED: {', '.join(exposed_files)}"
        )
    else:
        checker.critical("No sensitive files in git", True)
    
    # 5. API KEYS & CREDENTIALS
    checker.check_section("5. API KEYS & CREDENTIALS")
    
    if env_exists:
        with open('.env') as f:
            env_content = f.read()
        
        # Check for required keys
        required_keys = {
            'OPENROUTER_API_KEY': 'OpenRouter API (for LLM)',
            'GITHUB_TOKEN': 'GitHub integration',
            'GROQ_API_KEY': 'Groq fallback (optional)',
            'GEMINI_API_KEY': 'Gemini fallback (optional)'
        }
        
        for key, purpose in required_keys.items():
            has_key = key in env_content and not env_content.split(key)[1].split('\n')[0].strip() in ['', '=', '=your_key_here']
            if key == 'OPENROUTER_API_KEY':
                checker.critical(f"{key}", has_key, purpose)
            else:
                checker.warning(f"{key}", has_key, purpose)
    
    # 6. DEPENDENCIES
    checker.check_section("6. DEPENDENCIES")
    
    requirements = Path('requirements.txt').exists()
    checker.critical("requirements.txt present", requirements)
    
    if requirements:
        with open('requirements.txt') as f:
            deps = f.read()
        
        critical_deps = ['pyautogen', 'httpx', 'fastmcp', 'rich']
        for dep in critical_deps:
            has_dep = dep in deps.lower()
            checker.critical(f"Dependency: {dep}", has_dep)
    
    # Try importing critical packages
    import_checks = [
        ('autogen', 'AutoGen framework'),
        ('httpx', 'HTTP client'),
        ('rich', 'Terminal formatting'),
        ('yaml', 'YAML parsing'),
        ('dotenv', 'Environment loading')
    ]
    
    for module, desc in import_checks:
        try:
            __import__(module)
            checker.info(f"Import {module}", f"✓ Available ({desc})")
        except ImportError:
            checker.critical(f"Import {module}", False, f"MISSING - pip install {module}")
    
    # 7. TESTS
    checker.check_section("7. TESTING STATUS")
    
    test_files = list(Path('.').glob('test_*.py'))
    checker.info(f"Test files found", f"{len(test_files)} test scripts")
    
    # 8. DOCUMENTATION
    checker.check_section("8. DOCUMENTATION")
    
    docs = [
        ('README.md', 'Main documentation'),
        ('API_REFERENCE.md', 'API documentation'),
        ('docs/QUICK_START.md', 'Quick start guide'),
        ('docs/TROUBLESHOOTING.md', 'Troubleshooting guide'),
        ('PRODUCTION_CHECKLIST.md', 'Production checklist')
    ]
    
    for doc, desc in docs:
        exists = Path(doc).exists()
        checker.warning(f"{doc}", exists, desc)
    
    # 9. PERFORMANCE
    checker.check_section("9. PERFORMANCE & OPTIMIZATION")
    
    # Check for cache files
    cache_dirs = list(Path('.').rglob('__pycache__'))
    if cache_dirs:
        checker.info("Python cache", f"{len(cache_dirs)} __pycache__ directories (normal)")
    
    # Check data directory size
    if Path('data').exists():
        total_size = sum(f.stat().st_size for f in Path('data').rglob('*') if f.is_file())
        checker.info("Data directory size", f"{total_size / 1024 / 1024:.1f} MB")
    
    # FINAL SUMMARY
    print("\n" + "="*80)
    print("PRODUCTION READINESS SUMMARY")
    print("="*80)
    
    total = len(checker.results['passed']) + len(checker.results['critical']) + len(checker.results['warnings'])
    passed = len(checker.results['passed'])
    
    print(f"\n✓ Passed:   {passed}")
    print(f"✗ Critical: {len(checker.results['critical'])}")
    print(f"⚠ Warnings: {len(checker.results['warnings'])}")
    print(f"ℹ Info:     {len(checker.results['info'])}")
    
    if checker.results['critical']:
        print("\n🔴 CRITICAL ISSUES (Must fix before production):")
        for issue in checker.results['critical']:
            print(f"   - {issue}")
    
    if checker.results['warnings']:
        print("\n🟡 WARNINGS (Recommended to fix):")
        for issue in checker.results['warnings']:
            print(f"   - {issue}")
    
    # Production readiness verdict
    print("\n" + "="*80)
    if len(checker.results['critical']) == 0:
        if len(checker.results['warnings']) == 0:
            print("✅ PRODUCTION READY - No critical issues or warnings")
            print("   Status: EXCELLENT - Ready for deployment")
        elif len(checker.results['warnings']) <= 3:
            print("✅ PRODUCTION READY - No critical issues")
            print("   Status: GOOD - Minor warnings present but not blocking")
        else:
            print("⚠️  PRODUCTION READY WITH CAUTION")
            print("   Status: ACCEPTABLE - Address warnings when possible")
    else:
        print("❌ NOT PRODUCTION READY")
        print(f"   Status: BLOCKED - {len(checker.results['critical'])} critical issue(s) must be fixed")
    
    print("="*80 + "\n")
    
    return len(checker.results['critical']) == 0

if __name__ == "__main__":
    ready = main()
    sys.exit(0 if ready else 1)
