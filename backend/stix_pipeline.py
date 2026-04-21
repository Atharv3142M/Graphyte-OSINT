"""
STIX 2.1 standardization helpers for OSINT module outputs.

Produces bundles with ipv4-addr, domain-name, user-account, note, url,
and relationship objects that can be ingested into Neo4j.

Relationships added between:
  - user-account -> parent-domain  (social_hunter: "operates-on")
  - subdomain -> parent-domain      (cert_transparency: "drops")
  - note -> investigated entities   (all modules: "contextualizes")
  - url -> url                      (deep_scraper: "links-to")
  - url -> document                 (deep_scraper: "contains")
  - user-account -> url            (deep_scraper: "authored-on")
  - dns_intel: ipv4-addr, domain-name, network-traffic objects
  - whois_lookup: domain-name with registrant info
  - ssl_analyzer: ipv4-addr with cert details as note
  - http_security: url + note with header analysis
  - tech_stack: url + note with technology list
  - metadata_extractor: file with extracted metadata as note
  - graysentinel_pipeline: url nodes from ingested documents
  - cyberninja_passive: user-account per platform finding
  - xrecon: url nodes from recon sources
"""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List, Optional


def _bundle_id() -> str:
    return f"bundle--{uuid.uuid4()}"


def _obj_id(prefix: str) -> str:
    return f"{prefix}--{uuid.uuid4()}"


def _relationship(
    rel_type: str,
    source_id: str,
    target_id: str,
    created: str,
) -> Dict[str, Any]:
    return {
        "type": "relationship",
        "id": _obj_id("relationship"),
        "relationship_type": rel_type,
        "source_ref": source_id,
        "target_ref": target_id,
        "created": created,
        "modified": created,
    }


