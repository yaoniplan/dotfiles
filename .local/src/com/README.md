- #### Use "com"
    - `com`
- ***Notes***
    - `uv sync` # Install dependencies
        - `vim ~/.local/bin/com` # Add to the executable environment if you don't want to use `uv run main.py`
          ```
          #!/usr/bin/env sh
          exec uv run --directory ~/.local/src/com main.py
          ```
        - Update by pulling the source code
    - `vim ./chromium-flags.conf` # Configure as needed
      ```
      # You can add or modify your flags here
      ```
    - Design philosophy (Make it easier for future developers to write standardized scripts)
        - Search keywords - Search all sources simultaneously - Select comic via fzf - Select chapter via fzf - Automatically launch reader
        - When adding a new source, just write: search / get_chapters / resolve_read (Optional: fetch_image if the image is encrypted)
        - Providers are driven by open source communities (Ensure future maintainability)
        - These 3 providers are enough (Primary + Candidate (Alternate) + Additional)
        - `uv run test.py` # Debug providers
    - Because to solve some issues that affect user experience.
        - Ads
        - Some resources are available on different platforms
        - Seamless loading
        - Focus on comic itself (I don't want to be interrupted by irrelevant content)
- ***References***
    - https://github.com/keiyoushi/extensions-source/blob/16df97717c304c3f1e309c81acdceaeab5b51314/src/zh/guazimanhua/src/eu/kanade/tachiyomi/extension/zh/guazimanhua/Guazimanhua.kt # Source provider
    - https://github.com/keiyoushi/extensions-source/blob/16df97717c304c3f1e309c81acdceaeab5b51314/src/zh/manwa/src/eu/kanade/tachiyomi/extension/zh/manwa/Manwa.kt # Source provider
    - https://github.com/skepsun/kototoro-parsers/blob/94e3ee1beba2c0fc77c1ec19899e3fbf0c6e4c53/src/main/kotlin/org/skepsun/kototoro/parsers/site/zh/CopyMangaParser.kt # Source provider
    - Tachimanga style (Chapter label block: one blank line + bold text with default font size + one blank line)
    - Artificial intelligence
- ---
