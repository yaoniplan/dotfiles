local utils = require("mp.utils")

local last_title = nil
local last_position = 0

local function get_title()
    local title = mp.get_property("media-title", "")
    local filename = mp.get_property("filename", "")
    if title ~= nil and title ~= "" then return title end
    if filename ~= nil and filename ~= "" then return filename end
    return nil
end

local function format_time(seconds)
    if not seconds or seconds < 0 then return "00:00:00" end
    local h = math.floor(seconds / 3600)
    local m = math.floor((seconds % 3600) / 60)
    local s = math.floor(seconds % 60)
    return string.format("%02d:%02d:%02d", h, m, s)
end

local function notify(msg)
    if msg then
        utils.subprocess_detached({ args = { "notify-send", msg } })
    end
end

-- update position every second
mp.add_periodic_timer(1, function()
    local pos = mp.get_property_number("time-pos")
    if pos then last_position = pos end
end)

mp.register_event("file-loaded", function()
    last_title = get_title()
    last_position = 0
    notify(last_title)
end)

mp.register_event("end-file", function()
    if last_title then
        notify(last_title)                        -- 1st notification: title
        notify(format_time(last_position))        -- 2nd notification: 00:12:34
    end
end)
