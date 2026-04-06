/**
 * Client-side input classifier for the OSINT platform.
 * Detects the type(s) of a user-provided string: IP, domain, URL, email, etc.
 * Pure function — no network calls, no side effects.
 */

import { getDomain, getPublicSuffix } from "tldts";

/* ── Types ──────────────────────────────────────────────── */

export type DetectedType =
  | "ipv4"
  | "ipv6"
  | "cidr"
  | "domain"
  | "url"
  | "email"
  | "username"
  | "hash_md5"
  | "hash_sha1"
  | "hash_sha256"
  | "phone"
  | "asn"
  | "company";

/* ── Regexes (compiled once) ─────────────────────────────── */

const RE_IPV4 =
  /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
const RE_IPV6 =
  /^(?:(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+|::(?:ffff(?::0{1,4})?:)?(?:(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])\.){3}(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])\.){3}(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9]))$/;
const RE_CIDR =
  /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:3[0-2]|[12]?[0-9])$/;
const RE_URL = /^(?:https?|ftp|file):\/\/[^\s]+$/i;
const RE_EMAIL_LOCAL = /^[a-zA-Z0-9._%+\-]+$/;
const RE_HASH_MD5 = /^[a-fA-F0-9]{32}$/;
const RE_HASH_SHA1 = /^[a-fA-F0-9]{40}$/;
const RE_HASH_SHA256 = /^[a-fA-F0-9]{64}$/;
const RE_PHONE = /^\+?[1-9][0-9]{7,14}$/;
const RE_ASN = /^AS[1-9][0-9]{0,9}$/i;
const RE_USERNAME = /^[a-zA-Z0-9_\-]{2,30}$/;
const RE_COMPANY_SUFFIX =
  /\b(?:Inc|LLC|Ltd|Co|Corp| GmbH|SAS|SARL|PLC|AG|SPA|SA|NV|BV|OY|AB|Pte|Ltd|Private|Open)\b/i;

/* ── Private-use IP ranges to reject from OSINT scope ─────── */

const PRIVATE_IPV4_PREFIXES = ["10.", "192.168.", "127."];
const PRIVATE_172_START = 16;

function isPrivateIpv4(ip: string): boolean {
  return (
    PRIVATE_IPV4_PREFIXES.some((p) => ip.startsWith(p)) ||
    (ip.startsWith("172.") &&
      parseInt(ip.split(".")[1], 10) >= PRIVATE_172_START &&
      parseInt(ip.split(".")[1], 10) <= 31)
  );
}

/* ── Domain / TLD validation via tldts ───────────────────── */

function isValidDomain(raw: string): boolean {
  // Reject single labels and private-use names
  const blocked = new Set(["localhost", "test", "example", "invalid", "none"]);
  if (blocked.has(raw.toLowerCase())) return false;
  const suffix = getPublicSuffix(raw);
  if (!suffix) return false;
  const domain = getDomain(raw);
  return !!domain && domain !== suffix && domain.length > suffix.length;
}

/* ── Core classifier ─────────────────────────────────────── */

/**
 * Classify a raw user input string into one or more detected types.
 * A string can match multiple types (e.g. "google.com" is both a domain).
 *
 * @param input - Raw user input string
 * @returns Array of detected type strings
 */
export function classify(input: string): DetectedType[] {
  const raw = input.trim();
  if (!raw || raw.length > 500) return [];

  const results: DetectedType[] = [];

  /* ── 1. IPv4 (unambiguous when valid) ── */
  if (RE_IPV4.test(raw) && !isPrivateIpv4(raw)) {
    results.push("ipv4");
  }

  /* ── 2. IPv6 ── */
  if (RE_IPV6.test(raw)) {
    results.push("ipv6");
  }

  /* ── 3. CIDR ── */
  if (RE_CIDR.test(raw)) {
    results.push("cidr");
  }

  /* ── 4. URL ── */
  if (RE_URL.test(raw)) {
    results.push("url");
  }

  /* ── 5. Email ── */
  const atIdx = raw.indexOf("@");
  if (atIdx > 0 && atIdx < raw.length - 1) {
    const localPart = raw.slice(0, atIdx);
    const domainPart = raw.slice(atIdx + 1);
    if (RE_EMAIL_LOCAL.test(localPart) && domainPart.includes(".")) {
      results.push("email");
    }
  }

  /* ── 6. Hashes (32/40/64 hex chars) ── */
  if (RE_HASH_MD5.test(raw)) {
    results.push("hash_md5");
  } else if (RE_HASH_SHA1.test(raw)) {
    results.push("hash_sha1");
  } else if (RE_HASH_SHA256.test(raw)) {
    results.push("hash_sha256");
  }

  /* ── 7. Phone ── */
  const digitsOnly = raw.replace(/[\s\-\(\)\.]/g, "");
  if (RE_PHONE.test(digitsOnly)) {
    results.push("phone");
  }

  /* ── 8. ASN ── */
  if (RE_ASN.test(raw)) {
    results.push("asn");
  }

  /* ── 9. Domain (via tldts) ── */
  if (!RE_URL.test(raw) && isValidDomain(raw)) {
    results.push("domain");
  }

  /* ── 10. Username (fallback — only if nothing else matched) ── */
  if (
    results.length === 0 &&
    RE_USERNAME.test(raw) &&
    !raw.includes(".") &&
    !raw.includes("@") &&
    !RE_URL.test(raw)
  ) {
    results.push("username");
  }

  /* ── 11. Company name (low confidence — needs manual confirm) ── */
  if (results.length === 0 && raw.includes(" ") && RE_COMPANY_SUFFIX.test(raw)) {
    results.push("company");
  }

  return results;
}

/* ── Normalization helpers ───────────────────────────────── */

/**
 * Extract a clean domain from a URL or email address.
 * Returns the input itself if it's a valid domain.
 */
export function extractDomain(input: string): string | null {
  if (RE_URL.test(input)) {
    try {
      return new URL(input).hostname.replace(/^www\./, "").toLowerCase();
    } catch {
      return null;
    }
  }
  const atIdx = input.indexOf("@");
  if (atIdx > 0) {
    return input.slice(atIdx + 1).replace(/^www\./, "").toLowerCase();
  }
  if (isValidDomain(input)) {
    return input.replace(/^www\./, "").toLowerCase();
  }
  return null;
}

/**
 * Extract a clean IP from a string (handles CIDR notation).
 */
export function extractIP(input: string): string | null {
  if (RE_IPV4.test(input)) return input;
  if (RE_CIDR.test(input)) return input.split("/")[0];
  return null;
}

/**
 * Normalize any input to its clean dispatch target.
 */
export function normalizeInput(input: string): string {
  return extractDomain(input) ?? extractIP(input) ?? input.replace(/^https?:\/\//, "").split("/")[0];
}