#!/usr/bin/env python3
"""
Graphyte OSINT Platform - Validation & Health Check Script

Validates:
- Python environment and dependencies
- Backend service connectivity
- API endpoints
- Database connections
- WebSocket functionality
"""

import subprocess
import sys
import os
import json
import time
from typing import Dict, Tuple, List

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str):
    """Print section header."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def check_python_version() -> bool:
    """Check Python version is 3.10+."""
    print_header("Python Environment")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 10:
        print_success(f"Python {version_str}")
        return True
    else:
        print_error(f"Python {version_str} (required: 3.10+)")
        return False


def check_dependencies() -> bool:
    """Check required Python packages are installed."""
    print_header("Python Dependencies")
    
    required = [
        "fastapi",
        "uvicorn",
        "celery",
        "redis",
        "pydantic",
        "requests",
    ]
    
    all_installed = True
    for package in required:
        try:
            __import__(package)
            print_success(f"{package}")
        except ImportError:
            print_error(f"{package} (not installed)")
            all_installed = False
    
    return all_installed


def check_backend_imports() -> bool:
    """Check backend modules can be imported."""
    print_header("Backend Module Imports")
    
    imports = [
        ("backend.settings", "Settings"),
        ("backend.logging_config", "logger"),
        ("backend.services", "ServiceRegistry"),
        ("backend.schemas", "Investigation"),
        ("backend.app", "app"),
        ("backend.routes.auth", "router"),
        ("backend.routes.investigations", "router"),
        ("backend.routes.playbooks", "router"),
    ]
    
    all_imported = True
    for module, name in imports:
        try:
            exec(f"from {module} import {name}")
            print_success(f"{module}")
        except Exception as e:
            print_error(f"{module}: {str(e)[:60]}")
            all_imported = False
    
    return all_imported


def check_service_connectivity() -> Dict[str, bool]:
    """Check connectivity to backend services."""
    print_header("Service Connectivity")
    
    services = {
        "Redis": ("localhost", 6379),
        "PostgreSQL": ("localhost", 5432),
        "Neo4j (Bolt)": ("localhost", 7687),
        "Weaviate": ("localhost", 8080),
    }
    
    results = {}
    for name, (host, port) in services.items():
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                if result == 0:
                    print_success(f"{name} ({host}:{port})")
                    results[name] = True
                else:
                    print_warning(f"{name} ({host}:{port}) - not running")
                    results[name] = False
        except Exception as e:
            print_warning(f"{name} - {str(e)[:40]}")
            results[name] = False
    
    return results


def check_backend_health(api_url: str = "http://localhost:8000") -> bool:
    """Check backend health endpoint."""
    print_header("Backend API Health")
    
    try:
        import requests
        
        # Try health endpoint
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"API Health: {api_url}/health")
            health_data = response.json()
            status = health_data.get("status", "unknown")
            print_success(f"Status: {status}")
            
            # Check services
            services = health_data.get("services", {})
            for service, info in services.items():
                service_status = info.get("status", "unknown")
                if service_status == "healthy":
                    print_success(f"  {service}: {service_status}")
                else:
                    print_warning(f"  {service}: {service_status}")
            
            return True
        else:
            print_error(f"Health endpoint returned {response.status_code}")
            return False
    
    except Exception as e:
        print_warning(f"Backend not responding: {str(e)[:60]}")
        return False


def check_api_endpoints(api_url: str = "http://localhost:8000") -> bool:
    """Check critical API endpoints."""
    print_header("API Endpoints")
    
    try:
        import requests
        
        endpoints = [
            ("GET", "/health", "Health Check"),
            ("GET", "/ready", "Readiness Check"),
            ("GET", "/api/playbooks", "List Playbooks"),
            ("GET", "/api/modules", "List Modules"),
            ("GET", "/api/investigations", "List Investigations"),
        ]
        
        all_working = True
        for method, path, description in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{api_url}{path}", timeout=5)
                elif method == "POST":
                    response = requests.post(f"{api_url}{path}", timeout=5)
                
                if response.status_code in (200, 201):
                    print_success(f"{method} {path} - {description}")
                else:
                    print_warning(f"{method} {path} - Status {response.status_code}")
                    all_working = False
            except Exception as e:
                print_warning(f"{method} {path} - {str(e)[:40]}")
                all_working = False
        
        return all_working
    
    except Exception as e:
        print_error(f"Cannot test endpoints: {str(e)}")
        return False


def check_frontend() -> bool:
    """Check if frontend is running."""
    print_header("Frontend")
    
    try:
        import requests
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print_success("Frontend running at http://localhost:3000")
            return True
        else:
            print_warning(f"Frontend returned {response.status_code}")
            return False
    except Exception as e:
        print_warning(f"Frontend not running: {str(e)[:40]}")
        return False


def test_module_import() -> bool:
    """Test that a sample module can be imported."""
    print_header("Module Framework")
    
    try:
        from backend.modules.base import BaseModule
        from backend.modules.registry import module_registry
        
        print_success("BaseModule class available")
        print_success("Module registry available")
        
        # Try to list registered modules
        count = len(module_registry._modules)
        print_success(f"Registered modules: {count}")
        
        return True
    except Exception as e:
        print_error(f"Module framework error: {str(e)}")
        return False


def check_environment_file() -> bool:
    """Check .env file exists and has key variables."""
    print_header("Environment Configuration")
    
    if not os.path.exists(".env"):
        print_warning(".env file not found (using .env.example as template)")
        if os.path.exists(".env.example"):
            print_success(".env.example found - copy to .env to customize")
        return False
    
    print_success(".env file found")
    
    # Check for key variables
    required_vars = [
        "REDIS_URL",
        "DATABASE_URL",
        "NEO4J_URI",
    ]
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive parts
                masked = value[:30] + "..." if len(value) > 30 else value
                print_success(f"{var}: {masked}")
            else:
                print_warning(f"{var}: not set")
        
        return True
    except Exception as e:
        print_warning(f"Cannot read .env: {str(e)}")
        return False


def run_all_checks() -> Tuple[int, int]:
    """Run all validation checks and return pass/fail counts."""
    print(f"\n{BOLD}{BLUE}GRAPHYTE OSINT PLATFORM - VALIDATION SUITE{RESET}\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Backend Imports", check_backend_imports),
        ("Environment", check_environment_file),
        ("Module Framework", test_module_import),
        ("Service Connectivity", lambda: all(check_service_connectivity().values())),
        ("Backend Health", check_backend_health),
        ("API Endpoints", check_api_endpoints),
        ("Frontend", check_frontend),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_func in checks:
        try:
            result = check_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_error(f"{name} check failed: {str(e)}")
            failed += 1
    
    return passed, failed


def main():
    """Run validation suite."""
    try:
        passed, failed = run_all_checks()
        
        print_header("Validation Summary")
        print(f"Passed: {GREEN}{passed}{RESET}")
        print(f"Failed: {RED}{failed}{RESET}")
        
        if failed == 0:
            print_success("All checks passed! System is ready.")
            print(f"\nAccess dashboard: {BLUE}http://localhost:3000{RESET}")
            print(f"API docs: {BLUE}http://localhost:8000/docs{RESET}")
            return 0
        else:
            print_error(f"Some checks failed. Please fix the issues above.")
            print("\nQuick fixes:")
            print("  1. Start Docker services: docker-compose up -d")
            print("  2. Install dependencies: pip install -r backend/requirements.txt")
            print("  3. Start backend: python main.py")
            print("  4. Start frontend: cd frontend && pnpm dev")
            return 1
    
    except KeyboardInterrupt:
        print_error("Validation interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
