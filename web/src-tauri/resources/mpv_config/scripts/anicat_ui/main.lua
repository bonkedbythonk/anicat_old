local mp = mp
local assdraw = require 'mp.assdraw'
local msg = require 'mp.msg'
local options = require 'mp.options'

local opts = {
  accent = '0A84FF',
  font = 'sans-serif',
  skip_times = '',
  auto_next = 'no',
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
local green_ass = hex_to_ass_color('22c55e')
local amber_ass = hex_to_ass_color('f59e0b')

local state = {
  overlay = mp.create_osd_overlay('ass-events'),
  width = 1280,
  height = 720,
  position = 0,
  duration = 0,
  skips = {},
  active_skip = nil,
  skip_button = nil,
  hq_button = nil,
  auto_button = nil,
  next_button = nil,
  prev_button = nil,
  shaders_on = false,
  file_loaded = false,
  hovered_btn = nil,
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

local function refresh_shaders_state()
  local current_shaders = mp.get_property('glsl-shaders') or ''
  state.shaders_on = (current_shaders ~= '')
end

local function refresh_state()
  local w, h = mp.get_osd_size()
  state.width = w or 1280
  state.height = h or 720
  state.position = mp.get_property_number('time-pos') or 0
  state.duration = mp.get_property_number('duration') or 0
  state.active_skip = get_active_skip(state.position)
end

local function draw_rounded_rect(ass, x1, y1, x2, y2, r)
  -- Plain rectangle — bezier_to is not available in this MPV build
  ass:draw_start()
  ass:move_to(x1, y1)
  ass:line_to(x2, y1)
  ass:line_to(x2, y2)
  ass:line_to(x1, y2)
  ass:draw_stop()
end

local function in_rect(x, y, x1, y1, x2, y2)
  return x >= x1 and x <= x2 and y >= y1 and y <= y2
end

local function check_active_skip()
  local pos = mp.get_property_number('time-pos') or 0
  state.position = pos
  local active = get_active_skip(pos)
  if active ~= state.active_skip then
    state.active_skip = active
    return true
  end
  return false
end

local function check_hover()
  if not state.file_loaded then
    if state.hovered_btn ~= nil then
      state.hovered_btn = nil
      return true
    end
    return false
  end

  local mouse = mp.get_property_native('mouse-pos')
  if not mouse then
    if state.hovered_btn ~= nil then
      state.hovered_btn = nil
      return true
    end
    return false
  end

  local x = mouse.x or 0
  local y = mouse.y or 0

  local active_hover = nil
  if state.skip_bar_button and in_rect(x, y, state.skip_bar_button.x1, state.skip_bar_button.y1, state.skip_bar_button.x2, state.skip_bar_button.y2) then
    active_hover = 'skipbar'
  elseif state.hq_button and in_rect(x, y, state.hq_button.x1, state.hq_button.y1, state.hq_button.x2, state.hq_button.y2) then
    active_hover = 'hq'
  elseif state.auto_button and in_rect(x, y, state.auto_button.x1, state.auto_button.y1, state.auto_button.x2, state.auto_button.y2) then
    active_hover = 'auto'
  elseif state.next_button and in_rect(x, y, state.next_button.x1, state.next_button.y1, state.next_button.x2, state.next_button.y2) then
    active_hover = 'next'
  elseif state.prev_button and in_rect(x, y, state.prev_button.x1, state.prev_button.y1, state.prev_button.x2, state.prev_button.y2) then
    active_hover = 'prev'
  end

  if active_hover ~= state.hovered_btn then
    state.hovered_btn = active_hover
    return true
  end
  return false
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

local function enable_shaders()
  local shader_paths = {
    "~~/shaders/Anime4K_Clamp_Highlights.glsl",
    "~~/shaders/Anime4K_Restore_CNN_L.glsl",
    "~~/shaders/Anime4K_Upscale_CNN_x2_L.glsl",
    "~~/shaders/Anime4K_AutoDownscalePre_x2.glsl",
    "~~/shaders/Anime4K_AutoDownscalePre_x4.glsl"
  }
  local path_str = table.concat(shader_paths, ":")
  mp.commandv("change-list", "glsl-shaders", "set", path_str)
  refresh_shaders_state()
  mp.osd_message("Upscaling Enabled", 1.5)
end

local function disable_shaders()
  mp.commandv("set", "glsl-shaders", "")
  refresh_shaders_state()
  mp.osd_message("Upscaling Disabled", 1.5)
end

local function draw_button(ass, x1, y1, x2, y2, bg_color, border_color, label, font_size, text_color, fill_alpha, border_alpha, r)
  -- Button background
  ass:new_event()
  ass:append(string.format([[{\an7\1c%s\3c%s\1a&H%s&\3a&H%s&\bord1.5\shad0}]], 
    hex_to_ass_color(bg_color), 
    hex_to_ass_color(border_color),
    fill_alpha,
    border_alpha
  ))
  draw_rounded_rect(ass, x1, y1, x2, y2, r or 18)

  -- Button text
  ass:new_event()
  local text_x = math.floor((x1 + x2) / 2)
  local text_y = math.floor((y1 + y2) / 2) - 1
  ass:append(string.format([[{\an5\fn%s\fs%d\b1\1c%s\1a&H00&\bord0\shad0\pos(%d,%d)}]], 
    opts.font, font_size, hex_to_ass_color(text_color), text_x, text_y))
  ass:append(escape_ass(label))
end

local function draw_controls(ass, w, h)
  local pad = 12
  local btn_h = 38
  -- Center vertically inside ModernZ OSC bar (bar is ~70px from bottom)
  local y_center = h - 34
  local y1 = y_center - btn_h / 2
  local y2 = y1 + btn_h
  local gap = 8

  -- Button 5: Prev (Leftmost)
  local prev_width = 72
  local prev_x1 = pad + 8
  local prev_x2 = prev_x1 + prev_width
  state.prev_button = { x1 = prev_x1, y1 = y1, x2 = prev_x2, y2 = y2 }

  -- Button 4: Next
  local next_width = 72
  local next_x1 = prev_x2 + gap
  local next_x2 = next_x1 + next_width
  state.next_button = { x1 = next_x1, y1 = y1, x2 = next_x2, y2 = y2 }

  -- Button 3: Skip (always visible, pulsates when a segment is active)
  local skip_width = 80
  local skip_x1 = next_x2 + gap
  local skip_x2 = skip_x1 + skip_width
  state.skip_bar_button = { x1 = skip_x1, y1 = y1, x2 = skip_x2, y2 = y2 }

  -- Button 2: Auto
  local auto_width = 110
  local auto_x1 = skip_x2 + gap
  local auto_x2 = auto_x1 + auto_width
  state.auto_button = { x1 = auto_x1, y1 = y1, x2 = auto_x2, y2 = y2 }

  -- Button 1: HQ (Rightmost of this group)
  local hq_width = 95
  local hq_x1 = auto_x2 + gap
  local hq_x2 = hq_x1 + hq_width
  state.hq_button = { x1 = hq_x1, y1 = y1, x2 = hq_x2, y2 = y2 }

  -- Re-evaluate hover with the final control button dimensions
  check_hover()

  -- Draw Prev Button
  local prev_hovered = state.hovered_btn == 'prev'
  local prev_bg = prev_hovered and opts.accent or '050505'
  local prev_border = prev_hovered and opts.accent or '1c1c1e'
  local prev_text = prev_hovered and 'ffffff' or 'E2E8F0'
  local prev_fill_alpha = prev_hovered and '00' or '55'
  local prev_border_alpha = prev_hovered and '00' or '30'
  draw_button(ass, prev_x1, y1, prev_x2, y2, prev_bg, prev_border, 'Prev', 11, prev_text, prev_fill_alpha, prev_border_alpha, 8)

  -- Draw Next Button
  local next_hovered = state.hovered_btn == 'next'
  local next_bg = next_hovered and opts.accent or '050505'
  local next_border = next_hovered and opts.accent or '1c1c1e'
  local next_text = next_hovered and 'ffffff' or 'E2E8F0'
  local next_fill_alpha = next_hovered and '00' or '55'
  local next_border_alpha = next_hovered and '00' or '30'
  draw_button(ass, next_x1, y1, next_x2, y2, next_bg, next_border, 'Next', 11, next_text, next_fill_alpha, next_border_alpha, 8)

  -- Draw Skip Button (highlights when a skip segment is active)
  local skip_active = state.active_skip ~= nil
  local skip_hovered = state.hovered_btn == 'skipbar'
  local skip_label = 'Skip'
  if skip_active and state.active_skip.type then
    local t = state.active_skip.type
    if t == 'op' then skip_label = 'Skip OP'
    elseif t == 'ed' then skip_label = 'Skip ED'
    end
  end
  local skip_bg, skip_border, skip_text, skip_fill, skip_border_a
  if skip_active then
    -- Active skip segment: accent-bright with animated-like glow via lighter border
    skip_bg = skip_hovered and opts.accent or '050505'
    skip_border = skip_hovered and opts.accent or 'f59e0b'
    skip_text = skip_hovered and 'ffffff' or 'fbbf24'
    skip_fill = skip_hovered and '00' or '55'
    skip_border_a = skip_hovered and '00' or '40'
  else
    skip_bg = skip_hovered and opts.accent or '050505'
    skip_border = skip_hovered and opts.accent or '1c1c1e'
    skip_text = skip_hovered and 'ffffff' or '475569'
    skip_fill = skip_hovered and '00' or '55'
    skip_border_a = skip_hovered and '00' or '30'
  end
  draw_button(ass, skip_x1, y1, skip_x2, y2, skip_bg, skip_border, skip_label, 11, skip_text, skip_fill, skip_border_a, 8)

  -- Draw Auto Button
  local auto_enabled = (opts.auto_next == 'yes')
  local auto_label = auto_enabled and 'Auto: On' or 'Auto: Off'
  local auto_hovered = state.hovered_btn == 'auto'
  local auto_bg = auto_hovered and opts.accent or '050505'
  local auto_border = auto_hovered and opts.accent or '1c1c1e'
  local auto_text = auto_hovered and 'ffffff' or 'E2E8F0'
  local auto_fill_alpha = auto_hovered and '00' or '55'
  local auto_border_alpha = auto_hovered and '00' or '30'
  draw_button(ass, auto_x1, y1, auto_x2, y2, auto_bg, auto_border, auto_label, 11, auto_text, auto_fill_alpha, auto_border_alpha, 8)

  -- Draw HQ Button
  local hq_label = state.shaders_on and 'HQ: On' or 'HQ: Off'
  local hq_hovered = state.hovered_btn == 'hq'
  local hq_bg = hq_hovered and opts.accent or '050505'
  local hq_border = hq_hovered and opts.accent or '1c1c1e'
  local hq_text = hq_hovered and 'ffffff' or 'E2E8F0'
  local hq_fill_alpha = hq_hovered and '00' or '55'
  local hq_border_alpha = hq_hovered and '00' or '30'
  draw_button(ass, hq_x1, y1, hq_x2, y2, hq_bg, hq_border, hq_label, 11, hq_text, hq_fill_alpha, hq_border_alpha, 8)
end

local function render(force)
  if not state.file_loaded then
    state.overlay:remove()
    return
  end

  local w, h = mp.get_osd_size()
  w = w or 1280
  h = h or 720

  if w ~= state.width or h ~= state.height then
    state.width = w
    state.height = h
    force = true
  end

  local active_changed = check_active_skip()
  local hover_changed = check_hover()

  if not force and not active_changed and not hover_changed then
    return
  end

  state.skip_button = nil
  state.skip_bar_button = nil
  state.hq_button = nil
  state.auto_button = nil
  state.next_button = nil
  state.prev_button = nil

  if w <= 0 or h <= 0 then
    return
  end

  local ass = assdraw.ass_new()

  -- Draw controls bar (bottom-left)
  draw_controls(ass, w, h)

  state.overlay.data = ass.text
  state.overlay.res_x = w
  state.overlay.res_y = h
  state.overlay.hidden = false
  state.overlay:update()
end

local function render_forced()
  render(true)
end

local function render_unforced()
  render(false)
end

local function on_left_click()
  local mouse = mp.get_property_native('mouse-pos')
  if not mouse then
    return
  end
  local x = mouse.x or 0
  local y = mouse.y or 0

  -- Check skip bar button
  if state.skip_bar_button and in_rect(x, y, state.skip_bar_button.x1, state.skip_bar_button.y1, state.skip_bar_button.x2, state.skip_bar_button.y2) then
    skip_current_segment()
  elseif state.hq_button and in_rect(x, y, state.hq_button.x1, state.hq_button.y1, state.hq_button.x2, state.hq_button.y2) then
    if state.shaders_on then
      disable_shaders()
    else
      enable_shaders()
    end
  elseif state.auto_button and in_rect(x, y, state.auto_button.x1, state.auto_button.y1, state.auto_button.x2, state.auto_button.y2) then
    mp.commandv("script-message", "anicat-toggle-auto-next")
  elseif state.next_button and in_rect(x, y, state.next_button.x1, state.next_button.y1, state.next_button.x2, state.next_button.y2) then
    mp.commandv("script-message", "anicat-next-episode")
  elseif state.prev_button and in_rect(x, y, state.prev_button.x1, state.prev_button.y1, state.prev_button.x2, state.prev_button.y2) then
    mp.commandv("script-message", "anicat-previous-episode")
  end
end

local function set_auto_next(val)
  opts.auto_next = val
  render(true)
end

local function register_script_messages()
  if not mp.register_script_message then
    return
  end
  mp.register_script_message('anicat-skip-intro', skip_current_segment)
  mp.register_script_message('anicat-toggle-upscale', enable_shaders)
  mp.register_script_message('anicat-disable-upscale', disable_shaders)
  mp.register_script_message('anicat-set-auto-next', set_auto_next)
end

mp.observe_property('time-pos', 'number', render_unforced)
mp.observe_property('duration', 'number', render_unforced)
mp.observe_property('mouse-pos', 'native', render_unforced)
mp.observe_property('glsl-shaders', 'string', function()
  refresh_shaders_state()
  render(true)
end)

mp.register_event('file-loaded', function()
  state.file_loaded = true
  state.skips = parse_skip_times(opts.skip_times)
  refresh_shaders_state()
  render(true)
end)

mp.register_event('end-file', function()
  state.file_loaded = false
  state.overlay:remove()
  mp.osd_message('Playback finished. Press Q or close the window to return to Anicat.', 5)
end)

register_script_messages()

local ok, err = pcall(function()
  mp.add_forced_key_binding('MBTN_LEFT', 'anicat-left-click', on_left_click)
end)
if not ok then
  msg.warn('Could not register forced keybindings: ' .. tostring(err))
end

msg.info('Anicat overlay loaded: ctrl+1 = Upscaling On, ctrl+2 = Upscaling Off')
