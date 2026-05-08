local utils = require("mp.utils")

local last_title = nil

local function get_title()
    local title = mp.get_property("media-title", "")
    local filename = mp.get_property("filename", "")

    if title ~= nil and title ~= "" then
        return title
    end

    if filename ~= nil and filename ~= "" then
        return filename
    end

    return nil
end

local function notify(title)
    if not title then
        return
    end

    utils.subprocess_detached({
        args = {
            "notify-send",
            title
        }
    })
end

mp.register_event("file-loaded", function()
    last_title = get_title()
    notify(last_title)
end)

mp.register_event("shutdown", function()
    notify(last_title)
end)
