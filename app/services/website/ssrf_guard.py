"""SSRF (Server-Side Request Forgery) protection and URL validation guard."""

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple


class SSRFSecurityException(Exception):
    """Raised when an outbound URL points to a forbidden or private network destination."""
    pass


# Private, loopback, link-local, carrier-grade NAT, and documentation IPv4 / IPv6 networks
FORBIDDEN_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),       # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local / Cloud metadata (e.g. AWS 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),       # Private Class B
    ipaddress.ip_network("192.0.0.0/24"),        # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),        # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),      # Private Class C
    ipaddress.ip_network("198.18.0.0/15"),       # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),     # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),      # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),         # Multicast
    ipaddress.ip_network("240.0.0.0/4"),         # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),             # Loopback
    ipaddress.ip_network("::/128"),              # Unspecified
    ipaddress.ip_network("::ffff:0:0/96"),       # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),        # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),            # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),       # Documentation
    ipaddress.ip_network("fc00::/7"),            # Unique local address (private)
    ipaddress.ip_network("fe80::/10"),           # Link-local unicast
    ipaddress.ip_network("ff00::/8"),            # Multicast
]


def is_ip_forbidden(ip_str: str) -> bool:
    """Check if an IP string belongs to any private, loopback, or restricted network."""
    try:
        ip = ipaddress.ip_address(ip_str)
        # Check standard properties
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return True
        # Check explicit forbidden networks
        for net in FORBIDDEN_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        return True


def validate_url_safe(url: str) -> Tuple[bool, str, str]:
    """
    Validate that a URL is safe to fetch and does not resolve to private/local networks.

    Returns:
        (is_safe: bool, reason_or_normalized_url: str, canonical_host: str)
    """
    if not url:
        return (False, "URL is empty", "")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        return (False, f"Forbidden URL scheme '{parsed.scheme}'. Only http and https are permitted.", "")

    hostname = parsed.hostname
    if not hostname:
        return (False, "Invalid URL host", "")

    # Reject localhost strings directly
    lower_host = hostname.lower()
    if lower_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"):
        return (False, f"Restricted destination '{hostname}' is blocked by SSRF guard.", hostname)

    # Perform DNS resolution to inspect all underlying target IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if is_ip_forbidden(ip_str):
                return (False, f"Resolved IP '{ip_str}' for host '{hostname}' is in a restricted network range.", hostname)
    except socket.gaierror as e:
        return (False, f"DNS resolution failed for host '{hostname}': {str(e)}", hostname)
    except Exception as e:
        return (False, f"Error validating destination '{hostname}': {str(e)}", hostname)

    normalized_url = parsed.geturl()
    return (True, normalized_url, hostname)
