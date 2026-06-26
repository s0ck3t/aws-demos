import os
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser

class BrentwoodLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_link = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href')
            if href:
                self.current_link = href
                self.current_text = []

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.current_link is not None:
            text = "".join(self.current_text).strip()
            self.links.append((self.current_link, text))
            self.current_link = None
            self.current_text = []

def sanitize_filename(name):
    # Remove (PDF) or (pdf) from name
    name = re.sub(r'\s*\([Pp][Dd][Ff]\)\s*', '', name)
    # Replace non-alphanumeric characters with spaces or dashes
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Strip spaces
    name = name.strip()
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    return name

def main():
    target_url = "https://www.brentwood.gov.uk/strategies-and-policies"
    output_dir = "brentwood-housing-policies"
    
    os.makedirs(output_dir, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetching main page: {target_url}")
    req = urllib.request.Request(target_url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching main page: {e}")
        return

    parser = BrentwoodLinkParser()
    parser.feed(html)
    
    # Filter links that are PDFs or media items likely to be PDFs
    pdf_links = []
    seen_urls = set()
    
    for href, text in parser.links:
        # Check if URL looks like a PDF or a media document
        is_pdf_href = href.lower().endswith('.pdf')
        is_media = '/media/' in href
        
        # We also look at the link text
        is_pdf_text = 'pdf' in text.lower() or 'policy' in text.lower() or 'strategy' in text.lower() or 'notice' in text.lower() or 'procedure' in text.lower()
        
        # If it's a media link, or specifically ends with .pdf, or has pdf in the text and is a media link
        if is_pdf_href or is_media:
            full_url = urllib.parse.urljoin(target_url, href)
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                # Fallback text if empty
                if not text:
                    text = href.split('/')[-1]
                pdf_links.append((full_url, text))
                
    print(f"Found {len(pdf_links)} candidate PDF/media links.")
    
    for i, (url, text) in enumerate(pdf_links, 1):
        filename = sanitize_filename(text)
        filepath = os.path.join(output_dir, filename)
        
        print(f"[{i}/{len(pdf_links)}] Downloading {filename} from {url}...")
        
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                content_type = response.headers.get('Content-Type', '')
                # Follow redirect check (if URL changed or headers specify PDF)
                final_url = response.geturl()
                
                # Check if it is indeed a PDF
                if 'application/pdf' in content_type or final_url.lower().endswith('.pdf') or 'octet-stream' in content_type:
                    data = response.read()
                    with open(filepath, 'wb') as f:
                        f.write(data)
                    print(f"   Saved to {filepath} ({len(data)} bytes)")
                else:
                    # Maybe it's a webpage redirecting or showing a link to the PDF
                    # Let's read some content to see if we can find a direct PDF link
                    content = response.read()
                    print(f"   Skipped: Not a direct PDF (Content-Type: {content_type})")
        except Exception as e:
            print(f"   Error downloading: {e}")

if __name__ == '__main__':
    main()
