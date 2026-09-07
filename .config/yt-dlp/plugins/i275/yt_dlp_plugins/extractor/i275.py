import re
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, clean_html, urljoin


class I275IE(InfoExtractor):
    IE_NAME = 'i275'
    IE_DESC = '275听书网 (i275.com)'
    _VALID_URL = r'https?://(?:www\.|m\.)?i275\.com/(?:(?:book/(?P<book_id>\d+))|(?:play/(?P<play_book_id>\d+)/(?P<chapter_id>\d+)))\.html'
    _TESTS = [{
        'url': 'https://m.i275.com/play/39186/23328605.html',
        'info_dict': {
            'id': '23328605',
            'ext': 'm4a',
            'title': '苟在武道世界成圣 001 乱世',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.i275.com/book/39186.html',
        'info_dict': {
            'id': '39186',
            'title': '苟在武道世界成圣丨狠辣杀伐丨黑暗乱世丨老宝玉丨多人有声剧',
        },
        'playlist_mincount': 1590,
        'params': {'skip_download': True},
    }]
    _COMMON_HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/148.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Referer': 'https://m.i275.com/',
    }

    def _to_mobile_url(self, url):
        return re.sub(r'https?://(?:www\.)?i275\.com', 'https://m.i275.com', url)

    def _real_extract(self, url):
        mobile_url = self._to_mobile_url(url)

        # Critical: establish session cookies
        self._download_webpage(
            'https://m.i275.com/', None,
            note='Initializing session',
            headers=self._COMMON_HEADERS,
            fatal=False,
        )

        mobj = re.match(self._VALID_URL, url)
        book_id = mobj.group('book_id')
        play_book_id = mobj.group('play_book_id')
        chapter_id = mobj.group('chapter_id')

        if book_id:
            return self._extract_book(book_id, mobile_url)
        return self._extract_play(play_book_id, chapter_id, mobile_url)

    def _extract_book(self, book_id, url):
        entries = []
        page = 1
        page_size = 30
        total = None
        title = book_id

        while True:
            page_url = f'{url}?page={page}' if page > 1 else url
            webpage = self._download_webpage(
                page_url, book_id,
                note=f'Downloading book page {page}',
                headers=self._COMMON_HEADERS,
            )

            if page == 1:
                title = (
                    self._og_search_title(webpage, default=None)
                    or self._html_search_regex(
                        r'<h1[^>]*class="[^"]*text-2xl[^"]*"[^>]*>(.*?)</h1>',
                        webpage, 'title', default=None)
                    or self._html_search_meta('description', webpage, default=None)
                    or book_id
                )
                title = clean_html(title).strip() if title else book_id

                m = re.search(r'正文目录\s*\((\d+)\)', webpage)
                if m:
                    total = int(m.group(1))

            chapter_links = re.findall(
                r'<a\b[^>]*href=["\'](/play/(\d+)/(\d+)\.html)["\'][^>]*>'
                r'.*?<span[^>]*class="[^"]*text-sm[^"]*"[^>]*>(.*?)</span>',
                webpage, re.S | re.I)

            if not chapter_links:
                chapter_links = re.findall(
                    r'<a\b[^>]*href=["\'](/play/(\d+)/(\d+)\.html)["\'][^>]*>'
                    r'(?:.*?<span[^>]*>)?(.*?)</(?:span|a)>',
                    webpage, re.S | re.I)

            if not chapter_links:
                break

            for href, _, chapter_id, inner in chapter_links:
                chapter_title = clean_html(inner).strip()
                chapter_title = re.sub(r'^\d+\.\s*', '', chapter_title).strip()
                if not chapter_title:
                    chapter_title = chapter_id

                full_url = urljoin('https://m.i275.com', href)
                entries.append(self.url_result(
                    full_url,
                    video_id=chapter_id,
                    video_title=chapter_title,
                ))

            if total and len(entries) >= total:
                break
            if len(chapter_links) < page_size:
                break
            page += 1

        if not entries:
            raise ExtractorError('No chapters found for this book', expected=True)

        return self.playlist_result(entries, book_id, title)

    def _extract_play(self, play_book_id, chapter_id, url):
        max_retries = 6
        audio_url = None
        webpage = None

        for attempt in range(max_retries):
            webpage = self._download_webpage(
                url, chapter_id,
                note=f'Downloading play page (attempt {attempt + 1}/{max_retries})',
                headers=self._COMMON_HEADERS,
            )

            candidates = re.findall(
                r"url:\s*['\"](https?://[^'\"]+\.(?:m4a|mp3)[^'\"]*)['\"]", webpage)

            for c in candidates:
                if 'xmcdn.com' in c:
                    audio_url = c
                    break

            if audio_url:
                break

            if candidates and all('tingshijie.com' in c for c in candidates):
                self.to_screen(f'{chapter_id}: got broken tingshijie URL, retrying...')
                continue

            if candidates:
                audio_url = candidates[0]
                break

        if not audio_url or 'tingshijie.com' in audio_url:
            raise ExtractorError(
                'Unable to extract a working audio URL (got tingshijie or none). '
                'Please try again.', expected=True)

        title = (
            self._og_search_title(webpage, default=None)
            or self._html_search_meta('description', webpage, default=None)
            or self._html_search_regex(r'<h1[^>]*>(.*?)</h1>', webpage, 'title', default=None)
            or chapter_id
        )
        title = clean_html(title).strip() if title else chapter_id

        return {
            'id': chapter_id,
            'title': title,
            'url': audio_url,
            'ext': 'm4a' if '.m4a' in audio_url else 'mp3',
        }
