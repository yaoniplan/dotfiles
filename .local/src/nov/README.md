- #### Use ["nov"](https://github.com/yaoniplan/dotfiles/tree/development/.local/src/nov)
    - `nov`
- ***Notes***
    - `uv sync` # Install dependencies
        - `vim ~/.local/bin/nov` # Add to the executable environment if you don't want to use `uv run main.py`
          ```
          #!/usr/bin/env sh
          exec uv run --directory ~/.local/src/nov main.py
          ```
        - Update by pulling the source code
    - `vim ./chromium-flags.conf` # Configure as needed
      ```
      # You can add or modify your flags here
      ```
    - Design philosophy (Make it easier for future developers to write standardized scripts)
        - Search keywords - Search all sources in parallel - Select novel - Select chapter - launch reader
        - Adding a new source only requires: `search` / `get_chapters` / `resolve_read`
          ```python
          class Provider:
              name: str
          
              def search(self, keyword: str) -> list[dict]:
                  # → [{ "id", "name", "url?", "author?", "remark?", ... }, ...]
          
              def get_chapters(self, card: dict) -> list[dict]:
                  # → [{ "id", "name", "url?", "book_id?", ... }, ...]
          
              def resolve_read(self, chap: dict, comic=None) -> list[str]:
                  # → list of paragraph strings (chapter body)
          ```
        - Providers are driven by open source communities (Ensure future maintainability)
        - These 3 providers are enough (Primary + Candidate (Alternate) + Additional)
        - `uv run test.py` # Debug providers
    - Because to solve some issues that affect user experience.
        - Ads
        - Some resources are available on different platforms
        - Seamless loading
        - Focus on novel itself (I don't want to be interrupted by irrelevant content)
- ***References***
    - ![2026-09-10T17:32:57Z.gif](https://github.com/yaoniplan/dotfiles/releases/download/assets/2026-09-10T17.32.57Z.gif)
    - https://github.com/juliusnguyen/noveltrans/blob/main/src/noveltrans/scrapers/bqg5.py # Source provider
    - https://github.com/juliusnguyen/noveltrans/blob/main/src/noveltrans/scrapers/ixdzs.py # Source provider
    - Faloo style (Bold title + paragraph + one blank line + paragraph)
    - Artificial intelligence
- ---

