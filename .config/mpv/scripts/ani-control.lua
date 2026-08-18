-- https://github.com/yaoniplan/dotfiles/tree/master/.local/src/ani
local resolver = "/home/yaoniplan/.local/src/ani/ani-resolve.py"

mp.add_hook("on_load", 50, function()
    local url = mp.get_property("stream-open-filename", "")
    if not url:match("^ani%-playlist://") then
        return
    end

    -- 格式：ani-playlist://source/index
    local source, index = url:match("^ani%-playlist://(.+)/(%d+)$")
    if not source or not index then
        mp.msg.warn("invalid ani-playlist URL: " .. url)
        return
    end

    local proc = mp.command_native({
        name = "subprocess",
        playback_only = false,
        capture_stdout = true,
        capture_stderr = true,
        args = {"uv", "run", "python", resolver, "goto:" .. index}
    })

    if proc.status ~= 0 then
        mp.msg.warn("resolve failed: " .. (proc.stderr or ""))
        return
    end

    -- stdout 应为两行：URL\nTitle
    local lines = {}
    for line in proc.stdout:gmatch("[^\r\n]+") do
        table.insert(lines, line)
    end
    if #lines < 2 then
        mp.msg.warn("invalid output from resolver")
        return
    end

    local real_url = lines[1]
    local title = lines[2]

    -- 关键：先设置标题选项，再更改 URL，这样新文件会立即使用标题
    mp.set_property("file-local-options/force-media-title", title)
    mp.set_property("stream-open-filename", real_url)
end)
