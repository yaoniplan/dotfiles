# https://github.com/Silent1566/OmniBox-Spider/blob/f7e15bc9d228a647a360eee75765ac6e462e3197/听书/275听书.js
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    clean_html,
    urljoin,
)


class I275IE(InfoExtractor):
    IE_NAME = 'i275'
    _VALID_URL = r'https?://(?:www\.)?i275\.com/play/(?P<book_id>\d+)/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.i275.com/play/39186/23328605.html',
        'info_dict': {
            'id': '23328605',
            'ext': 'm4a',
            'title': '苟在武道世界成圣 001 乱世',
        },
    }]

    def _resolve_lrts(self, token):
        parts = token.split('#')
        if len(parts) < 3:
            raise ExtractorError('Invalid LRTS token format')

        entity_match = re.match(r'^lrts\$(\d+)$', parts[0])
        if not entity_match:
            raise ExtractorError('Invalid LRTS entity ID')

        entity_id = entity_match.group(1)
        track_id = parts[1]
        section = parts[2]

        params = {
            'entityId': entity_id,
            'entityType': '3',
            'opType': '1',
            'sections': f'[{section}]',
            'type': '0',
            'id': track_id,
            'section': section,
        }
        headers = {'Referer': 'https://m.lrts.me/'}

        for endpoint in ['getPlayPath', 'getListenPath']:
            payload = self._download_json(
                f'https://m.lrts.me/ajax/{endpoint}',
                section, fatal=False, query=params, headers=headers) or {}

            audio_url = None
            if endpoint == 'getPlayPath':
                lst = payload.get('list') or []
                if lst:
                    audio_url = lst[0].get('path')
            else:
                audio_url = payload.get('data', {}).get('path')

            if str(payload.get('status')) == '0' and audio_url and audio_url.startswith('http'):
                return audio_url

        raise ExtractorError('Failed to resolve LRTS audio path')

    def _real_extract(self, url):
        book_id, audio_id = self._match_valid_url(url).groups()
        book_url = f'https://www.i275.com/book/{book_id}.html'

        # Initialize PHPSESSID cookie by requesting book page first to prevent redirect to homepage
        self._download_webpage(book_url, audio_id, note='Establishing session', fatal=False)

        headers = {'Referer': book_url}
        webpage = self._download_webpage(url, audio_id, headers=headers)

        title = self._html_search_regex(
            r'<title>(?:正在播放：)?(.*?)(?: - |-275听书网|$)', webpage, 'title', default=audio_id)

        audio_match = self._search_regex(
            r'''audio\s*:\s*\[\s*\{[\s\S]*?\burl\s*:\s*["']([^"']+)["']''',
            webpage, 'audio url')

        # Fix URL escaping without turning &timestamp= into ×tamp
        audio_url = audio_match.replace('\\/', '/')
        audio_url = audio_url.replace('&amp;', '&').replace('&quot;', '"')

        referer = url
        if audio_url.startswith('lrts$'):
            audio_url = self._resolve_lrts(audio_url)
            referer = 'https://m.lrts.me/'

        if audio_url.startswith('http://'):
            audio_url = 'https://' + audio_url[7:]

        return {
            'id': audio_id,
            'title': title.strip(),
            'url': audio_url,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'Referer': referer,
            },
        }


class I275BookIE(InfoExtractor):
    IE_NAME = 'i275:book'
    _VALID_URL = r'https?://(?:www\.)?i275\.com/book/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.i275.com/book/39186.html',
        'playlist_mincount': 100,
        'info_dict': {
            'id': '39186',
            'title': '苟在武道世界成圣丨狠辣杀伐丨黑暗乱世丨老宝玉丨多人有声剧',
        },
    }]

    def _real_extract(self, url):
        book_id = self._match_id(url)
        webpage = self._download_webpage(url, book_id)

        book_title = self._html_search_regex(
            r'<h1[^>]*>([\s\S]*?)</h1>', webpage, 'book title', default=None)
        if book_title:
            book_title = clean_html(book_title)

        description = self._html_search_regex(
            r'>作品简介</h3>\s*<p[^>]*>([\s\S]*?)</p>', webpage, 'description', default=None)
        if description:
            description = clean_html(description)

        episodes = re.findall(
            r'''href=["'](/play/\d+/\d+\.html)["'][\s\S]*?<span[^>]*class=["'][^"']*truncate[^"']*["'][^>]*>([\s\S]*?)</span>''',
            webpage)

        entries = []
        for ep_path, ep_title in episodes:
            ep_url = urljoin('https://www.i275.com', ep_path)
            clean_title = clean_html(ep_title).replace('$', '￥').replace('#', '﹟')
            entries.append(self.url_result(
                ep_url, ie=I275IE.ie_key(), video_title=clean_title))

        return self.playlist_result(
            entries,
            playlist_id=book_id,
            playlist_title=book_title,
            playlist_description=description)
