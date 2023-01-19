" Plugins will be downloaded under the specified directory.
call plug#begin(has('nvim') ? stdpath('date') . '/plugged' : '~/.vim/plugged')

" Lists of plugins
Plug 'vimwiki/vimwiki'

" Make plugins named VimWiki work
set nocompatible
filetype plugin on
syntax on

" Use spaces for indenting
set expandtab " Replace tab characters with spaces
set tabstop=4 " Insert 4 spaces when expandtab is enabled
set shiftwidth=4 " Replace indentation with spaces

" Use Markdown syntax for VimWiki
let g:vimwiki_list = [{'path': '~/vimwiki/',
	                      \ 'syntax': 'markdown', 'ext': '.md'}]

set noswapfile " Disable swap files for VimWiki

" List ends here. Plugins become visible to Vim after this call.
call plug#end()
