/**
 * Mock Data Providers for Enterprise OSINT Digital Footprint Visualizer
 *
 * These providers enable UI preview and development without backend connectivity.
 * All data simulates STIX 2.1 format and realistic Celery task outputs.
 */

import type { NodeDetail } from "@/components/NodeDetailPanel";

// ============================================================================
// MOCK STIX 2.1 GRAPH DATA
// ============================================================================

export const MOCK_GRAPH_ELEMENTS = {
  nodes: [
    {
      data: {
        id: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        label: "8.8.8.8",
        type: "ipv4-addr",
        riskScore: 0.15,
        stix: {
          type: "ipv4-addr",
          id: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          value: "8.8.8.8",
          x_shodan_ports: [53, 443],
          x_shodan_city: "Mountain View",
          x_shodan_country: "United States",
          x_shodan_org: "Google LLC",
          x_shodan_isp: "Google LLC",
        },
        entityResolution: {
          asn: "AS15169",
          organization: "Google LLC",
          reverse_dns: "dns.google",
        },
      },
    },
    {
      data: {
        id: "domain-name--b2c3d4e5-f6a7-8901-bcde-f12345678901",
        label: "google.com",
        type: "domain-name",
        riskScore: 0.05,
        stix: {
          type: "domain-name",
          id: "domain-name--b2c3d4e5-f6a7-8901-bcde-f12345678901",
          value: "google.com",
        },
        entityResolution: {
          registrar: "MarkMonitor Inc.",
          creation_date: "1997-09-15",
          expiry_date: "2028-09-14",
        },
      },
    },
    {
      data: {
        id: "network-traffic--c3d4e5f6-a7b8-9012-cdef-123456789012",
        label: "Port 443 (HTTPS)",
        type: "network-traffic",
        riskScore: 0.1,
        stix: {
          type: "network-traffic",
          id: "network-traffic--c3d4e5f6-a7b8-9012-cdef-123456789012",
          dst_port: 443,
          protocols: ["tcp", "tls"],
          x_open: true,
          x_host: "8.8.8.8",
        },
        entityResolution: {
          service: "HTTPS",
          banner: "TLS 1.3",
        },
      },
    },
    {
      data: {
        id: "network-traffic--d4e5f6a7-b8c9-0123-def0-234567890123",
        label: "Port 53 (DNS)",
        type: "network-traffic",
        riskScore: 0.1,
        stix: {
          type: "network-traffic",
          id: "network-traffic--d4e5f6a7-b8c9-0123-def0-234567890123",
          dst_port: 53,
          protocols: ["tcp", "udp"],
          x_open: true,
          x_host: "8.8.8.8",
        },
        entityResolution: {
          service: "DNS",
          banner: "Google Public DNS",
        },
      },
    },
    {
      data: {
        id: "note--e5f6a7b8-c9d0-1234-ef01-345678901234",
        label: "Security Headers Audit",
        type: "note",
        riskScore: 0.35,
        stix: {
          type: "note",
          id: "note--e5f6a7b8-c9d0-1234-ef01-345678901234",
          abstract: "HTTP Security Headers Analysis",
          content: {
            grade: "B",
            score: 75,
            missing: ["Content-Security-Policy", "Cross-Origin-Embedder-Policy"],
          },
        },
        entityResolution: {
          url: "https://google.com",
          audit_timestamp: "2026-03-26T14:32:00Z",
        },
      },
    },
    {
      data: {
        id: "ipv4-addr--f6a7b8c9-d0e1-2345-f012-456789012345",
        label: "142.250.185.78",
        type: "ipv4-addr",
        riskScore: 0.12,
        stix: {
          type: "ipv4-addr",
          id: "ipv4-addr--f6a7b8c9-d0e1-2345-f012-456789012345",
          value: "142.250.185.78",
          x_shodan_ports: [80, 443],
          x_shodan_city: "Mountain View",
          x_shodan_country: "United States",
          x_shodan_org: "Google LLC",
        },
        entityResolution: {
          asn: "AS15169",
          organization: "Google LLC",
        },
      },
    },
    {
      data: {
        id: "domain-name--a7b8c9d0-e1f2-3456-0123-567890123456",
        label: "dns.google",
        type: "domain-name",
        riskScore: 0.08,
        stix: {
          type: "domain-name",
          id: "domain-name--a7b8c9d0-e1f2-3456-0123-567890123456",
          value: "dns.google",
        },
        entityResolution: {
          registrar: "MarkMonitor Inc.",
          reverse_dns_of: "8.8.8.8",
        },
      },
    },
    {
      data: {
        id: "note--b8c9d0e1-f2a3-4567-1234-678901234567",
        label: "SSL Certificate Analysis",
        type: "note",
        riskScore: 0.05,
        stix: {
          type: "note",
          id: "note--b8c9d0e1-f2a3-4567-1234-678901234567",
          abstract: "TLS Certificate Details",
          content: {
            common_name: "*.google.com",
            issuer: "GTS CA 1C3",
            valid_from: "2026-02-15",
            valid_until: "2026-05-10",
            grade: "A",
            cipher: "TLS_AES_256_GCM_SHA384",
            protocol: "TLSv1.3",
          },
        },
        entityResolution: {
          fingerprint_sha256: "a1b2c3d4e5f6...",
        },
      },
    },
    {
      data: {
        id: "ipv4-addr--c9d0e1f2-a3b4-5678-2345-789012345678",
        label: "185.199.108.153",
        type: "ipv4-addr",
        riskScore: 0.45,
        stix: {
          type: "ipv4-addr",
          id: "ipv4-addr--c9d0e1f2-a3b4-5678-2345-789012345678",
          value: "185.199.108.153",
          x_shodan_ports: [22, 80, 443, 3306],
          x_shodan_city: "Frankfurt",
          x_shodan_country: "Germany",
          x_shodan_org: "GitHub Inc",
        },
        entityResolution: {
          asn: "AS36459",
          organization: "GitHub Inc",
          threat_intel: "Port 3306 (MySQL) exposed - potential risk",
        },
      },
    },
    {
      data: {
        id: "network-traffic--d0e1f2a3-b4c5-6789-3456-890123456789",
        label: "Port 3306 (MySQL)",
        type: "network-traffic",
        riskScore: 0.75,
        stix: {
          type: "network-traffic",
          id: "network-traffic--d0e1f2a3-b4c5-6789-3456-890123456789",
          dst_port: 3306,
          protocols: ["tcp"],
          x_open: true,
          x_host: "185.199.108.153",
        },
        entityResolution: {
          service: "MySQL",
          banner: "MySQL 8.0.32",
          risk_note: "Database port publicly accessible",
        },
      },
    },
  ],
  edges: [
    {
      data: {
        id: "edge--1",
        source: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        target: "domain-name--b2c3d4e5-f6a7-8901-bcde-f12345678901",
        type: "resolves_to",
        label: "resolves to",
      },
    },
    {
      data: {
        id: "edge--2",
        source: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        target: "network-traffic--c3d4e5f6-a7b8-9012-cdef-123456789012",
        type: "has_port",
        label: "443/tcp",
      },
    },
    {
      data: {
        id: "edge--3",
        source: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        target: "network-traffic--d4e5f6a7-b8c9-0123-def0-234567890123",
        type: "has_port",
        label: "53/tcp",
      },
    },
    {
      data: {
        id: "edge--4",
        source: "domain-name--b2c3d4e5-f6a7-8901-bcde-f12345678901",
        target: "note--e5f6a7b8-c9d0-1234-ef01-345678901234",
        type: "has_note",
        label: "security audit",
      },
    },
    {
      data: {
        id: "edge--5",
        source: "ipv4-addr--f6a7b8c9-d0e1-2345-f012-456789012345",
        target: "domain-name--a7b8c9d0-e1f2-3456-0123-567890123456",
        type: "resolves_to",
        label: "PTR",
      },
    },
    {
      data: {
        id: "edge--6",
        source: "domain-name--b2c3d4e5-f6a7-8901-bcde-f12345678901",
        target: "note--b8c9d0e1-f2a3-4567-1234-678901234567",
        type: "has_note",
        label: "SSL cert",
      },
    },
    {
      data: {
        id: "edge--7",
        source: "ipv4-addr--c9d0e1f2-a3b4-5678-2345-789012345678",
        target: "network-traffic--d0e1f2a3-b4c5-6789-3456-890123456789",
        type: "has_port",
        label: "3306/tcp",
      },
    },
    {
      data: {
        id: "edge--8",
        source: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        target: "ipv4-addr--f6a7b8c9-d0e1-2345-f012-456789012345",
        type: "related_to",
        label: "same ASN",
      },
    },
  ],
};

