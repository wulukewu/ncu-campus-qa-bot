#!/usr/bin/env python3
"""
Utility script to find iframe URLs in web pages.
Useful for discovering the actual content URL when pages use iframes.

Usage:
    python find_iframe.py <url>
    python find_iframe.py https://pdc.adm.ncu.edu.tw/form_course.asp
    python find_iframe.py https://pdc.adm.ncu.edu.tw/form_reg.asp --insecure
"""

import argparse
import sys
from urllib.parse import urljoin

import certifi
import requests
from bs4 import BeautifulSoup


def find_iframes(url: str, insecure: bool = False) -> list:
    """
    Fetch a URL and extract all iframe sources.
    Returns a list of absolute iframe URLs.
    """
    try:
        verify_arg = False if insecure else certifi.where()
        
        print(f"Fetching: {url}")
        r = requests.get(url, verify=verify_arg, timeout=30)
        
        # Try to detect encoding (common for Chinese websites)
        r.encoding = r.apparent_encoding or 'big5'
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, 'html.parser')
        iframes = soup.find_all('iframe')
        
        if not iframes:
            print("❌ No iframes found on the page")
            return []
        
        print(f"✅ Found {len(iframes)} iframe(s)\n")
        
        results = []
        for i, iframe in enumerate(iframes, 1):
            src = iframe.get('src', '')
            if src:
                abs_url = urljoin(url, src)
                results.append(abs_url)
                
                print(f"Iframe #{i}:")
                print(f"  Relative: {src}")
                print(f"  Absolute: {abs_url}")
                
                # Show other attributes if present
                if iframe.get('width') or iframe.get('height'):
                    print(f"  Size: {iframe.get('width', '?')} x {iframe.get('height', '?')}")
                if iframe.get('title'):
                    print(f"  Title: {iframe.get('title')}")
                print()
            else:
                print(f"Iframe #{i}: (no src attribute)")
                print()
        
        return results
        
    except requests.RequestException as e:
        print(f"❌ Error fetching URL: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Find iframe URLs in web pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_iframe.py https://pdc.adm.ncu.edu.tw/form_course.asp --insecure
  python find_iframe.py https://pdc.adm.ncu.edu.tw/form_reg.asp --insecure
  
Common NCU Admin Pages:
  - Course Forms:        https://pdc.adm.ncu.edu.tw/form_course.asp
  - Registration Forms:  https://pdc.adm.ncu.edu.tw/form_reg.asp
  - Statistics:          https://pdc.adm.ncu.edu.tw/rate_note_reg1.asp
        """
    )
    parser.add_argument('url', help='URL of the page to check for iframes')
    parser.add_argument('--insecure', action='store_true',
                        help='Disable SSL certificate verification')
    
    args = parser.parse_args()
    
    # Suppress SSL warnings if insecure mode
    if args.insecure:
        try:
            import urllib3
            urllib3.disable_warnings()
        except ImportError:
            pass
    
    iframes = find_iframes(args.url, insecure=args.insecure)
    
    if iframes:
        print("=" * 60)
        print("Summary: Use these URLs in your downloader scripts:")
        print("=" * 60)
        for url in iframes:
            print(f"  {url}")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
