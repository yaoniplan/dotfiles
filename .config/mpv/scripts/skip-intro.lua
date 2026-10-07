-- https://github.com/rui-ddc/skip-intro
-- Hold Tab = smooth scrub forward, Shift+Tab = backward, release Tab = set anchor
opts = {
    memory_file    = "~~/.intro_memory.txt",
    auto_skip      = true,
    min_skip       = 5,
    max_skip       = 300,
    osd_time       = 2,
    scrub_interval = 0.03,   -- timer interval (smaller = smoother)
    scrub_step     = 0.05,   -- seconds per step (smaller = finer)
}

memory = {}
local scrub_timer = nil

function setOptions()
    require 'mp.options'.read_options(opts)
end

function getTime()
    return mp.get_property_native('time-pos') or 0
end

function setTime(t)
    mp.set_property_number('time-pos', t)
end

-- "[vod] Series Name - Ep06" → "Series Name"
function get_series_name()
    local title = mp.get_property("media-title") or ""
    title = title:gsub("^%[[^%]]+%]%s*", ""):gsub("%s*%-.*$", "")
    title = title:match("^%s*(.-)%s*$") or title
    return title ~= "" and title or nil
end

function load_memory()
    memory = {}
    local path = mp.command_native({"expand-path", opts.memory_file})
    local f = io.open(path, "r")
    if not f then return end
    for line in f:lines() do
        local t, name = line:match("^([%d%.]+)%s+(.+)$")
        if t and name then
            memory[name] = tonumber(t)
        end
    end
    f:close()
end

-- newest entry written at the top
function save_memory(first_key, first_val)
    local path = mp.command_native({"expand-path", opts.memory_file})
    local f = io.open(path, "w")
    if not f then return end
    if first_key then
        f:write(string.format("%.6f %s\n", first_val, first_key))
    end
    for k, v in pairs(memory) do
        if k ~= first_key and type(v) == "number" then
            f:write(string.format("%.6f %s\n", v, k))
        end
    end
    f:close()
end

function set_anchor()
    local series = get_series_name()
    if not series then
        mp.osd_message("Cannot detect series name", opts.osd_time)
        return
    end
    local t = getTime()
    if t < opts.min_skip or t > opts.max_skip then
        mp.osd_message(string.format("%.1fs out of range (%d–%d)", t, opts.min_skip, opts.max_skip), opts.osd_time)
        return
    end
    memory[series] = t
    save_memory(series, t)
    mp.osd_message(string.format("Anchor set: \"%s\" → %.1fs", series, t), opts.osd_time)
end

local function stop_scrub()
    if scrub_timer then
        scrub_timer:kill()
        scrub_timer = nil
    end
end

local function start_scrub(forward)
    stop_scrub()
    local step = forward and opts.scrub_step or -opts.scrub_step
    mp.commandv("seek", step, "relative", "exact")
    scrub_timer = mp.add_periodic_timer(opts.scrub_interval, function()
        mp.commandv("seek", step, "relative", "exact")
    end)
end

function on_tab(state)
    if state.event == "down" then
        start_scrub(true)
    elseif state.event == "up" then
        stop_scrub()
        set_anchor()
    end
end

function on_shift_tab(state)
    if state.event == "down" then
        start_scrub(false)
    elseif state.event == "up" then
        stop_scrub()
        set_anchor()
    end
end

function on_file_loaded()
    if not opts.auto_skip then return end
    local series = get_series_name()
    if not series then return end
    local t = memory[series]
    if type(t) ~= "number" or t < opts.min_skip then return end

    setTime(t)
    mp.osd_message(string.format("Skip \"%s\" → %.1fs", series, t), opts.osd_time)
end

setOptions()
load_memory()
mp.add_key_binding('Tab', 'intro-tab', on_tab, {complex = true})
mp.add_key_binding('Shift+Tab', 'intro-shift-tab', on_shift_tab, {complex = true})
mp.register_event('file-loaded', on_file_loaded)
