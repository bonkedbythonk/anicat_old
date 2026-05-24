local mp = mp
local assdraw = require 'mp.assdraw'
local msg = require 'mp.msg'
local options = require 'mp.options'

local opts = {
  accent = '0A84FF',
  font = 'sans-serif',
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
  shaders_on = false,
  file_loaded = false,
  is_hovered = false,
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
  local c = 0.5522847 * r
  ass:draw_start()
  ass:move_to(x1 + r, y1)
  ass:line_to(x2 - r, y1)
  ass:bezier_to(x2 - r + c, y1, x2, y1 + r - c, x2, y1 + r)
  ass:line_to(x2, y2 - r)
  ass:bezier_to(x2, y2 - r + c, x2 - r + c, y2, x2 - r, y2)
  ass:line_to(x1 + r, y2)
  ass:bezier_to(x1 + r - c, y2, x1, y2 - r + c, x1, y2 - r)
  ass:line_to(x1, y1 + r)
  ass:bezier_to(x1, y1 + r - c, x1 + r - c, y1, x1 + r, y1)
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
  if not state.file_loaded or not state.skip_button then
    if state.is_hovered then
      state.is_hovered = false
      return true
    end
    return false
  end

  local mouse = mp.get_property_native('mouse-pos')
  if not mouse then
    if state.is_hovered then
      state.is_hovered = false
      return true
    end
    return false
  end

  local x = mouse.x or 0
  local y = mouse.y or 0
  local hovered = in_rect(x, y, state.skip_button.x1, state.skip_button.y1, state.skip_button.x2, state.skip_button.y2)
  if hovered ~= state.is_hovered then
    state.is_hovered = hovered
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

local function draw_button(ass, x1, y1, x2, y2, bg_color, border_color, label, font_size, text_color, fill_alpha, border_alpha)
  -- Button background
  ass:new_event()
  ass:append(string.format([[{\an7\1c%s\3c%s\1a&H%s&\3a&H%s&\bord1.5\shad0}]], 
    hex_to_ass_color(bg_color), 
    hex_to_ass_color(border_color),
    fill_alpha,
    border_alpha
  ))
  draw_rounded_rect(ass, x1, y1, x2, y2, 18)

  -- Button text
  ass:new_event()
  local text_x = math.floor((x1 + x2) / 2)
  local text_y = math.floor((y1 + y2) / 2) - 1
  ass:append(string.format([[{\an5\fn%s\fs%d\b1\1c%s\1a&H00&\bord0\shad0\pos(%d,%d)}]], 
    opts.font, font_size, hex_to_ass_color(text_color), text_x, text_y))
  ass:append(escape_ass(label))
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
  state.hq_button = nil

  if w <= 0 or h <= 0 then
    return
  end

  local ass = assdraw.ass_new()
  local pad = 20
  local btn_h = 36

  -- ======== SKIP BUTTON (bottom-right, only when active skip) ========
  if state.active_skip then
    local skip_label = 'Skip Intro'
    if state.active_skip.type == 'ed' then
      skip_label = 'Skip Outro'
    elseif state.active_skip.type == 'op' then
      skip_label = 'Skip Intro'
    else
      skip_label = 'Skip Segment'
    end

    local text_len = #skip_label
    local btn_width = math.max(130, text_len * 9 + 48)
    local s_x1 = w - btn_width - pad
    local s_y1 = h - btn_h - pad - 60
    local s_x2 = w - pad
    local s_y2 = s_y1 + btn_h
    state.skip_button = { x1 = s_x1, y1 = s_y1, x2 = s_x2, y2 = s_y2 }

    -- Re-evaluate hover with the final skip button dimensions
    check_hover()

    local bg_color, border_color, text_color
    local fill_alpha, border_alpha
    if state.is_hovered then
      bg_color = opts.accent
      border_color = opts.accent
      text_color = 'ffffff'
      fill_alpha = '00'
      border_alpha = '00'
    else
      bg_color = '0F172A'
      border_color = '334155'
      text_color = 'E2E8F0'
      fill_alpha = '33'   -- 80% opacity
      border_alpha = '40' -- 75% opacity
    end

    draw_button(ass, s_x1, s_y1, s_x2, s_y2, bg_color, border_color, skip_label, 14, text_color, fill_alpha, border_alpha)
  end

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

  -- Check skip button
  if state.skip_button and in_rect(x, y, state.skip_button.x1, state.skip_button.y1, state.skip_button.x2, state.skip_button.y2) then
    skip_current_segment()
  end
end

local function register_script_messages()
  if not mp.register_script_message then
    return
  end
  mp.register_script_message('anicat-skip-intro', skip_current_segment)
  mp.register_script_message('anicat-toggle-upscale', enable_shaders)
  mp.register_script_message('anicat-disable-upscale', disable_shaders)
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
