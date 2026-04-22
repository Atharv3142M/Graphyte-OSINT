import json
import subprocess
import os
import sys

modules = [
    ("shodan_recon", {"target": "google.com"}),
    ("censys_recon", {"target": "google.com"}),
    ("scraper", {"urls": ["http://google.com"]}),
    ("port_scanner", {"host": "google.com", "ports": [80]}),
    ("cyberninja_passive", {"usernames": ["admin"]}),
    ("xrecon", {"query": "admin"}),
    ("dns_intel", {"domain": "google.com", "brute_subdomains": False}),
    ("whois_lookup", {"domain": "google.com"}),
    ("ssl_analyzer", {"host": "google.com", "port": 443}),
    ("http_security", {"url": "http://google.com"}),
    ("tech_stack", {"url": "http://google.com"}),
    ("metadata_extractor", {"file_path": "test.txt"}),
    ("graysentinel_ingest", {"urls": ["http://google.com"]}),
    ("social_hunter", {"username": "admin"}),
    ("cert_transparency", {"domain": "google.com"}),
    ("deep_scraper", {"url": "http://google.com"}),
    ("ip_geolocation", {"target": "8.8.8.8"}),
    ("reverse_ip_lookup", {"target": "8.8.8.8"}),
    ("bgp_asn_lookup", {"target": "8.8.8.8"}),
    ("wayback_machine", {"target": "google.com"}),
    ("email_header_analyzer", {"raw_headers": ""}),
    ("sherlock_hunt", {"username": "admin"})
]

for mod, pload in modules:
    print(f"Testing {mod}...")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "backend.run_module", mod],
            input=json.dumps(pload).encode('utf-8'),
            capture_output=True,
            timeout=10
        )
        if proc.returncode != 0:
            print(f"FAILED {mod}: {proc.stderr.decode('utf-8')}")
        else:
            out = proc.stdout.decode('utf-8')
            res = json.loads(out)
            if not res.get("success", False):
                print(f"LOGIC FAILED {mod}: {res}")
            else:
                print(f"SUCCESS {mod}")
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT {mod}")
    except Exception as e:
        print(f"ERROR {mod}: {e}")
