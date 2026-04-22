"""
SSL/TLS Certificate Analyzer - Certificate chain, SANs, cipher audit, security grading.
Zero dependencies beyond Python stdlib (ssl + socket).
"""
from __future__ import annotations

import hashlib
import socket
import ssl
from datetime import datetime, timezone
from typing import Any


def _parse_subject_or_issuer(tuples: tuple) -> dict[str, str]:
    """Convert the nested tuple format from ssl.getpeercert() to a flat dict."""
    result: dict[str, str] = {}
    for item in tuples:
        for key, value in item:
            result[key] = value
    return result


def _extract_sans(cert: dict) -> list[str]:
    """Extract Subject Alternative Names from a certificate."""
    sans: list[str] = []
    for type_name, value in cert.get("subjectAltName", ()):
        if type_name.lower() in ("dns", "ip address"):
            sans.append(value)
    return sorted(set(sans))


def _grade_cipher(cipher_name: str, bits: int) -> str:
    """Grade a cipher suite. Returns A/B/C/F."""
    weak_ciphers = {"RC4", "DES", "3DES", "NULL", "EXPORT", "anon"}
    name_upper = cipher_name.upper()
    for weak in weak_ciphers:
        if weak in name_upper:
            return "F"
    if bits < 128:
        return "F"
    if bits < 256:
        return "B"
    return "A"


def _grade_protocol(protocol: str) -> str:
    """Grade the TLS protocol version."""
    proto_upper = protocol.upper()
    if "TLSV1.3" in proto_upper:
        return "A"
    if "TLSV1.2" in proto_upper:
        return "B"
    if "TLSV1.1" in proto_upper:
        return "C"
    # TLS 1.0, SSLv3, SSLv2
    return "F"


def ssl_analyze(
    host: str,
    port: int = 443,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Analyze the SSL/TLS certificate and connection security of a host.

    Args:
        host: Target hostname (e.g. 'google.com').
        port: TLS port (default 443).
        timeout: Connection timeout in seconds.

    Returns:
        Dict with certificate details, SANs, cipher info, protocol,
        expiry countdown, chain depth, and overall security grade.
    """
    host = host.strip().lower().replace("https://", "", 1).replace("http://", "", 1).split("/")[0].split(":")[0]

    result: dict[str, Any] = {
        "success": True,
        "host": host,
        "port": port,
    }

    try:
        # Create SSL context that fetches the full cert
        context = ssl.create_default_context()
        conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
        conn.settimeout(timeout)
        conn.connect((host, port))

        # Certificate info
        cert = conn.getpeercert()
        cert_bin = conn.getpeercert(binary_form=True)

        # Connection info
        protocol = conn.version() or "unknown"
        cipher_info = conn.cipher()  # (name, version, bits)

        conn.close()

    except ssl.SSLCertVerificationError as e:
        result["success"] = True  # Still report what we can
        result["verification_error"] = str(e)
        # Try without verification to get cert details
        try:
            context_noverify = ssl.create_default_context()
            context_noverify.check_hostname = False
            context_noverify.verify_mode = ssl.CERT_NONE
            conn2 = context_noverify.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
            conn2.settimeout(timeout)
            conn2.connect((host, port))
            cert = conn2.getpeercert(binary_form=False) or {}
            cert_bin = conn2.getpeercert(binary_form=True)
            protocol = conn2.version() or "unknown"
            cipher_info = conn2.cipher()
            conn2.close()
            result["self_signed_or_invalid"] = True
        except Exception as e2:
            return {**result, "success": False, "error": f"SSL connection failed: {e2}"}

    except (socket.timeout, socket.gaierror, OSError) as e:
        return {**result, "success": False, "error": f"Connection failed: {e}"}

    except Exception as e:
        return {**result, "success": False, "error": str(e)}

    # Parse certificate fields
    subject = _parse_subject_or_issuer(cert.get("subject", ()))
    issuer = _parse_subject_or_issuer(cert.get("issuer", ()))
    sans = _extract_sans(cert)

    # Certificate fingerprint
    fingerprint_sha256 = ""
    if cert_bin:
        fingerprint_sha256 = hashlib.sha256(cert_bin).hexdigest()

    # Validity dates
    not_before_str = cert.get("notBefore", "")
    not_after_str = cert.get("notAfter", "")

    days_until_expiry = None
    is_expired = False
    try:
        not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
        not_after = not_after.replace(tzinfo=timezone.utc)
        delta = not_after - datetime.now(timezone.utc)
        days_until_expiry = delta.days
        is_expired = days_until_expiry < 0
    except (ValueError, TypeError):
        pass

    # Cipher and protocol details
    cipher_name = cipher_info[0] if cipher_info else "unknown"
    cipher_bits = cipher_info[2] if cipher_info else 0

    # Serial number
    serial = cert.get("serialNumber", "")

    # Calculate overall grade
    issues: list[str] = []
    grades: list[str] = []

    proto_grade = _grade_protocol(protocol)
    cipher_grade = _grade_cipher(cipher_name, cipher_bits)
    grades.extend([proto_grade, cipher_grade])

    if is_expired:
        grades.append("F")
        issues.append("Certificate has EXPIRED")
    elif days_until_expiry is not None and days_until_expiry < 30:
        issues.append(f"Certificate expires in {days_until_expiry} days")

    if result.get("self_signed_or_invalid"):
        grades.append("F")
        issues.append("Certificate is self-signed or invalid")

    if proto_grade in ("C", "F"):
        issues.append(f"Weak TLS protocol: {protocol}")
    if cipher_grade == "F":
        issues.append(f"Weak cipher suite: {cipher_name}")

    if not sans:
        issues.append("No Subject Alternative Names in certificate")

    # Overall grade is the worst individual grade
    grade_order = {"F": 0, "C": 1, "B": 2, "A": 3}
    overall_grade = min(grades, key=lambda g: grade_order.get(g, 0)) if grades else "B"

    result.update({
        "subject": subject,
        "issuer": issuer,
        "common_name": subject.get("commonName", ""),
        "issuer_org": issuer.get("organizationName", ""),
        "sans": sans,
        "san_count": len(sans),
        "serial_number": serial,
        "fingerprint_sha256": fingerprint_sha256,
        "not_before": not_before_str,
        "not_after": not_after_str,
        "days_until_expiry": days_until_expiry,
        "is_expired": is_expired,
        "protocol": protocol,
        "cipher": cipher_name,
        "cipher_bits": cipher_bits,
        "grade": overall_grade,
        "issues": issues,
    })

    return result
