local mp = mp
local assdraw = require 'mp.assdraw'
local msg = require 'mp.msg'
local options = require 'mp.options'

local opts = {
  accent = '00f2fe',
  font = 'Outfit',
  skip_times = '',
}

options.read_options(opts, 'anicat_ui')

local function hex_to_ass_color(hex)
  if not hex or hex == '' then
    return '&H00FFFFFF&'
  end
  hex = hex:gsub('#', '')
  if #hex ~= 6 then
    return '&H00FFFFFF&'
  end
  local r = hex:sub(1, 2)
  local g = hex:sub(3, 4)
  local b = hex:sub(5, 6)
  return string.format('&H00%s%s%s&', b, g, r)
end

local accent_ass = hex_to_ass_color(opts.accent)

local state = {
  overlay = mp.create_osd_overlay('ass-events'),
  width = 1280,
  height = 720,
  position = 0,
  duration = 0,
  skips = {},
  active_skip = nil,
  button = nil,
}

local function escape_ass(text)
  if text == nil then
    return ''
  end
  local ok, escaped = pcall(mp.command_native, { 'escape-ass', tostring(text) })
  if ok and type(escaped) == 'string' then
    return escaped
  end
  return tostring(text)
    :gsub('\\', '\\\\')
    :gsub('{', '\\{')
    :gsub('}', '\\}')
end

local function parse_skip_times(raw)
  local parsed = {}
  if not raw or raw == '' then
    return parsed
  end
  for part in string.gmatch(raw, '([^;]+)') do
    local skip_type, start_s, end_s = part:match('([^,]+),([^,]+),([^,]+)')
    if skip_type and start_s and end_s then
      parsed[#parsed + 1] = {
        type = skip_type,
        start = tonumber(start_s) or 0,
        endt = tonumber(end_s) or 0,
      }
    end
  end
  return parsed
end

local function get_active_skip(position)
  for _, entry in ipairs(state.skips) do
    if position >= entry.start and position <= entry.endt then
      return entry
    end
  end
  return nil
end

state.skips = parse_skip_times(opts.skip_times)

local function refresh_state()
  local w, h = mp.get_osd_size()
  state.width = w or 1280
  state.height = h or 720
  state.position = mp.get_property_number('time-pos') or 0
  state.duration = mp.get_property_number('duration') or 0
  state.active_skip = get_active_skip(state.position)
end

local function round_rect(ass, x1, y1, x2, y2)
  ass:draw_start()
  ass:rect_cw(x1, y1, x2, y2)
  ass:draw_stop()
end

local function in_rect(x, y, x1, y1, x2, y2)
  return x >= x1 and x <= x2 and y >= y1 and y <= y2
end

local function jump_to(time_pos)
  local duration = state.duration or 0
  if duration <= 0 then
    return
  end
  local clamped = math.max(0, math.min(duration, time_pos))
  mp.set_property_number('time-pos', clamped)
end

local function skip_current_segment()
  local skip = state.active_skip
  if skip and skip.endt and skip.endt > state.position then
    jump_to(skip.endt)
    mp.osd_message('Skipped segment', 1.5)
  end
end

local function render()
  refresh_state()
  state.button = nil

  if not state.active_skip then
    state.overlay:remove()
    return
  end

  local w = state.width
  local h = state.height
  if w <= 0 or h <= 0 then
    return
  end

  local ass = assdraw.ass_new()
  
  local skip_label = 'Skip Intro'
  if state.active_skip.type == 'ed' then
    skip_label = 'Skip Outro'
  elseif state.active_skip.type == 'op' then
    skip_label = 'Skip Intro'
  else
    skip_label = 'Skip Segment'
  end

  local text_len = #skip_label
  local btn_width = math.max(120, text_len * 9 + 40)
  
  -- Netflix-style bottom-right positioning, nicely floating clear of ModernZ OSC
  local x1 = w - btn_width - 30
  local y1 = h - 130
  local x2 = w - 30
  local y2 = h - 85

  state.button = { x1 = x1, y1 = y1, x2 = x2, y2 = y2 }

  -- Glassmorphic panel styling
  ass:new_event()
  ass:append(string.format([[{\an7\1c%s\3c%s\bord2\shad0\alpha&H30&}]], hex_to_ass_color('0a0b10'), accent_ass))
  round_rect(ass, x1, y1, x2, y2)

  -- Centered text styling
  ass:new_event()
  local text_x = math.floor((x1 + x2) / 2)
  local text_y = math.floor((y1 + y2) / 2) - 1
  ass:append(string.format([[{\an5\fn%s\fs15\b1\1c%s\bord0\shad0\pos(%d,%d)}]], opts.font, '&H00FFFFFF&', text_x, text_y))
  ass:append(escape_ass(skip_label))

  state.overlay.data = ass.text
  state.overlay.res_x = w
  state.overlay.res_y = h
  state.overlay.hidden = false
  state.overlay:update()
end

local function on_left_click()
  refresh_state()
  local mouse = mp.get_property_native('mouse-pos')
  if not mouse or not state.button then
    return
  end
  local x = mouse.x or 0
  local y = mouse.y or 0
  if in_rect(x, y, state.button.x1, state.button.y1, state.button.x2, state.button.y2) then
    skip_current_segment()
  end
end

local function register_script_messages()
  if not mp.register_script_message then
    return
  end
  mp.register_script_message('anicat-skip-intro', skip_current_segment)
end

mp.observe_property('time-pos', 'number', render)
mp.observe_property('duration', 'number', render)
mp.observe_property('mouse-pos', 'native', render)
mp.register_event('file-loaded', function()
  -- Try to extract from observed script-opts
  local opts_str = mp.get_property('options/script-opts') or ''
  local match_val = opts_str:match('anicat_ui%-skip_times=([^,]+)') or opts.skip_times
  state.skips = parse_skip_times(match_val)
  render()
end)

register_script_messages()

local ok, err = pcall(function()
  mp.add_forced_key_binding('MBTN_LEFT', 'anicat-skip-click', on_left_click)
end)
if not ok then
  msg.warn('Could not bind MBTN_LEFT: ' .. tostring(err))
end

msg.info('AniCat skip helper overlay loaded')