// ============================================================================
// MOCK TERMINAL STREAM OUTPUTS
// ============================================================================

export const MOCK_TERMINAL_STREAMS: Record<string, string[]> = {
  shodan: [
    '\x1b[36m[INFO]\x1b[0m Initiating Shodan recon for 8.8.8.8',
    '\x1b[90m[stream]\x1b[0m Connecting to Shodan API...',
    '\x1b[32m[success]\x1b[0m API authentication successful',
    '\x1b[90m[stream]\x1b[0m Fetching host information...',
    '\x1b[32m[RESULT]\x1b[0m Host found: dns.google',
    '\x1b[90m[stream]\x1b[0m Organization: Google LLC',
    '\x1b[90m[stream]\x1b[0m Location: Mountain View, United States',
    '\x1b[32m[RESULT]\x1b[0m Open ports: [53, 443, 80]',
    '\x1b[33m[WARNING]\x1b[0m Port 53 (DNS) is publicly accessible',
    '\x1b[90m[stream]\x1b[0m Retrieving service banners...',
    '\x1b[32m[RESULT]\x1b[0m Port 443: HTTPS (TLS 1.3)',
    '\x1b[32m[RESULT]\x1b[0m Port 53: Google Public DNS',
    '\x1b[36m[INFO]\x1b[0m STIX bundle generated with 3 objects',
    '\x1b[90m[stream]\x1b[0m Publishing to Neo4j...',
    '\x1b[32m[DONE]\x1b[0m Recon complete - 3 nodes, 5 edges created',
  ],
  port_scan: [
    '\x1b[36m[INFO]\x1b[0m Initiating port scan for 185.199.108.153',
    '\x1b[90m[stream]\x1b[0m Scanning ports: [21, 22, 80, 443, 3306, 5432, 8080]',
    '\x1b[90m[stream]\x1b[0m Using 20 concurrent workers, 2s timeout',
    '\x1b[32m[OPEN]\x1b[0m Port 22/tcp - SSH',
    '\x1b[32m[OPEN]\x1b[0m Port 80/tcp - HTTP',
    '\x1b[32m[OPEN]\x1b[0m Port 443/tcp - HTTPS',
    '\x1b[31m[RISK]\x1b[0m Port 3306/tcp - MySQL (PUBLICLY EXPOSED)',
    '\x1b[33m[WARNING]\x1b[0m Database port accessible without authentication',
    '\x1b[90m[stream]\x1b[0m Banner grabbing...',
    '\x1b[32m[RESULT]\x1b[0m SSH: OpenSSH 8.9p1',
    '\x1b[32m[RESULT]\x1b[0m MySQL: 8.0.32-0ubuntu0.22.04.2',
    '\x1b[31m[CRITICAL]\x1b[0m MySQL allows remote root login',
    '\x1b[36m[INFO]\x1b[0m Generating STIX network-traffic objects...',
    '\x1b[32m[DONE]\x1b[0m Scan complete - 4 open ports, 1 critical finding',
  ],
  dns_intel: [
    '\x1b[36m[INFO]\x1b[0m Initiating DNS intelligence for google.com',
    '\x1b[90m[stream]\x1b[0m Resolving A records...',
    '\x1b[32m[RESULT]\x1b[0m A: 142.250.185.78',
    '\x1b[32m[RESULT]\x1b[0m A: 142.250.185.110',
    '\x1b[90m[stream]\x1b[0m Resolving MX records...',
    '\x1b[32m[RESULT]\x1b[0m MX: smtp.google.com (priority 10)',
    '\x1b[90m[stream]\x1b[0m Resolving NS records...',
    '\x1b[32m[RESULT]\x1b[0m NS: ns1.google.com',
    '\x1b[32m[RESULT]\x1b[0m NS: ns2.google.com',
    '\x1b[90m[stream]\x1b[0m Checking SPF record...',
    '\x1b[32m[RESULT]\x1b[0m SPF: v=spf1 include:_spf.google.com ~all',
    '\x1b[33m[WARNING]\x1b[0m SPF uses ~all (softfail) - moderate protection',
    '\x1b[90m[stream]\x1b[0m Checking DMARC record...',
    '\x1b[32m[RESULT]\x1b[0m DMARC: v=DMARC1; p=reject; rua=mailto:dmarc@google.com',
    '\x1b[32m[SUCCESS]\x1b[0m DMARC policy is strong (reject)',
    '\x1b[90m[stream]\x1b[0m Brute-forcing subdomains (100 wordlist entries)...',
    '\x1b[32m[FOUND]\x1b[0m www.google.com -> 142.250.185.78',
    '\x1b[32m[FOUND]\x1b[0m mail.google.com -> 142.250.185.110',
    '\x1b[32m[FOUND]\x1b[0m api.google.com -> 142.250.185.46',
    '\x1b[32m[DONE]\x1b[0m DNS intel complete - 3 subdomains discovered',
  ],
  agent: [
    '\x1b[35m[AGENT]\x1b[0m Orchestrator initialized for investigation',
    '\x1b[35m[AGENT]\x1b[0m Goal: Investigate 185.199.108.153',
    '\x1b[35m[AGENT]\x1b[0m Routing to Searcher agent...',
    '\x1b[90m[Searcher]\x1b[0m Running Shodan lookup...',
    '\x1b[32m[Searcher]\x1b[0m Found: GitHub Inc, Frankfurt, Germany',
    '\x1b[90m[Searcher]\x1b[0m Running port scan...',
    '\x1b[31m[Searcher]\x1b[0m CRITICAL: MySQL port 3306 exposed',
    '\x1b[35m[AGENT]\x1b[0m Routing to Analyzer agent...',
    '\x1b[90m[Analyzer]\x1b[0m Evaluating threat score...',
    '\x1b[33m[Analyzer]\x1b[0m Risk assessment: MEDIUM-HIGH (0.65)',
    '\x1b[33m[Analyzer]\x1b[0m Reasoning: Public database exposure',
    '\x1b[35m[AGENT]\x1b[0m Synthesizing results...',
    '\x1b[35m[AGENT]\x1b[0m Generating STIX bundle...',
    '\x1b[32m[AGENT]\x1b[0m Investigation complete - 5 objects, threat_score: 0.65',
  ],
};

