import re
from urllib.parse import urlparse
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, url_or_none

class YhdmIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?yhdm\.one/vod-play/(?P<id>\d+)/(?P<ep>ep\d+)\.html'
    IE_NAME = 'yhdm'
    IE_DESC = '樱花动漫 (yhdm.one)'

    _HEADERS = {
        'Referer': 'https://yhdm.one/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }

    # ======================================================================
    #  Single source configuration  (order = priority, key = source label,
    #  value = list of domain patterns for that source)
    # ======================================================================
    _SOURCES = {
        'WJ': ['ppqrrs.com'],                # v1, v10, etc.
        'UK': ['ukzy.ukubf3.com'],
        'YH': ['vod12.wgslsw.com'],
        'JY': ['hd.ijycnd.com'],
        'SN': ['yuglf.com'],                # v13, v14, etc.
        'GS': ['v.gsuus.com'],
        'XL': ['play.xluuss.com'],
        'HN': ['hn.bfvvs.com'],
        'MD': ['play.modujx11.com'],
        'IK': ['bfikuncdn.com'],
        'FF': ['vip.ffzy-plays.com'],
        'LZ': ['v.lzcdn27.com'],
        'JS': ['vv.jisuzyv.com'],
    }

    # ======================================================================
    #  (The rest of the extractor is unchanged – you don’t need to edit it)
    # ======================================================================

    def _label_from_url(self, url):
        """Return the source label for a given m3u8 URL based on domain."""
        try:
            host = urlparse(url).hostname
            if host:
                for label, domains in self._SOURCES.items():
                    if any(domain in host for domain in domains):
                        return label
        except Exception:
            pass
        return None

    def _real_extract(self, url):
        video_id, ep = self._match_valid_url(url).group('id', 'ep')
        display_id = f"{video_id}_{ep}"

        # 1. Download main page (needed for title)
        webpage = self._download_webpage(url, display_id, headers=self._HEADERS)

        # --- Title extraction ---
        title = self._html_search_regex(
            r'<title>([^<]+?)</title>', webpage, 'title', default=display_id).strip()
        if ' - ' in title:
            title = title.rsplit(' - ', 1)[0].strip()
        if title.endswith('在线播放'):
            title = title[:-4].strip()

        # 2. Fetch source list from dynamic API (with retries)
        api_url = f'https://yhdm.one/_get_plays/{video_id}/{ep}'

        api_data = None
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            api_data = self._download_json(
                api_url, display_id,
                headers=self._HEADERS,
                note=f'Fetching source list (attempt {attempt}/{max_retries})',
                fatal=False)
            if api_data and 'video_plays' in api_data:
                break
            if attempt < max_retries:
                self.report_warning(
                    f'Failed to fetch source list (attempt {attempt}), retrying...')
                self.sleep(2, display_id)

        sources = {}
        if api_data and 'video_plays' in api_data:
            for play in api_data['video_plays']:
                m3u8_url = play.get('play_data')
                if not m3u8_url or '.m3u8' not in m3u8_url:
                    continue
                clean = url_or_none(m3u8_url)
                if not clean:
                    continue
                label = self._label_from_url(clean) or f'source_{len(sources)}'
                if label not in sources:
                    sources[label] = clean

        # 3. Fallback: scrape static HTML (may contain labelled <a> tags)
        if not sources:
            for match in re.finditer(
                    r'/_player_x_/(https?://[^"]+\.m3u8)"[^>]*>([^<]+)</a>',
                    webpage):
                m3u8_url, label = match.groups()
                label = label.strip()
                clean = url_or_none(m3u8_url)
                if clean and label and label not in sources:
                    sources[label] = clean

        if not sources:
            raise ExtractorError('No video sources found.', expected=True)

        # 4. Select the highest‑priority source according to _SOURCES order
        chosen_url = None
        for label in self._SOURCES:
            if label in sources:
                chosen_url = sources[label]
                break
        if not chosen_url:
            chosen_url = next(iter(sources.values()))

        return {
            'id': display_id,
            'title': title,
            'url': chosen_url,
            'ext': 'mp4',
            'http_headers': self._HEADERS,
        }
