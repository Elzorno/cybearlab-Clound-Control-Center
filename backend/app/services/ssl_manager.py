"""
SSL/TLS certificate management service - Let's Encrypt integration.
"""

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


# Let's Encrypt paths
LETSENCRYPT_LIVE = Path("/etc/letsencrypt/live")
LETSENCRYPT_RENEWAL = Path("/etc/letsencrypt/renewal")
CERTBOT_BIN = "certbot"


@dataclass
class Certificate:
    domain: str
    domains: List[str]  # All domains covered (including SANs)
    issuer: str
    valid_from: str
    valid_until: str
    days_remaining: int
    is_expired: bool
    is_expiring_soon: bool  # < 30 days
    serial: str
    cert_path: str
    key_path: str
    chain_path: str
    auto_renew: bool


@dataclass
class CertificateRequest:
    domains: List[str]
    email: str
    webroot_path: Optional[str] = None
    standalone: bool = False
    dns_challenge: bool = False
    dry_run: bool = False


def _run_command(cmd: List[str], sudo: bool = True, timeout: int = 300) -> Tuple[bool, str]:
    """Run a system command."""
    if sudo:
        cmd = ["sudo"] + cmd
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def _parse_cert_dates(cert_path: str) -> Tuple[Optional[str], Optional[str], int]:
    """Parse certificate dates using openssl."""
    valid_from = None
    valid_until = None
    days_remaining = 0
    
    # Get start date
    success, output = _run_command(
        ["openssl", "x509", "-in", cert_path, "-noout", "-startdate"],
        sudo=False
    )
    if success:
        # notBefore=Jan  1 00:00:00 2024 GMT
        match = re.search(r'notBefore=(.+)', output)
        if match:
            valid_from = match.group(1).strip()
    
    # Get end date
    success, output = _run_command(
        ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
        sudo=False
    )
    if success:
        # notAfter=Dec 31 23:59:59 2024 GMT
        match = re.search(r'notAfter=(.+)', output)
        if match:
            valid_until = match.group(1).strip()
            
            # Calculate days remaining
            try:
                # Parse various date formats
                for fmt in ["%b %d %H:%M:%S %Y %Z", "%b  %d %H:%M:%S %Y %Z"]:
                    try:
                        end_date = datetime.strptime(valid_until, fmt)
                        days_remaining = (end_date - datetime.now()).days
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
    
    return valid_from, valid_until, days_remaining


def _parse_cert_info(cert_path: str) -> dict:
    """Parse certificate information using openssl."""
    info = {
        "issuer": "",
        "serial": "",
        "domains": [],
    }
    
    # Get issuer
    success, output = _run_command(
        ["openssl", "x509", "-in", cert_path, "-noout", "-issuer"],
        sudo=False
    )
    if success:
        # issuer=C = US, O = Let's Encrypt, CN = R3
        match = re.search(r'CN\s*=\s*([^,]+)', output)
        if match:
            info["issuer"] = match.group(1).strip()
    
    # Get serial
    success, output = _run_command(
        ["openssl", "x509", "-in", cert_path, "-noout", "-serial"],
        sudo=False
    )
    if success:
        # serial=ABCD1234...
        match = re.search(r'serial=(.+)', output)
        if match:
            info["serial"] = match.group(1).strip()
    
    # Get subject (primary domain)
    success, output = _run_command(
        ["openssl", "x509", "-in", cert_path, "-noout", "-subject"],
        sudo=False
    )
    if success:
        match = re.search(r'CN\s*=\s*([^,\n]+)', output)
        if match:
            info["domains"].append(match.group(1).strip())
    
    # Get SANs (Subject Alternative Names)
    success, output = _run_command(
        ["openssl", "x509", "-in", cert_path, "-noout", "-ext", "subjectAltName"],
        sudo=False
    )
    if success:
        for match in re.finditer(r'DNS:([^,\s]+)', output):
            domain = match.group(1).strip()
            if domain not in info["domains"]:
                info["domains"].append(domain)
    
    return info


