from bs4 import BeautifulSoup


def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')

    h1 = soup.find('h1')
    title = soup.find('title')
    meta_desc = soup.find('meta', attrs={'name': 'description'})

    return {
        'h1': h1.get_text(strip=True) if h1 else '',
        'title': title.get_text(strip=True) if title else '',
        'description': (
            meta_desc.get('content', '').strip() if meta_desc else ''
        ),
    }
