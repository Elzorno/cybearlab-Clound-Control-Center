"""
DNS management service - Hostinger API integration.
"""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx

from ..config import settings


# Hostinger API configuration
HOSTINGER_API_BASE = "https://api.hostinger.com/v1"
HOSTINGER_API_TOKEN = os.getenv("HOSTINGER_API_TOKEN", "")
DOMAIN = os.getenv("DNS_DOMAIN", "cybearlab.cloud")

# Load token from certbot credentials if not in env
if not HOSTINGER_API_TOKEN:
    creds_path = Path("/etc/letsencrypt/hostinger.ini")
    if creds_path.exists():
        try:
            content = creds_path.read_text()
            for line in content.splitlines():
                if "dns_hostinger_api_token" in line:
                    HOSTINGER_API_TOKEN = line.split("=")[1].strip()
                    break
        except Exception:
            pass


@dataclass
class DnsRecord:
    id: str
    name: str  # subdomain part (e.g., "www" or "student1")
    type: str  # A, AAAA, CNAME, TXT, MX, etc.
    content: str  # IP address, hostname, or text
    ttl: int
    priority: Optional[int] = None  # For MX records


@dataclass
class CertificateInfo:
    domain: str
    issuer: str
    valid_from: datetime
    valid_to: datetime
    days_remaining: int
    is_wildcard: bool


def _get_headers() -> dict:
    """Get API headers with auth token."""
    return {
        "Authorization": f"Bearer {HOSTINGER_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _api_available() -> bool:
    """Check if Hostinger API is configured."""
    return bool(HOSTINGER_API_TOKEN)


async def list_dns_records() -> list[DnsRecord]:
    """List all DNS records for the domain."""
    if not _api_available():
        return _get_mock_records()
    
    records = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{HOSTINGER_API_BASE}/dns/{DOMAIN}/records",
                headers=_get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                for r in data.get("records", []):
                    records.append(DnsRecord(
                        id=str(r.get("id", "")),
                        name=r.get("name", ""),
                        type=r.get("type", ""),
                        content=r.get("content", ""),
                        ttl=r.get("ttl", 3600),
                        priority=r.get("priority"),
                    ))
            else:
                # Fallback to mock if API fails
                return _get_mock_records()
    except Exception as e:
        print(f"DNS API error: {e}")
        return _get_mock_records()
    
    return records


async def create_dns_record(
    name: str,
    record_type: str,
    content: str,
    ttl: int = 3600,
    priority: Optional[int] = None
) -> tuple[bool, str]:
    """Create a new DNS record."""
    if not _api_available():
        return True, f"[MOCK] Created {record_type} record: {name}.{DOMAIN} -> {content}"
    
    try:
        payload = {
            "name": name,
            "type": record_type,
            "content": content,
            "ttl": ttl,
        }
        if priority is not None and record_type == "MX":
            payload["priority"] = priority
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{HOSTINGER_API_BASE}/dns/{DOMAIN}/records",
                headers=_get_headers(),
                json=payload
            )
            
            if response.status_code in (200, 201):
                return True, f"Created {record_type} record for {name}.{DOMAIN}"
            else:
                return False, f"API error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Failed to create record: {e}"


async def delete_dns_record(record_id: str) -> tuple[bool, str]:
    """Delete a DNS record by ID."""
    if not _api_available():
        return True, f"[MOCK] Deleted record {record_id}"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{HOSTINGER_API_BASE}/dns/{DOMAIN}/records/{record_id}",
                headers=_get_headers()
            )
            
            if response.status_code in (200, 204):
                return True, "Record deleted successfully"
            else:
                return False, f"API error: {response.status_code}"
    except Exception as e:
        return False, f"Failed to delete record: {e}"


async def update_dns_record(
    record_id: str,
    content: str,
    ttl: Optional[int] = None
) -> tuple[bool, str]:
    """Update an existing DNS record."""
    if not _api_available():
        return True, f"[MOCK] Updated record {record_id} -> {content}"
    
    try:
        payload = {"content": content}
        if ttl:
            payload["ttl"] = ttl
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{HOSTINGER_API_BASE}/dns/{DOMAIN}/records/{record_id}",
                headers=_get_headers(),
                json=payload
            )
            
            if response.status_code == 200:
                return True, "Record updated successfully"
            else:
                return False, f"API error: {response.status_code}"
    except Exception as e:
        return False, f"Failed to update record: {e}"


def get_certificate_info(domain: str = None) -> Optional[CertificateInfo]:
    """Get SSL certificate information."""
    cert_path = Path("/etc/letsencrypt/live/wildcard.cybearlab.cloud/cert.pem")
    
    if not cert_path.exists():
        return None
    
    try:
        # Use openssl to get certificate details
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_path), "-noout", "-dates", "-issuer"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        lines = result.stdout.strip().split('\n')
        issuer = ""
        not_before = None
        not_after = None
        
        for line in lines:
            if line.startswith("notBefore="):
                date_str = line.replace("notBefore=", "")
                not_before = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            elif line.startswith("notAfter="):
                date_str = line.replace("notAfter=", "")
                not_after = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            elif line.startswith("issuer="):
                issuer = line.replace("issuer=", "").strip()
        
        if not_after:
            days_remaining = (not_after - datetime.now()).days
        else:
            days_remaining = 0
        
        return CertificateInfo(
            domain=f"*.{DOMAIN}",
            issuer=issuer,
            valid_from=not_before or datetime.now(),
            valid_to=not_after or datetime.now(),
            days_remaining=days_remaining,
            is_wildcard=True,
        )
    except Exception as e:
        print(f"Certificate check error: {e}")
        return None


def get_student_subdomains() -> list[str]:
    """Get list of student subdomains from nginx configs."""
    subdomains = []
    nginx_sites = Path("/etc/nginx/sites-enabled")
    
    if not nginx_sites.exists():
        return subdomains
    
    try:
        for conf in nginx_sites.iterdir():
            if conf.is_file():
                content = conf.read_text()
                for line in content.splitlines():
                    if "server_name" in line:
                        # Extract subdomain from server_name directive
                        parts = line.strip().rstrip(";").split()
                        for part in parts[1:]:
                            if part.endswith(f".{DOMAIN}"):
                                subdomain = part.replace(f".{DOMAIN}", "")
                                if subdomain and subdomain not in subdomains:
                                    subdomains.append(subdomain)
    except Exception:
        pass
    
    return sorted(subdomains)


def _get_mock_records() -> list[DnsRecord]:
    """Return mock DNS records for demo/testing."""
    # Generate from student subdomains
    subdomains = get_student_subdomains()
    records = [
        DnsRecord(id="1", name="@", type="A", content="72.61.7.180", ttl=3600),
        DnsRecord(id="2", name="www", type="CNAME", content=DOMAIN, ttl=3600),
        DnsRecord(id="3", name="*", type="A", content="72.61.7.180", ttl=3600),
    ]
    
    # Add student subdomains
    for i, subdomain in enumerate(subdomains, start=10):
        records.append(DnsRecord(
            id=str(i),
            name=subdomain,
            type="CNAME",
            content=DOMAIN,
            ttl=3600,
        ))
    
    return records


def get_domain() -> str:
    """Get the managed domain."""
    return DOMAIN