def list_certificates() -> List[Certificate]:
    """List all Let's Encrypt certificates."""
    certs = []
    
    if not LETSENCRYPT_LIVE.exists():
        return certs
    
    for cert_dir in LETSENCRYPT_LIVE.iterdir():
        if not cert_dir.is_dir():
            continue
        
        cert_path = cert_dir / "cert.pem"
        key_path = cert_dir / "privkey.pem"
        chain_path = cert_dir / "fullchain.pem"
        
        if not cert_path.exists():
            continue
        
        domain = cert_dir.name
        
        # Parse certificate info
        valid_from, valid_until, days_remaining = _parse_cert_dates(str(cert_path))
        cert_info = _parse_cert_info(str(cert_path))
        
        is_expired = days_remaining < 0
        is_expiring_soon = 0 <= days_remaining <= 30
        
        # Check auto-renewal status
        renewal_conf = LETSENCRYPT_RENEWAL / f"{domain}.conf"
        auto_renew = renewal_conf.exists()
        
        certs.append(Certificate(
            domain=domain,
            domains=cert_info.get("domains", [domain]),
            issuer=cert_info.get("issuer", "Unknown"),
            valid_from=valid_from or "Unknown",
            valid_until=valid_until or "Unknown",
            days_remaining=days_remaining,
            is_expired=is_expired,
            is_expiring_soon=is_expiring_soon,
            serial=cert_info.get("serial", ""),
            cert_path=str(cert_path),
            key_path=str(key_path),
            chain_path=str(chain_path),
            auto_renew=auto_renew,
        ))
    
    return sorted(certs, key=lambda c: c.domain)


def get_certificate(domain: str) -> Certificate:
    """Get details for a specific certificate."""
    certs = list_certificates()
    for cert in certs:
        if cert.domain == domain or domain in cert.domains:
            return cert
    raise ValueError(f"Certificate not found for domain: {domain}")


def request_certificate(request: CertificateRequest) -> Certificate:
    """
    Request a new Let's Encrypt certificate.
    
    Args:
        request: CertificateRequest with domains, email, and method
        
    Returns:
        Created Certificate object
    """
    if not request.domains:
        raise ValueError("At least one domain is required")
    
    if not request.email:
        raise ValueError("Email is required for Let's Encrypt registration")
    
    # Build certbot command
    cmd = [CERTBOT_BIN, "certonly"]
    
    # Add domains
    for domain in request.domains:
        cmd.extend(["-d", domain])
    
    # Add email
    cmd.extend(["--email", request.email])
    
    # Non-interactive
    cmd.append("--non-interactive")
    cmd.append("--agree-tos")
    
    # Challenge method
    if request.standalone:
        cmd.append("--standalone")
    elif request.dns_challenge:
        cmd.append("--manual")
        cmd.append("--preferred-challenges")
        cmd.append("dns")
    elif request.webroot_path:
        cmd.extend(["--webroot", "-w", request.webroot_path])
    else:
        # Default to Apache plugin
        cmd.append("--apache")
    
    # Dry run if requested
    if request.dry_run:
        cmd.append("--dry-run")
    
    success, output = _run_command(cmd, timeout=600)
    
    if not success:
        raise ValueError(f"Certificate request failed: {output}")
    
    if request.dry_run:
        # Return a placeholder for dry run
        return Certificate(
            domain=request.domains[0],
            domains=request.domains,
            issuer="Let's Encrypt (dry run)",
            valid_from="N/A",
            valid_until="N/A",
            days_remaining=90,
            is_expired=False,
            is_expiring_soon=False,
            serial="dry-run",
            cert_path="N/A",
            key_path="N/A",
            chain_path="N/A",
            auto_renew=True,
        )
    
    # Return the new certificate
    return get_certificate(request.domains[0])


