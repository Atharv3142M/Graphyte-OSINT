"""
EXAMPLE: Refactored DNS Intelligence module using clean architecture.

This demonstrates the new pattern for all 26 modules. Replaces the old:
- backend/modules/dns_intel.py
- Hardcoded route in api.py
- Hardcoded task in tasks.py
- Hardcoded elif in run_module.py
"""

import dns.resolver
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from backend.modules.base import BaseModule, ModuleMetadata, ModuleResult, ModuleCategory
from backend.modules.registry import register_module


# Module metadata - auto-discovered for API docs and routing
DNS_INTEL_METADATA = ModuleMetadata(
    name="dns_intel",
    display_name="DNS Intelligence",
    description="Perform DNS reconnaissance on a domain (A, MX, NS, TXT records)",
    category=ModuleCategory.RECON,
    version="2.0.0",
    timeout_seconds=15,
    supports_async=True,
    tags=["dns", "domain", "network"],
)


@register_module(DNS_INTEL_METADATA)
class DnsIntelModule(BaseModule):
    """DNS reconnaissance module."""
    
    metadata = DNS_INTEL_METADATA
    
    async def execute(self, payload: Dict[str, Any]) -> ModuleResult:
        """
        Execute DNS reconnaissance.
        
        Payload:
            {
                "target": "example.com",
                "record_types": ["A", "MX", "NS", "TXT"],  # Optional, defaults to all
                "timeout_seconds": 10  # Optional
            }
        
        Returns:
            ModuleResult with DNS records and extracted artifacts
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate payload
            validation_error = self._validate_payload(payload, required_keys=["target"])
            if validation_error:
                return validation_error
            
            target = payload.get("target", "").strip()
            record_types = payload.get("record_types", ["A", "MX", "NS", "TXT"])
            timeout_seconds = payload.get("timeout_seconds", 10)
            
            # Validate target format
            if not target or "." not in target:
                return self._create_result(
                    success=False,
                    error_code="INVALID_TARGET",
                    error_message=f"Invalid domain: {target}",
                )
            
            self._log_info(
                f"Starting DNS reconnaissance for {target}",
                target=target,
                record_types=record_types,
            )
            
            # Run DNS lookup asynchronously
            try:
                records = await asyncio.wait_for(
                    self._run_sync(lambda: self._resolve_dns(target, record_types)),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                return self._create_result(
                    success=False,
                    error_code="DNS_TIMEOUT",
                    error_message=f"DNS resolution exceeded {timeout_seconds}s timeout",
                )
            
            # Extract artifacts from records
            artifacts = self._extract_artifacts(target, records)
            
            self._log_info(
                f"DNS reconnaissance completed for {target}",
                records_found=len(records),
                artifacts_found=len(artifacts),
            )
            
            # Calculate execution time
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = self._create_result(
                success=True,
                data={
                    "domain": target,
                    "records": records,
                    "record_count": len(records),
                },
                artifacts=artifacts,
            )
            result.duration_ms = duration_ms
            
            return result
        
        except dns.exception.DNSException as e:
            self._log_error(f"DNS exception: {e}", error_type=type(e).__name__)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = self._create_result(
                success=False,
                error_code="DNS_LOOKUP_FAILED",
                error_message=f"DNS lookup failed: {str(e)[:100]}",
            )
            result.duration_ms = duration_ms
            return result
        
        except Exception as e:
            self._log_error(f"Unexpected error: {e}", error_type=type(e).__name__)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            result = self._create_result(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message="Internal module error",
            )
            result.duration_ms = duration_ms
            return result
    
    def _resolve_dns(self, domain: str, record_types: list[str]) -> Dict[str, Any]:
        """
        Synchronous DNS resolution.
        Runs in thread pool to avoid blocking async context.
        """
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5
        
        records = {}
        
        for rtype in record_types:
            try:
                answers = resolver.resolve(domain, rtype)
                records[rtype.upper()] = [str(rdata) for rdata in answers]
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.rdatatype.UnknownRdatatype):
                records[rtype.upper()] = []
            except dns.exception.DNSException:
                # Don't fail entire module for one record type
                records[rtype.upper()] = []
        
        return records
    
    def _extract_artifacts(self, domain: str, records: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Extract artifacts from DNS records."""
        artifacts = []
        
        # A records -> IP addresses
        if "A" in records:
            for ip in records["A"]:
                artifacts.append({
                    "type": "ip_address",
                    "value": ip,
                    "source": "dns_a_record",
                    "confidence": 0.95,
                })
        
        # MX records -> mail servers
        if "MX" in records:
            for mx in records["MX"]:
                # Extract host from MX record (format: "priority host")
                parts = mx.split()
                if len(parts) >= 2:
                    host = parts[-1].rstrip(".")
                    artifacts.append({
                        "type": "domain",
                        "value": host,
                        "source": "dns_mx_record",
                        "confidence": 0.95,
                    })
        
        # NS records -> nameservers
        if "NS" in records:
            for ns in records["NS"]:
                ns_domain = ns.rstrip(".")
                if ns_domain:
                    artifacts.append({
                        "type": "domain",
                        "value": ns_domain,
                        "source": "dns_ns_record",
                        "confidence": 0.95,
                    })
        
        # TXT records -> DMARC, SPF, etc.
        if "TXT" in records:
            for txt in records["TXT"]:
                if any(keyword in txt.lower() for keyword in ["dmarc", "spf", "dkim"]):
                    artifacts.append({
                        "type": "dns_record",
                        "value": txt[:200],  # Truncate long records
                        "source": "dns_txt_record",
                        "confidence": 0.90,
                    })
        
        return artifacts