def build_stix_bundle(module_name: str, result: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Convert a module result into a STIX 2.1 bundle with proper relationship edges.
    Returns None if no meaningful mapping exists.
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.debug("[STIX-PIPELINE] module=%s result_keys=%s success=%s has_error=%s",
                 module_name, list(result.keys()) if result else None,
                 result.get("success") if result else None, bool(result.get("error") if result else None))

    if not result or not result.get("success", True) or result.get("error"):
        logger.debug("[STIX-PIPELINE] Skipping %s: result=%s success=%s error=%s",
                     module_name, bool(result), result.get("success") if result else None, result.get("error"))
        return None

    objects: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Keep a registry of id->obj so we can create relationships after-the-fact
    id_map: Dict[str, Dict[str, Any]] = {}

    def register(obj: Dict[str, Any]) -> None:
        if "id" in obj:
            id_map[obj["id"]] = obj
        objects.append(obj)

    def relate(source_id: str, target_id: str, rel_type: str) -> None:
        relationships.append(_relationship(rel_type, source_id, target_id, now))

    # -------------------------------------------------------------------------
    # shodan_recon
    # -------------------------------------------------------------------------
    if module_name == "shodan_recon":
        data = result.get("data") or {}
        if data.get("type") == "host":
            ipv4 = result.get("target")
            if ipv4:
                obj = {
                    "type": "ipv4-addr",
                    "id": _obj_id("ipv4-addr"),
                    "value": ipv4,
                    "x_shodan_ports": data.get("ports", []),
                    "x_shodan_city": data.get("city"),
                    "x_shodan_country": data.get("country_name"),
                    "x_shodan_org": data.get("org"),
                    "x_shodan_isp": data.get("isp"),
                }
                register(obj)
        elif data.get("type") == "domain":
            for match in data.get("matches", []):
                ip = match.get("ip_str")
                if ip:
                    obj = {
                        "type": "ipv4-addr",
                        "id": _obj_id("ipv4-addr"),
                        "value": ip,
                        "x_shodan_port": match.get("port"),
                        "x_shodan_city": match.get("city"),
                        "x_shodan_country": match.get("country_name"),
                    }
                    register(obj)

    # -------------------------------------------------------------------------
    # port_scanner
    # -------------------------------------------------------------------------
    elif module_name == "port_scanner":
        host = result.get("host")
        for p in result.get("open_ports", []):
            port = p.get("port")
            if host and port is not None:
                obj = {
                    "type": "network-traffic",
                    "id": _obj_id("network-traffic"),
                    "dst_port": port,
                    "protocols": ["tcp"],
                    "x_open": True,
                    "x_host": host,
                }
                register(obj)

    # -------------------------------------------------------------------------
    # scraper
    # -------------------------------------------------------------------------
    elif module_name == "scraper":
        emails = result.get("found_emails", [])
        phones = result.get("found_numbers", [])
        if emails or phones:
            obj = {
                "type": "note",
                "id": _obj_id("note"),
                "created": now,
                "modified": now,
                "abstract": "Contact information discovered by scraper",
                "content": {"emails": emails, "phone_numbers": phones},
            }
            register(obj)

    # -------------------------------------------------------------------------
    # social_hunter  ← enriched with relationships
    # -------------------------------------------------------------------------
    elif module_name == "social_hunter":
        username = result.get("username", "")
        profiles = result.get("profiles", [])

        account_type_map = {
            "github": "github", "gitlab": "gitlab", "twitter": "twitter",
            "facebook": "facebook", "instagram": "instagram", "linkedin": "linkedin",
            "reddit": "reddit", "tiktok": "tiktok", "youtube": "youtube",
            "twitch": "twitch", "steam": "steam", "pinterest": "pinterest",
            "medium": "medium", "codepen": "codepen", "npm": "npm", "pypi": "pypi",
            "dockerhub": "docker-hub", "keybase": "keybase", "telegram": "telegram",
            "discord": "discord", "mastodon": "mastodon", "bluesky": "bluesky",
            "devto": "devto", "replit": "replit", "stackoverflow": "stackoverflow",
            "patreon": "patreon", "snapchat": "snapchat",
            "soundcloud": "soundcloud", "spotify": "spotify",
            "venmo": "venmo", "cashapp": "cashapp",
        }

        found_accounts: List[Dict[str, Any]] = []
        for profile in profiles:
            if profile.get("status") == "found":
                platform = profile.get("platform", "unknown")
                profile_url = profile.get("url", "")
                account_type = account_type_map.get(platform, platform)

                obj = {
                    "type": "user-account",
                    "id": _obj_id("user-account"),
                    "account_type": account_type,
                    "account_login": username,
                    "display_name": f"@{username}",
                    "url": profile_url,
                    "x_platform": platform,
                    "x_profile_status": "active",
                }
                register(obj)
                found_accounts.append(obj)

        found_count = result.get("found_count", 0)
        if found_count > 0:
            # Summary note with context
            note_obj = {
                "type": "note",
                "id": _obj_id("note"),
                "created": now,
                "modified": now,
                "abstract": f"Username '{username}' found on {found_count} platform(s)",
                "content": {
                    "username": username,
                    "platforms_found": result.get("found", []),
                    "platforms_not_found": result.get("not_found", []),
                },
            }
            register(note_obj)

            # Link each found user-account to the summary note
            for account in found_accounts:
                relate(account["id"], note_obj["id"], "contextualizes")

            # Link the note to the investigated identity
            identity_id = _obj_id("identity")
            identity_obj = {
                "type": "identity",
                "id": identity_id,
                "name": username,
                "identity_class": "individual",
                "x_identity_type": "username-investigation",
            }
            register(identity_obj)
            relate(identity_obj["id"], note_obj["id"], "contextualizes")
            for account in found_accounts:
                relate(identity_obj["id"], account["id"], "operates-on")

    # -------------------------------------------------------------------------
    # cert_transparency  ← enriched with subdomain-of relationships
    # -------------------------------------------------------------------------
    elif module_name == "cert_transparency":
        domain = result.get("domain", "")
        subdomains = result.get("unique_subdomains", [])
        wildcards = result.get("wildcards", [])

        if not domain:
            return None

        # Parent domain node
        parent_obj = {
            "type": "domain-name",
            "id": _obj_id("domain-name"),
            "value": domain,
            "x_is_parent": True,
        }
        register(parent_obj)

        # Investigation note for the domain
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": (
                f"Certificate Transparency discovered {len(subdomains)} subdomains "
                f"and {len(wildcards)} wildcards for {domain}"
            ),
            "content": {
                "target_domain": domain,
                "subdomain_count": len(subdomains),
                "wildcard_count": len(wildcards),
                "wildcards": wildcards[:10],
            },
        }
        register(note_obj)
        relate(parent_obj["id"], note_obj["id"], "contextualizes")

        # Subdomain nodes with drops relationship to parent
        for subdomain in subdomains[:100]:
            sub_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": subdomain,
                "x_resolved_from": domain,
                "x_source": "certificate_transparency",
            }
            register(sub_obj)
            # Each subdomain is a child of the parent domain
            relate(sub_obj["id"], parent_obj["id"], "drops")

        # Wildcard domain nodes
        for wildcard in wildcards[:20]:
            wc_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": wildcard,
                "x_is_wildcard": True,
                "x_resolved_from": domain,
                "x_source": "certificate_transparency",
            }
            register(wc_obj)
            relate(wc_obj["id"], parent_obj["id"], "drops")

    # -------------------------------------------------------------------------
    # deep_scraper  ← enriched with links-to, contains, authored-on
    # -------------------------------------------------------------------------
    elif module_name == "deep_scraper":
        target_url = result.get("target_url", "")
        emails = result.get("emails", [])
        phones = result.get("phone_numbers", [])
        internal_links = result.get("internal_links", [])
        external_links = result.get("external_links", [])
        documents = result.get("documents", [])
        social_profiles = result.get("social_profiles", [])

        if not target_url:
            return None

        # Root URL node
        root_obj = {
            "type": "url",
            "id": _obj_id("url"),
            "value": target_url,
            "x_is_target": True,
        }
        register(root_obj)

        # Contact info note
        contact_note: Optional[Dict[str, Any]] = None
        if emails or phones:
            contact_note = {
                "type": "note",
                "id": _obj_id("note"),
                "created": now,
                "modified": now,
                "abstract": "Contact information discovered by deep scraper",
                "content": {
                    "emails": emails[:50],
                    "phone_numbers": phones[:20],
                },
            }
            register(contact_note)
            relate(root_obj["id"], contact_note["id"], "contextualizes")

        # Internal link URL nodes linked to root
        internal_url_objects: List[Dict[str, Any]] = []
        for link in internal_links[:30]:
            link_obj = {
                "type": "url",
                "id": _obj_id("url"),
                "value": link,
                "x_link_type": "internal",
                "x_source_url": target_url,
            }
            register(link_obj)
            internal_url_objects.append(link_obj)
            # Root page links to internal pages
            relate(root_obj["id"], link_obj["id"], "links-to")

        # External link URL nodes
        for link in external_links[:20]:
            ext_obj = {
                "type": "url",
                "id": _obj_id("url"),
                "value": link,
                "x_link_type": "external",
                "x_source_url": target_url,
            }
            register(ext_obj)
            relate(root_obj["id"], ext_obj["id"], "links-to")

        # Document nodes linked to the root URL
        for doc in documents[:20]:
            doc_obj = {
                "type": "url",
                "id": _obj_id("url"),
                "value": doc.get("url", ""),
                "x_doc_type": doc.get("type"),
                "x_doc_title": doc.get("title"),
                "x_doc_author": doc.get("author"),
                "x_discovered_from": target_url,
            }
            register(doc_obj)
            relate(root_obj["id"], doc_obj["id"], "contains")

        # Social profile user-account nodes
        for profile in social_profiles[:20]:
            platform = profile.get("platform", "unknown")
            username_str = profile.get("username", "")
            profile_url = profile.get("url", "")

            if not username_str:
                continue

            acct_obj = {
                "type": "user-account",
                "id": _obj_id("user-account"),
                "account_type": platform,
                "account_login": username_str,
                "url": profile_url,
                "x_source": "deep_scraper",
                "x_discovered_from": target_url,
            }
            register(acct_obj)
            # Profile was found on / authored via the target domain
            relate(acct_obj["id"], root_obj["id"], "authored-on")

        # Summary note
        summary_note = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": (
                f"Deep scrape of {target_url}: {len(emails)} emails, "
                f"{len(phones)} phones, {len(internal_links)} internal links, "
                f"{len(external_links)} external links, {len(documents)} documents, "
                f"{len(social_profiles)} social profiles"
            ),
            "content": {
                "pages_crawled": result.get("pages_crawled", 0),
                "crawl_depth": result.get("crawl_depth", 0),
            },
        }
        register(summary_note)
        relate(root_obj["id"], summary_note["id"], "contextualizes")

    # -------------------------------------------------------------------------
    # dns_intel  ← A/AAAA/MX/NS/TXT + subdomains + SPF/DMARC assessment
    # -------------------------------------------------------------------------
    elif module_name == "dns_intel":
        domain = result.get("domain", "")
        records = result.get("records", {})

        domain_obj: Optional[Dict[str, Any]] = None
        if domain:
            domain_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": domain,
                "x_dns_secure": result.get("security_assessment", {}).get("grade", "N/A"),
            }
            register(domain_obj)

        # A/AAAA records → ipv4/ipv6-addr nodes
        for rtype in ("A", "AAAA"):
            for ip in records.get(rtype, []):
                ip_type = "ipv4-addr" if rtype == "A" else "ipv6-addr"
                ip_obj = {
                    "type": ip_type,
                    "id": _obj_id(ip_type),
                    "value": ip,
                }
                register(ip_obj)
                if domain_obj:
                    relate(ip_obj["id"], domain_obj["id"], "resolves_to")

        # MX records → domain-name (mail servers)
        for mx in records.get("MX", []):
            mx_host = str(mx).split()[1] if " " in str(mx) else str(mx)
            mx_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": mx_host,
                "x_record_type": "MX",
                "x_priority": str(mx).split()[0] if " " in str(mx) else "10",
            }
            register(mx_obj)
            if domain_obj:
                relate(domain_obj["id"], mx_obj["id"], "has_mx")

        # NS records
        for ns in records.get("NS", []):
            ns_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": str(ns),
                "x_record_type": "NS",
            }
            register(ns_obj)
            if domain_obj:
                relate(domain_obj["id"], ns_obj["id"], "has_ns")

        # TXT records (SPF, DMARC)
        for txt in records.get("TXT", []):
            if not isinstance(txt, str):
                txt = str(txt)
            if txt.strip('"').startswith("v=spf1"):
                txt_obj = {
                    "type": "note",
                    "id": _obj_id("note"),
                    "created": now,
                    "modified": now,
                    "abstract": "SPF DNS record",
                    "content": {"raw": txt},
                }
                register(txt_obj)
                if domain_obj:
                    relate(domain_obj["id"], txt_obj["id"], "has_txt_record")

        # Subdomain brute-force results
        for sub_result in result.get("subdomains_found", []):
            sub_fqdn = sub_result.get("fqdn", "")
            if not sub_fqdn:
                continue
            sub_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": sub_fqdn,
                "x_source": "dns_bruteforce",
                "x_resolves_to_ips": sub_result.get("ips", []),
            }
            register(sub_obj)
            if domain_obj:
                relate(sub_obj["id"], domain_obj["id"], "subdomain_of")

        # Security assessment note
        assessment = result.get("security_assessment", {})
        if assessment:
            note_obj = {
                "type": "note",
                "id": _obj_id("note"),
                "created": now,
                "modified": now,
                "abstract": f"DNS security assessment: {assessment.get('grade', 'N/A')}",
                "content": {
                    "score": assessment.get("score"),
                    "grade": assessment.get("grade"),
                    "issues": assessment.get("issues", []),
                    "spf_present": result.get("spf") is not None,
                    "dmarc_present": result.get("dmarc") is not None,
                },
            }
            register(note_obj)
            if domain_obj:
                relate(domain_obj["id"], note_obj["id"], "contextualizes")

    # -------------------------------------------------------------------------
    # whois_lookup  ← domain-name with full registrant data
    # -------------------------------------------------------------------------
    elif module_name == "whois_lookup":
        domain = result.get("domain", "")
        if not domain:
            return None

        domain_obj = {
            "type": "domain-name",
            "id": _obj_id("domain-name"),
            "value": domain,
            "x_registrar": result.get("registrar"),
            "x_registrant_org": result.get("registrant_org"),
            "x_registrant_country": result.get("registrant_country"),
            "x_creation_date": result.get("creation_date"),
            "x_expiry_date": result.get("expiry_date"),
            "x_updated_date": result.get("updated_date"),
            "x_domain_age_days": result.get("domain_age_days"),
            "x_dnssec": result.get("dnssec"),
        }
        register(domain_obj)

        # Nameservers
        for ns in result.get("nameservers", []):
            ns_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": ns,
                "x_record_type": "NS",
            }
            register(ns_obj)
            relate(domain_obj["id"], ns_obj["id"], "has_ns")

        # WHOIS note with full details
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"WHOIS lookup for {domain}",
            "content": {
                "registrar": result.get("registrar"),
                "registrant_org": result.get("registrant_org"),
                "creation_date": result.get("creation_date"),
                "expiry_date": result.get("expiry_date"),
                "domain_age_days": result.get("domain_age_days"),
                "dnssec": result.get("dnssec"),
                "status": result.get("status", []),
                "warnings": result.get("warnings", []),
            },
        }
        register(note_obj)
        relate(domain_obj["id"], note_obj["id"], "contextualizes")

        # Contact emails
        for email in result.get("emails", [])[:10]:
            email_obj = {
                "type": "email-addr",
                "id": _obj_id("email-addr"),
                "value": email,
                "x_source": "whois",
            }
            register(email_obj)
            relate(domain_obj["id"], email_obj["id"], "has_email")

    # -------------------------------------------------------------------------
    # ssl_analyzer  ← ipv4-addr with certificate details as note
    # -------------------------------------------------------------------------
    elif module_name == "ssl_analyzer":
        host = result.get("host", "")
        port = result.get("port", 443)
        if not host:
            return None

        ip_obj = {
            "type": "ipv4-addr",
            "id": _obj_id("ipv4-addr"),
            "value": host,
            "x_ssl_port": port,
            "x_ssl_grade": result.get("grade"),
            "x_ssl_protocol": result.get("protocol"),
            "x_ssl_cipher": result.get("cipher"),
            "x_days_until_expiry": result.get("days_until_expiry"),
            "x_is_expired": result.get("is_expired", False),
        }
        register(ip_obj)

        # Certificate note
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"SSL/TLS certificate analysis for {host}:{port} — Grade {result.get('grade', 'N/A')}",
            "content": {
                "subject": result.get("subject", {}),
                "issuer": result.get("issuer", {}),
                "common_name": result.get("common_name"),
                "sans": result.get("sans", []),
                "san_count": result.get("san_count", 0),
                "serial_number": result.get("serial_number"),
                "fingerprint_sha256": result.get("fingerprint_sha256"),
                "not_before": result.get("not_before"),
                "not_after": result.get("not_after"),
                "days_until_expiry": result.get("days_until_expiry"),
                "is_expired": result.get("is_expired", False),
                "protocol": result.get("protocol"),
                "cipher": result.get("cipher"),
                "cipher_bits": result.get("cipher_bits"),
                "grade": result.get("grade"),
                "issues": result.get("issues", []),
                "self_signed_or_invalid": result.get("self_signed_or_invalid", False),
            },
        }
        register(note_obj)
        relate(ip_obj["id"], note_obj["id"], "contextualizes")

        # SANs as domain-name nodes
        for san in result.get("sans", []):
            if not san:
                continue
            san_obj = {
                "type": "domain-name",
                "id": _obj_id("domain-name"),
                "value": san,
                "x_source": "ssl_san",
            }
            register(san_obj)
            relate(ip_obj["id"], san_obj["id"], "has_san")

    # -------------------------------------------------------------------------
    # http_security  ← url with security header analysis as note
    # -------------------------------------------------------------------------
    elif module_name == "http_security":
        url = result.get("url", "")
        final_url = result.get("final_url", url)
        if not url and not final_url:
            return None

        display_url = final_url or url
        url_obj = {
            "type": "url",
            "id": _obj_id("url"),
            "value": display_url,
            "x_status_code": result.get("status_code"),
            "x_uses_https": result.get("uses_https", False),
            "x_grade": result.get("grade"),
            "x_score": result.get("score"),
        }
        register(url_obj)

        # Security headers note
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"HTTP Security Headers audit for {display_url} — Grade {result.get('grade', 'N/A')}",
            "content": {
                "grade": result.get("grade"),
                "score": result.get("score"),
                "headers_present": result.get("headers_present"),
                "headers_missing": result.get("headers_missing"),
                "headers_total": result.get("headers_total"),
                "found_headers": result.get("found_headers", {}),
                "missing_headers": result.get("missing_headers", []),
                "information_disclosure": result.get("information_disclosure", []),
                "analysis": result.get("analysis", []),
            },
        }
        register(note_obj)
        relate(url_obj["id"], note_obj["id"], "contextualizes")

    # -------------------------------------------------------------------------
    # tech_stack  ← url with technology stack as note
    # -------------------------------------------------------------------------
    elif module_name == "tech_stack":
        url = result.get("url", "")
        final_url = result.get("final_url", url)
        if not url and not final_url:
            return None

        display_url = final_url or url
        url_obj = {
            "type": "url",
            "id": _obj_id("url"),
            "value": display_url,
            "x_server": result.get("server"),
            "x_status_code": result.get("status_code"),
        }
        register(url_obj)

        # Technology note
        technologies = result.get("technologies", [])
        categories = result.get("categories", [])
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"Technology stack fingerprinting for {display_url} — {len(technologies)} technologies detected",
            "content": {
                "tech_count": result.get("tech_count", 0),
                "categories": categories,
                "technologies": [
                    {"name": t.get("name"), "category": t.get("category"), "confidence": t.get("confidence"), "evidence": t.get("evidence")}
                    for t in technologies
                ],
                "server": result.get("server"),
                "powered_by": result.get("powered_by"),
            },
        }
        register(note_obj)
        relate(url_obj["id"], note_obj["id"], "contextualizes")

        # Each technology → software node
        for tech in technologies:
            tech_obj = {
                "type": "software",
                "id": _obj_id("software"),
                "name": tech.get("name"),
                "x_category": tech.get("category"),
                "x_confidence": tech.get("confidence"),
            }
            register(tech_obj)
            relate(url_obj["id"], tech_obj["id"], "runs")

    # -------------------------------------------------------------------------
    # metadata_extractor  ← file with extracted metadata as note
    # -------------------------------------------------------------------------
    elif module_name == "metadata_extractor":
        filename = result.get("filename", "")
        file_type = result.get("file_type", "unknown")

        file_obj = {
            "type": "file",
            "id": _obj_id("file"),
            "name": filename,
            "x_file_type": file_type,
        }
        register(file_obj)

        metadata = result.get("metadata", {})
        gps = result.get("gps")

        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"File metadata extraction: {filename} ({file_type})",
            "content": {
                "metadata": metadata,
                "gps": gps,
            },
        }
        register(note_obj)
        relate(file_obj["id"], note_obj["id"], "contextualizes")

        # GPS coordinates as location
        if gps:
            loc_obj = {
                "type": "location",
                "id": _obj_id("location"),
                "x_latitude": gps.get("latitude"),
                "x_longitude": gps.get("longitude"),
                "x_source": "image_exif_gps",
            }
            register(loc_obj)
            relate(file_obj["id"], loc_obj["id"], "located_at")

    # -------------------------------------------------------------------------
    # graysentinel_pipeline  ← url nodes for each ingested document
    # -------------------------------------------------------------------------
    elif module_name == "graysentinel_pipeline":
        urls = result.get("urls", [])
        ingested = result.get("ingested", 0)

        if not urls:
            return None

        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"GraySentinel pipeline: ingested {ingested} chunks from {len(urls)} URL(s)",
            "content": {
                "urls": urls,
                "ingested_chunks": ingested,
            },
        }
        register(note_obj)

        for url in urls[:50]:
            url_obj = {
                "type": "url",
                "id": _obj_id("url"),
                "value": url,
                "x_source": "graysentinel_pipeline",
            }
            register(url_obj)
            relate(note_obj["id"], url_obj["id"], "contains")

    # -------------------------------------------------------------------------
    # cyberninja_passive  ← user-account nodes per platform find
    # -------------------------------------------------------------------------
    elif module_name == "cyberninja_passive":
        data = result.get("data", {})
        if not data:
            return None

        all_checks: List[Dict[str, Any]] = []
        for username, user_data in data.items():
            checks = user_data.get("checks", [])
            all_checks.extend(checks)

        if not all_checks:
            return None

        identity_id = _obj_id("identity")
        identity_obj = {
            "type": "identity",
            "id": identity_id,
            "name": list(data.keys())[0] if data else "unknown",
            "identity_class": "individual",
            "x_identity_type": "username-investigation",
        }
        register(identity_obj)

        found_accounts: List[Dict[str, Any]] = []
        for check in all_checks:
            if check.get("exists"):
                site = check.get("site", "unknown")
                acct_obj = {
                    "type": "user-account",
                    "id": _obj_id("user-account"),
                    "account_type": site.lower().replace(" ", "-"),
                    "account_login": check.get("url", ""),
                    "url": check.get("url", ""),
                    "x_status_code": check.get("status_code"),
                    "x_platform": site,
                    "x_profile_status": "active",
                }
                register(acct_obj)
                found_accounts.append(acct_obj)
                relate(identity_obj["id"], acct_obj["id"], "operates-on")

        # Summary note
        found_count = len(found_accounts)
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"CyberNinja passive: {found_count} accounts found",
            "content": {
                "total_checks": len(all_checks),
                "found_count": found_count,
                "checks": [
                    {"site": c.get("site"), "exists": c.get("exists"), "status_code": c.get("status_code")}
                    for c in all_checks
                ],
            },
        }
        register(note_obj)
        relate(identity_obj["id"], note_obj["id"], "contextualizes")

    # -------------------------------------------------------------------------
    # xrecon  ← url nodes from recon sources
    # -------------------------------------------------------------------------
    elif module_name == "xrecon":
        query = result.get("query", "")
        query_type = result.get("query_type", "username")
        xrecon_data = result.get("data", {})

        if not query:
            return None

        identity_obj = {
            "type": "identity",
            "id": _obj_id("identity"),
            "name": query,
            "identity_class": "individual",
            "x_identity_type": f"xrecon-{query_type}",
        }
        register(identity_obj)

        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"xRecon {query_type} search: {query}",
            "content": xrecon_data,
        }
        register(note_obj)
        relate(identity_obj["id"], note_obj["id"], "contextualizes")

        # If data contains URLs, create url nodes
        sources = xrecon_data.get("sources", [])
        if isinstance(sources, list):
            for src in sources[:50]:
                if isinstance(src, str) and ("://" in src or src.startswith("http")):
                    src_obj = {
                        "type": "url",
                        "id": _obj_id("url"),
                        "value": src,
                        "x_source": "xrecon",
                    }
                    register(src_obj)
                    relate(note_obj["id"], src_obj["id"], "contains")

    # -------------------------------------------------------------------------
    # IP Geolocation
    # -------------------------------------------------------------------------
    elif module_name == "ip_geolocation":
        ip_value = result.get("ip")
        if ip_value:
            ip_obj = {"type": "ipv4-addr", "id": _obj_id("ipv4-addr"), "value": ip_value}
            register(ip_obj)
            note_obj = {
                "type": "note",
                "id": _obj_id("note"),
                "created": now,
                "modified": now,
                "abstract": f"IP geolocation for {ip_value}",
                "content": result,
            }
            register(note_obj)
            relate(ip_obj["id"], note_obj["id"], "located-at")

    # -------------------------------------------------------------------------
    # Reverse IP
    # -------------------------------------------------------------------------
    elif module_name == "reverse_ip_lookup":
        ip_value = result.get("ip")
        domains = result.get("domains", [])
        if ip_value:
            ip_obj = {"type": "ipv4-addr", "id": _obj_id("ipv4-addr"), "value": ip_value}
            register(ip_obj)
            for domain in domains[:100]:
                dom_obj = {"type": "domain-name", "id": _obj_id("domain-name"), "value": domain}
                register(dom_obj)
                relate(ip_obj["id"], dom_obj["id"], "resolves-to")

    # -------------------------------------------------------------------------
    # BGP / ASN
    # -------------------------------------------------------------------------
    elif module_name == "bgp_asn_lookup":
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": f"BGP/ASN lookup for {result.get('target', '')}",
            "content": result.get("data", {}),
        }
        register(note_obj)

    # -------------------------------------------------------------------------
    # Wayback
    # -------------------------------------------------------------------------
    elif module_name == "wayback_machine":
        target = result.get("target", "")
        snapshots = result.get("snapshots", [])
        target_obj = {"type": "domain-name", "id": _obj_id("domain-name"), "value": target}
        register(target_obj)
        for snap in snapshots[:100]:
            snapshot_url = snap.get("snapshot_url")
            if not snapshot_url:
                continue
            url_obj = {"type": "url", "id": _obj_id("url"), "value": snapshot_url, "x_source": "wayback"}
            register(url_obj)
            relate(target_obj["id"], url_obj["id"], "related-to")

    # -------------------------------------------------------------------------
    # Email Header Analyzer
    # -------------------------------------------------------------------------
    elif module_name == "email_header_analyzer":
        for ip in result.get("ips", [])[:50]:
            ip_obj = {"type": "ipv4-addr", "id": _obj_id("ipv4-addr"), "value": ip}
            register(ip_obj)
        note_obj = {
            "type": "note",
            "id": _obj_id("note"),
            "created": now,
            "modified": now,
            "abstract": "Email header analysis",
            "content": result,
        }
        register(note_obj)

    # -------------------------------------------------------------------------
    # Sherlock
    # -------------------------------------------------------------------------
    elif module_name == "sherlock_hunt":
        username = result.get("username")
        found = result.get("found", [])
        if username:
            ident = {
                "type": "identity",
                "id": _obj_id("identity"),
                "name": username,
                "identity_class": "individual",
            }
            register(ident)
            for profile in found[:300]:
                platform = profile.get("platform", "unknown")
                profile_url = profile.get("url", "")
                account = {
                    "type": "user-account",
                    "id": _obj_id("user-account"),
                    "account_login": username,
                    "account_type": str(platform).lower(),
                    "x_profile_url": profile_url,
                }
                register(account)
                relate(ident["id"], account["id"], "associated-with")

    # -------------------------------------------------------------------------
    # Merge all relationships into the bundle
    # -------------------------------------------------------------------------
    objects.extend(relationships)

    if not objects:
        logger.debug("[STIX-PIPELINE] module=%s: no objects registered, returning None", module_name)
        return None

    logger.info("[STIX-PIPELINE] module=%s: built bundle with %d objects, %d relationships",
                module_name, len(objects) - len(relationships), len(relationships))
    return {
        "type": "bundle",
        "id": _bundle_id(),
        "spec_version": "2.1",
        "objects": objects,
    }
