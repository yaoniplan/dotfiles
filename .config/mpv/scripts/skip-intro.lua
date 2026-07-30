-- https://github.com/rui-ddc/skip-intro
MAX_SPEED = 100
NORMAL_SPEED = 1
ONE_SECOND = 1
skip = false
startTime = 0
memory = {}

-- Max noise (dB) and min silence duration (s) to trigger
opts = {
    quietness = -30,
    duration = 0.5,
    memory_file = "~~/intro_memory.json",  -- 记忆文件
    auto_skip = true,                      -- 有记忆时自动跳转
    min_skip = 20,                         -- 最小有效秒数
    max_skip = 180,                        -- 最大有效秒数
    osd_time = 2,
}

function setOptions()
    local options = require 'mp.options'
    options.read_options(opts)
end

function setTime(time)
    mp.set_property_number('time-pos', time)
end

function getTime()
    return mp.get_property_native('time-pos')
end

function setSpeed(speed)
    mp.set_property('speed', speed)
end

function setPause(state)
    mp.set_property_bool('pause', state)
end

function setMute(state)
    mp.set_property_bool('mute', state)
end

-- 从 media-title 提取系列名，例如 "[gua] 无上神帝 / 第10集" → "无上神帝"
function get_series_name()
    local title = mp.get_property("media-title") or ""
    title = title:gsub("^%[[^%]]+%]%s*", "")          -- 去掉 [gua]
    local series = title:match("^(.-)%s*/%s*第") or title:match("^(.-)%s*第%d") or title
    series = series:match("^%s*(.-)%s*$")              -- trim
    if series == "" then return nil end
    return series
end

function load_memory()
    local utils = require 'mp.utils'
    local path = mp.command_native({"expand-path", opts.memory_file})
    local f = io.open(path, "r")
    if not f then
        memory = {}
        return
    end
    local content = f:read("*a")
    f:close()
    local data = utils.parse_json(content)
    if type(data) == "table" then
        memory = data
    else
        memory = {}
    end
end

function save_memory()
    local utils = require 'mp.utils'
    local path = mp.command_native({"expand-path", opts.memory_file})
    local f = io.open(path, "w")
    if f then
        f:write(utils.format_json(memory))
        f:close()
    end
end

function initAudioFilter()
    local af_table = mp.get_property_native('af')
    af_table[#af_table + 1] = {
        enabled = false,
        label   = 'silencedetect',
        name    = 'lavfi',
        params  = { graph = 'silencedetect=noise=' .. opts.quietness .. 'dB:d=' .. opts.duration }
    }
    mp.set_property_native('af', af_table)
end

function initVideoFilter()
    local vf_table = mp.get_property_native('vf')
    vf_table[#vf_table + 1] = {
        enabled = false,
        label   = 'blackout',
        name    = 'lavfi',
        params  = { graph = '' }
    }
    mp.set_property_native('vf', vf_table)
end

function setAudioFilter(state)
    local af_table = mp.get_property_native('af')
    if #af_table > 0 then
        for i = #af_table, 1, -1 do
            if af_table[i].label == 'silencedetect' then
                af_table[i].enabled = state
                mp.set_property_native('af', af_table)
                break
            end
        end
    end
end

function dim(state)
    local dim = { width = 0, height = 0 }
    if state == true then
        dim.width = mp.get_property_native('width')
        dim.height = mp.get_property_native('height')
    end
    return dim.width .. 'x' .. dim.height
end

function setVideoFilter(state)
    local vf_table = mp.get_property_native('vf')
    if #vf_table > 0 then
        for i = #vf_table, 1, -1 do
            if vf_table[i].label == 'blackout' then
                vf_table[i].enabled = state
                vf_table[i].params  = { graph = 'nullsink,color=c=black:s=' .. dim(state) }
                mp.set_property_native('vf', vf_table)
                break
            end
        end
    end
end

function silenceTrigger(name, value)
    if value == '{}' or value == nil then
        return
    end

    local skipTime = tonumber(string.match(value, '%d+%.?%d+'))
    local currTime = getTime()

    if skipTime == nil or skipTime < currTime + ONE_SECOND then
        return
    end

    stopSkip()
    setTime(skipTime)
    skip = false

    -- 记忆功能
    local series = get_series_name()
    if series and skipTime >= opts.min_skip and skipTime <= opts.max_skip then
        memory[series] = skipTime
        save_memory()
        mp.osd_message(string.format("已记住「%s」片头结束于 %.1f 秒", series, skipTime), opts.osd_time)
    else
        mp.osd_message(string.format("跳过到 %.1f 秒", skipTime), opts.osd_time)
    end
end

function setAudioTrigger(state)
    if state == true then
        mp.observe_property('af-metadata/silencedetect', 'string', silenceTrigger)
    else
        mp.unobserve_property(silenceTrigger)
    end
end

function startSkip()
    startTime = getTime()
    -- This audio filter detects moments of silence
    setAudioFilter(true)
    -- This video filter makes fast-forward faster
    setVideoFilter(true)
    setAudioTrigger(true)
    setPause(false)
    setMute(true)
    setSpeed(MAX_SPEED)
end

function stopSkip()
    setAudioFilter(false)
    setVideoFilter(false)
    setAudioTrigger(false)
    setMute(false)
    setSpeed(NORMAL_SPEED)
end

function keypress()
    skip = not skip
    if skip then
        startSkip()
        mp.osd_message("静音跳过中... (再按 Tab 取消)", opts.osd_time)
    else
        stopSkip()
        setTime(startTime)
        mp.osd_message("已取消跳过", opts.osd_time)
    end
end

-- 文件加载时自动跳转
function on_file_loaded()
    if not opts.auto_skip then return end
    local series = get_series_name()
    if not series then return end

    local t = memory[series]
    if t and type(t) == "number" and t >= opts.min_skip then
        mp.add_timeout(0.4, function()
            local cur = getTime() or 0
            if cur < t - 2 then
                setTime(t)
                mp.osd_message(string.format("自动跳过「%s」片头 → %.1f 秒", series, t), opts.osd_time)
            end
        end)
    end
end

-- 清除当前系列记忆
function clear_current()
    local series = get_series_name()
    if series and memory[series] then
        memory[series] = nil
        save_memory()
        mp.osd_message("已清除「" .. series .. "」的片头记忆", opts.osd_time)
    else
        mp.osd_message("当前没有可清除的记忆", opts.osd_time)
    end
end

setOptions()
load_memory()
initAudioFilter()
initVideoFilter()

mp.add_key_binding('Tab', 'skip-key', keypress)
mp.add_key_binding('Ctrl+Tab', 'clear-intro-memory', clear_current)
mp.register_event('file-loaded', on_file_loaded)
