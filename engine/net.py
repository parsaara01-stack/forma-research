"""Bounded retries for the two public non-SEC providers"""
import time
import http.client
import urllib.error
import urllib.parse
import urllib.request


def download(url: str) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'www.ishares.com', 'fred.stlouisfed.org'}:
        raise ValueError('Unexpected public data provider')
    request = urllib.request.Request(url, headers={'User-Agent': 'forma-research/0.3 public research'})
    for attempt, timeout in enumerate((30, 60, 120)):
        pause = 2 ** (attempt + 1)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise
            retry_after = exc.headers.get('Retry-After', '') if exc.headers else ''
            pause = min(30, max(pause, int(retry_after) if retry_after.isdigit() else 0))
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as exc:
            if attempt == 2:
                raise OSError(f'Public source unavailable after three attempts: {parsed.hostname}') from exc
        time.sleep(pause)
    raise OSError('Public source retries exhausted')
