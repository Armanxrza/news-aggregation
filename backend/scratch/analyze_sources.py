import asyncio
import aiohttp
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import json

raw_list = """onlinekhabar.com
setopati.com
ratopati.com
annapurnapost.com
ekantipur.com
baahrakhari.com
kharibot.com
ktmsamachar.com
kathmandutoday.com
tajakhabar.com
clickmandu.com
bizmandu.com
purbadharkhabar.com
arthakoartha.com
capitalnepal.com
aashthanews.com
wadapalika.com
nagariknews.nagariknetwork.com
nayapatrikadaily.com
aarthikkhabar.com
sunaulonepal.com
kathmandupost.com
thehimalayantimes.com
bbc.com/nepali
rajdhanidaily.com
laganinews.com
pardafas.com
taksaarnews.com
karobaardainik.com
aarthikabhiyaan.com
nepalitimes.com
samacharpatra.com
himalayadarpan.com
osnepal.com
thahakhabar.com
koshionline.com
hamrokura.com
arthasarokar.com
nepalipatra.com
nepalsamaye.com
bizsala.com
ujyaaloonline.com
himalkhabar.com
goalnepal.com
hamrokhelkud.com
radionepal.gov.np
janakpurtoday.com.np
khabarpurwanchal.com
blastkhabar.com
avenues.tv
radiosagarmatha.org.np
nepalipost.com"""

async def check_rss(session, domain):
    if not domain.startswith("http"):
        url = f"https://{domain}"
    else:
        url = domain
        
    rss_links = []
    
    try:
        # Check homepage for RSS meta tags
        async with session.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                links = soup.find_all('link', type='application/rss+xml')
                for link in links:
                    href = link.get('href')
                    if href:
                        rss_links.append(urljoin(url, href))
                        
        # If no meta tag found, try common paths
        if not rss_links:
            common_paths = ['/feed', '/rss', '/rss.xml', '/feed/']
            for path in common_paths:
                test_url = urljoin(url, path)
                try:
                    async with session.get(test_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'}) as res:
                        if res.status == 200:
                            text = await res.text()
                            if "rss" in text[:500].lower() or "feed" in text[:500].lower() or "<?xml" in text[:50]:
                                rss_links.append(test_url)
                                break
                except:
                    pass
                    
        return {"domain": domain, "rss_links": list(set(rss_links)), "status": "Success" if rss_links else "No RSS Found"}
        
    except Exception as e:
        return {"domain": domain, "rss_links": [], "status": f"Error: {str(e)}"}

async def main():
    domains = [d.strip() for d in raw_list.split('\n') if d.strip()]
    results = []
    
    # We need beautifulsoup4 installed
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "beautifulsoup4"])

    async with aiohttp.ClientSession() as session:
        tasks = [check_rss(session, domain) for domain in domains]
        results = await asyncio.gather(*tasks)
        
    with open("rss_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
        
    success = [r for r in results if r['rss_links']]
    print(f"Total Sources: {len(domains)}")
    print(f"Sources with RSS: {len(success)}")
    print(f"Sources without RSS/Errors: {len(domains) - len(success)}")

if __name__ == "__main__":
    asyncio.run(main())
