import re
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError


class YtysxsIE(InfoExtractor):
    IE_NAME = 'ytysxs'
    IE_DESC = '悦聽有聲書 (ytysxs.com)'
    _VALID_URL = r'https?://(?:www\.)?ytysxs\.com/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.ytysxs.com/16694.html',
        'info_dict': {
            'id': '16694',
            'title': '《苟在武道世界成聖》有聲書小說|東方玄幻小說|在水中的紙老虎著|老寶玉_白玉京播',
        },
        'playlist_mincount': 148,   # 148 tracks across two playlists
    }]

    _HEADERS = {
        'Referer': 'https://www.ytysxs.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers=self._HEADERS)

        # Title: prefer Open Graph, then meta description, then ID
        title = (
            self._og_search_title(webpage, default=None)
            or self._html_search_meta('description', webpage)
            or video_id
        )

        # Find all AudioIgniter playlist IDs on the page
        playlist_ids = re.findall(
            r'data-tracks-url="[^"]*audioigniter_playlist_id=(\d+)', webpage
        )
        if not playlist_ids:
            raise ExtractorError('No AudioIgniter playlists found on the page', expected=True)

        entries = []
        for pl_id in playlist_ids:
            playlist_url = f'https://www.ytysxs.com/?audioigniter_playlist_id={pl_id}'
            try:
                playlist_data = self._download_json(
                    playlist_url, video_id,
                    headers=self._HEADERS,
                    note=f'Downloading playlist {pl_id}',
                    errnote=f'Unable to download playlist {pl_id}',
                )
            except ExtractorError as e:
                self.report_warning(f'Skipping playlist {pl_id}: {e}')
                continue

            # The endpoint returns a list directly – no wrapper object
            if not isinstance(playlist_data, list):
                self.report_warning(f'Unexpected playlist format for {pl_id}, skipping')
                continue

            for track in playlist_data:
                audio_url = track.get('audio')
                if not audio_url:
                    continue

                track_title = track.get('title', '')
                artist = track.get('subtitle', '')  # narrator name

                entry = {
                    'id': self._search_regex(r'/([^/]+)\.mp3', audio_url, 'track id', default=audio_url),
                    'title': track_title,
                    'url': audio_url,
                    'artist': artist,
                    'extractor': self.IE_NAME,
                    'webpage_url': url,
                }
                entries.append(entry)

        if not entries:
            raise ExtractorError('No audio tracks could be extracted', expected=True)

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': title,
            'entries': entries,
        }
