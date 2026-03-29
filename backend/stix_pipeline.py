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
    if not result or not result.get("success", True) or result.get("error"):
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
    # Merge all relationships into the bundle
    # -------------------------------------------------------------------------
    objects.extend(relationships)

    if not objects:
        return None

    return {
        "type": "bundle",
        "id": _bundle_id(),
        "spec_version": "2.1",
        "objects": objects,
    }

