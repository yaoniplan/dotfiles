-- https://github.com/CogentRedTester/mpv-file-browser/issues/82#issuecomment-1342220863
-- https://github.com/CogentRedTester/mpv-file-browser/blob/master/docs/addons.md
local fb = require 'file-browser'

local parser = {
    api_version = '1.9.0',
    priority = 105,
    name = 'random'
}

function parser:can_parse(directory)
    -- Only modify local filesystem directories.
    return fb.get_protocol(directory) == nil
end

function parser:parse(directory, state)
    local list, opts = self:defer(directory, state)
    if not list then return list, opts end

    -- Keep directories together and shuffle only files.
    local files = {}

    for _, item in ipairs(list) do
        if item.type == 'file' then
            files[#files + 1] = item
        end
    end

    -- Fisher-Yates shuffle.
    for i = #files, 2, -1 do
        local j = math.random(i)
        files[i], files[j] = files[j], files[i]
    end

    -- Replace the file positions with the shuffled files.
    local file_index = 1

    for i, item in ipairs(list) do
        if item.type == 'file' then
            list[i] = files[file_index]
            file_index = file_index + 1
        end
    end

    -- Prevent file-browser from applying its normal sorting.
    opts.sorted = true

    return list, opts
end

parser.keybinds = {
    {
        key = 's',
        name = 'shuffle',
        command = function()
            fb.rescan()
        end
    }
}

return parser
