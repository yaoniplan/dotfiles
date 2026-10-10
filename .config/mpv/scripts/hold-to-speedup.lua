-- https://github.com/iiiGerardoiii/mpv-hold-to-speedup/blob/main/hold-to-speedup.lua
local speed_increment = 1.0
local hold_threshold = 0.4          -- 可以稍微调短一点
local debounce_ms = 0.08            -- 防抖时间（秒），建议 0.06~0.12

local is_speeding = false
local timer = nil
local debounce_timer = nil
local pre_hold_speed = 1.0
local space_down = false            -- 当前是否认为按着空格

local function format_speed(speed)
    if math.abs(speed - math.floor(speed)) < 0.000001 then
        return string.format("%dx", speed)
    else
        return string.format("%.1fx", speed)
    end
end

local function speed_on()
    if is_speeding then return end
    is_speeding = true
    pre_hold_speed = mp.get_property_number("speed")
    local new_speed = pre_hold_speed + speed_increment
    mp.set_property("speed", new_speed)
    mp.set_osd_ass(0, 0, format_speed(new_speed) .. " ▶▶")
end

local function speed_off()
    if not is_speeding then return end
    mp.set_property("speed", pre_hold_speed)
    mp.set_osd_ass(0, 0, "")
    is_speeding = false
    mp.osd_message("", 0)
    mp.osd_message("▶", 1)
end

local function kill_timers()
    if timer then timer:kill(); timer = nil end
    if debounce_timer then debounce_timer:kill(); debounce_timer = nil end
end

-- 真正的松开处理
local function real_space_up()
    space_down = false
    kill_timers()
    if is_speeding then
        speed_off()
    else
        mp.command("cycle pause")
    end
end

local function handle_space(event)
    if event.event == "down" then
        -- 如果已经在加速中，忽略这次 down（可能是抖动）
        if is_speeding then
            -- 取消可能正在等待的“真正松开”
            if debounce_timer then
                debounce_timer:kill()
                debounce_timer = nil
            end
            return
        end

        space_down = true
        kill_timers()
        timer = mp.add_timeout(hold_threshold, speed_on)

    elseif event.event == "up" then
        if not space_down then return end

        -- 启动防抖：只有持续松开超过 debounce_ms 才真正处理
        if debounce_timer then debounce_timer:kill() end
        debounce_timer = mp.add_timeout(debounce_ms, real_space_up)
    end
end

-- 左键逻辑保持原样（通常鼠标不容易抖）
local function handle_click(event)
    if event.event == "down" then
        timer = mp.add_timeout(hold_threshold, speed_on)
    elseif event.event == "up" then
        if timer then timer:kill(); timer = nil end
        if is_speeding then speed_off() end
    end
end

mp.add_forced_key_binding("space", "speed_space", handle_space, {complex = true})
mp.add_forced_key_binding("MBTN_LEFT", "speed_click", handle_click, {complex = true})