// ============================================================================
// MOCK NODE DETAILS (for panel preview)
// ============================================================================

export const MOCK_NODE_DETAILS: Record<string, NodeDetail> = {
  "ipv4-addr--a1b2c3d4": {
    id: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    label: "8.8.8.8 (Google Public DNS)",
    type: "ipv4-addr",
    riskScore: 0.15,
    stix: {
      type: "ipv4-addr",
      id: "ipv4-addr--a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      value: "8.8.8.8",
      x_shodan_ports: [53, 443, 80],
      x_shodan_city: "Mountain View",
      x_shodan_country: "United States",
      x_shodan_org: "Google LLC",
      x_shodan_isp: "Google LLC",
    },
    entityResolution: {
      asn: "AS15169",
      organization: "Google LLC",
      reverse_dns: "dns.google",
      whois_registrar: "ICANN",
      abuse_contact: "network-abuse@google.com",
    },
    metadata: {
      first_seen: "2026-03-20T08:15:00Z",
      last_seen: "2026-03-26T14:32:00Z",
      confidence: 0.98,
      source: "shodan_recon",
    },
  },
  "network-traffic--d0e1f2a3": {
    id: "network-traffic--d0e1f2a3-b4c5-6789-3456-890123456789",
    label: "Port 3306 (MySQL) - CRITICAL",
    type: "network-traffic",
    riskScore: 0.75,
    stix: {
      type: "network-traffic",
      id: "network-traffic--d0e1f2a3-b4c5-6789-3456-890123456789",
      dst_port: 3306,
      protocols: ["tcp"],
      x_open: true,
      x_host: "185.199.108.153",
    },
    entityResolution: {
      service: "MySQL",
      version: "8.0.32",
      banner: "MySQL 8.0.32-0ubuntu0.22.04.2",
      risk_note: "Database port publicly accessible",
      cvss_score: 7.5,
    },
    metadata: {
      first_seen: "2026-03-26T14:30:00Z",
      scan_method: "tcp_connect",
      source: "port_scanner",
      recommendation: "Restrict MySQL to localhost or trusted IPs",
    },
  },
};

