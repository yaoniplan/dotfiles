" Plugins will be downloaded under the specified directory.
call plug#begin(has('nvim') ? stdpath('date') . '/plugged' : '~/.vim/plugged')

" Lists of plugins
Plug 'vimwiki/vimwiki'

" List ends here. Plugins become visible to Vim after this call.
call plug#end()

" Make plugins named VimWiki work
set nocompatible
filetype plugin on
syntax on

" Use spaces for indenting
set expandtab " Replace tab characters with spaces
set tabstop=4 " Insert 4 spaces when expandtab is enabled
set shiftwidth=4 " Replace indentation with spaces

" Use Markdown syntax for VimWiki
" Replace `diary/` with `journales/`
let g:vimwiki_list = [{
    \ 'path': '~/test/',
    \ 'diary_rel_path': 'journals/',
    \ 'syntax': 'markdown',
    \ 'ext': '.md'}]
" Replace `[Vim](Vim)` with `[Vim](Vim.md)`
" Refer to https://github.com/vimwiki/vimwiki/issues/1210
let g:vimwiki_markdown_link_ext = 1
" Disable all Concealing (level: 0-3)
let g:vimwiki_conceallevel = 3
" Disable URL shortening
let g:vimwiki_url_maxsave = 0
" Replace spaces in the file names with underscores
let g:vimwiki_links_space_char = '_'

set directory^=$HOME/.vim/tmp// " Move all swap files to `~/.vim/tmp/`
