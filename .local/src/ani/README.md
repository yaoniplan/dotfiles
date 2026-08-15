- #### Use "ani"
    - `ani`
- ***Notes***
    - Design philosophy (Make it easier for future developers to write standardized scripts)
        - The script (providers/xxx.py) is modified based on the community version to ensure future maintainability. (Because the encryption of some websites is not friendly to beginners)
        - Search keywords - Search all sources simultaneously - Select video via fzf - Select episode via fzf - Automatically launch player
        - When adding a new source, just write: search / get_tracks / resolve_play
        - the extracted fields should not display the actual URL to improve the user interface when select video
        - All source fields should be aligned to improve the user interface when select video
        - Do not display the actual URL of the video during the episode selection stage to improve the user experience
        - These 3 providers are enough (Primary + Candidate (Alternate) + Additional)
    - Because to solve some issues that affect user experience.
        - Ads
        - Some resources are available on different platforms
        - Seamless loading
        - Focus on animation itself (I don't want to be interrupted by irrelevant content)
    - `vim ./mpv.conf` # Configure as needed
      ```
      # You can add or modify your parameters here.
      ```
    - Decoupling
        - [X] test.py
        - [X] player.py
        - selector.py
    - Minimize
        - Maintain a barely usable amount of code
    - Customize
        - Based on this version, you can add small features by requesting AI
        - AI + history
        - AI + source provider
        - AI + automatically skip the intro and outro
        - AI + preload the next episode
    - `uv sync` # Install dependencies
        - `vim ~/.local/bin/ani` # Add to the executable environment if you don't wnat to use `uv run main.py`
          ```
          #!/usr/bin/env sh
          exec uv run --directory ~/.local/src/ani main.py "$@"
          ```
        - Update by pulling the source code
- ***References***
    - ![2026-05-08T16:58:42Z.gif](https://github.com/user-attachments/assets/546fd52e-9dc7-4ec0-8ea5-f9f66ae9cd19)
    - https://github.com/Yswag/xptv-extensions/blob/main/js/iyftv.js # Source provider
    - https://github.com/fangkuia/XPTV/blob/main/js/duboku.js # Source provider
    - https://github.com/fangkuia/XPTV/blob/main/js/ole.js # Source provider
    - https://github.com/yaoniplan/dotfiles/blob/7c578f857055fc6ac834ba7dbb0934988c390ae3/.local/src/ani/main.py # The final version of the single main.py before decoupling
    - https://github.com/pystardust/ani-cli/blob/master/ani-cli # `/--force-media-title`
    - Artificial intelligence
- ---