// ============================================================================
// MOCK ACTIVITY TIMELINE
// ============================================================================

export const MOCK_TIMELINE_EVENTS = [
  {
    id: "event-1",
    timestamp: "2026-03-26T14:25:00Z",
    type: "investigation_started",
    title: "Investigation Initiated",
    description: "User began reconnaissance against 8.8.8.8",
    severity: "info",
  },
  {
    id: "event-2",
    timestamp: "2026-03-26T14:25:03Z",
    type: "shodan_recon",
    title: "Shodan Reconnaissance",
    description: "API lookup completed - 3 services identified",
    severity: "info",
  },
  {
    id: "event-3",
    timestamp: "2026-03-26T14:25:08Z",
    type: "port_scan",
    title: "Port Scan Executed",
    description: "Scanned 17 common ports - 4 open, 1 critical finding",
    severity: "warning",
  },
  {
    id: "event-4",
    timestamp: "2026-03-26T14:25:12Z",
    type: "stix_ingested",
    title: "STIX Objects Created",
    description: "7 STIX 2.1 objects ingested into Neo4j graph",
    severity: "info",
  },
  {
    id: "event-5",
    timestamp: "2026-03-26T14:25:15Z",
    type: "threat_scored",
    title: "Threat Assessment",
    description: "Overall risk score: 0.45 (MEDIUM)",
    severity: "warning",
  },
];