def renew_certificate(domain: str, force: bool = False) -> Certificate:
    """
    Renew a certificate.
    
    Args:
        domain: Domain name to renew
        force: Force renewal even if not expiring
        
    Returns:
        Renewed Certificate object
    """
    cmd = [CERTBOT_BIN, "renew", "--cert-name", domain]
    
    if force:
        cmd.append("--force-renewal")
    
    success, output = _run_command(cmd, timeout=600)
    
    if not success:
        raise ValueError(f"Certificate renewal failed: {output}")
    
    return get_certificate(domain)


def renew_all_certificates(dry_run: bool = False) -> List[dict]:
    """
    Renew all certificates that are due for renewal.
    
    Args:
        dry_run: Test renewal without making changes
        
    Returns:
        List of renewal results
    """
    cmd = [CERTBOT_BIN, "renew"]
    
    if dry_run:
        cmd.append("--dry-run")
    
    success, output = _run_command(cmd, timeout=900)
    
    results = []
    
    # Parse output for results
    for line in output.split("\n"):
        if "renewal" in line.lower() or "renewed" in line.lower():
            results.append({"message": line.strip(), "success": "success" in line.lower()})
    
    if not results:
        results.append({
            "message": "No certificates due for renewal" if success else output,
            "success": success
        })
    
    return results


def revoke_certificate(domain: str, reason: str = "unspecified") -> bool:
    """
    Revoke a certificate.
    
    Args:
        domain: Domain name to revoke
        reason: Revocation reason (unspecified, keycompromise, affiliationchanged, superseded, cessationofoperation)
        
    Returns:
        True if successful
    """
    valid_reasons = ["unspecified", "keycompromise", "affiliationchanged", "superseded", "cessationofoperation"]
    if reason not in valid_reasons:
        raise ValueError(f"Invalid reason. Must be one of: {', '.join(valid_reasons)}")
    
    cert = get_certificate(domain)
    
    cmd = [CERTBOT_BIN, "revoke", "--cert-path", cert.cert_path, "--reason", reason, "--non-interactive"]
    
    success, output = _run_command(cmd)
    
    if not success:
        raise ValueError(f"Certificate revocation failed: {output}")
    
    return True


def delete_certificate(domain: str) -> bool:
    """
    Delete a certificate (removes from Let's Encrypt management).
    
    Args:
        domain: Domain name to delete
        
    Returns:
        True if successful
    """
    cmd = [CERTBOT_BIN, "delete", "--cert-name", domain, "--non-interactive"]
    
    success, output = _run_command(cmd)
    
    if not success:
        raise ValueError(f"Certificate deletion failed: {output}")
    
    return True


def test_renewal(domain: str) -> dict:
    """
    Test certificate renewal without making changes.
    
    Args:
        domain: Domain to test
        
    Returns:
        Test result with success status and message
    """
    cmd = [CERTBOT_BIN, "renew", "--cert-name", domain, "--dry-run"]
    
    success, output = _run_command(cmd, timeout=300)
    
    return {
        "success": success,
        "message": output,
        "domain": domain,
    }


def get_acme_challenges_pending() -> List[dict]:
    """Get any pending ACME challenges (for manual DNS verification)."""
    # This would need integration with certbot's internal state
    # For now, return empty list
    return []


def check_certificate_expiry_warnings() -> List[dict]:
    """Check for certificates expiring soon and return warnings."""
    warnings = []
    certs = list_certificates()
    
    for cert in certs:
        if cert.is_expired:
            warnings.append({
                "domain": cert.domain,
                "severity": "critical",
                "message": f"Certificate for {cert.domain} has EXPIRED!",
                "days_remaining": cert.days_remaining,
            })
        elif cert.is_expiring_soon:
            warnings.append({
                "domain": cert.domain,
                "severity": "warning",
                "message": f"Certificate for {cert.domain} expires in {cert.days_remaining} days",
                "days_remaining": cert.days_remaining,
            })
    
    return warnings
