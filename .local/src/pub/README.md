- #### Use ["pub"](https://github.com/yaoniplan/dotfiles/tree/development/.local/src/pub)
    - `pub`
- ***Notes***
    - `uv sync` # Install dependencies
        - `vim ~/.local/bin/pub` # Add to the executable environment if you don't want to use `uv run main.py`
          ```
          #!/usr/bin/env sh
          exec uv run --directory ~/.local/src/pub main.py
          ```
        - Update by pulling the source code
    - `vim ./.env` # Configure as needed (You can refer to `.env.example`)
      ```
      # You can add or modify your accounts here
      ```
    - `vim ./chromium-flags.conf` # Configure as needed
      ```
      # You can add or modify your flags here
      ```
    - Design philosophy (Make it easier for future developers to write standardized scripts)
        - Search keywords - Search all sources in parallel - Select a publication - Select a section - launch reader
        - Adding a new source only requires: `search` / `get_sections` / `resolve_read`
        - Providers are driven by open source communities (Ensure future maintainability)
        - These 3 providers are enough (Primary + Candidate (Alternate) + Additional)
        - `uv run test.py` # Debug providers
    - Because to solve some issues that affect user experience.
        - Ads
        - Some resources are available on different platforms
        - Seamless loading
        - Focus on publication itself (I don't want to be interrupted by irrelevant content)
- ***References***
    - ![2026-10-05T16:47:29Z.gif](https://github.com/yaoniplan/dotfiles/releases/download/assets/2026-10-05T16.47.29Z.gif)
    - https://github.com/heartleo/zlib # Source provider
    - https://github.com/SvnFrs/shadow-bridge/blob/cbb3ee114900718863861ac8bbe9b00481606dcc/src/providers/libgen.ts # Source provider
    - https://github.com/codep-alt/bookdrop/blob/master/bookdrop.koplugin/bookdrop_opds_provider.lua # Source provider
    - Artificial intelligence
- ---