// ============================================================================
// MOCK MEDIA FORENSICS DATA
// ============================================================================

export const MOCK_IMAGE_METADATA = {
  filename: "evidence_001.jpg",
  file_type: "image" as const,
  metadata: {
    camera_make: "Apple",
    camera_model: "iPhone 14 Pro",
    software: "iOS 17.2.1",
    datetime_original: "2026-03-25T18:42:33Z",
    exposure_time: "1/120",
    f_number: "f/1.78",
    iso: 125,
    focal_length: "6.86mm",
    image_width: 4032,
    image_height: 3024,
    color_space: "sRGB",
  },
  gps: {
    latitude: 37.7749,
    longitude: -122.4194,
    location_name: "San Francisco, CA (approximate)",
  },
  analysis: {
    faces_detected: 2,
    objects_detected: ["person", "laptop", "coffee cup", "window"],
    scene_classification: "indoor/office",
    authenticity_score: 0.94,
    manipulation_detected: false,
  },
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Simulates streaming terminal output
 */
export function simulateStream(
  streamKey: string,
  onLine: (line: string) => void,
  onComplete?: () => void,
): () => void {
  const lines = MOCK_TERMINAL_STREAMS[streamKey] || MOCK_TERMINAL_STREAMS.shodan;
  let index = 0;

  const interval = setInterval(() => {
    if (index < lines.length) {
      onLine(lines[index]);
      index++;
    } else {
      clearInterval(interval);
      onComplete?.();
    }
  }, 150 + Math.random() * 200); // Variable delay for realism

  return () => clearInterval(interval);
}

/**
 * Get mock graph elements (simulates API response)
 */
export function getMockGraphElements() {
  return Promise.resolve(MOCK_GRAPH_ELEMENTS);
}

/**
 * Get mock node details (simulates API response)
 */
export function getMockNodeDetails(nodeId: string): NodeDetail | null {
  return MOCK_NODE_DETAILS[nodeId] || null;
}
