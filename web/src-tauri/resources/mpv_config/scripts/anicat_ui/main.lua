local mp = mp
local assdraw = require 'mp.assdraw'
local msg = require 'mp.msg'
local options = require 'mp.options'

local opts = {
  accent = '0A84FF',
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

-- Draw a rounded pill button and return the label width
local function draw_button(ass, x1, y1, x2, y2, bg_color, border_color, label, font_size, text_color)
  -- Button background
  ass:new_event()
  ass:append(string.format([[{\an7\1c%s\3c%s\bord1.5\shad0\alpha&H20&}]], hex_to_ass_color(bg_color), hex_to_ass_color(border_color)))
  round_rect(ass, x1, y1, x2, y2)

  -- Button text
  ass:new_event()
  local text_x = math.floor((x1 + x2) / 2)
  local text_y = math.floor((y1 + y2) / 2) - 1
  ass:append(string.format([[{\an5\fn%s\fs%d\b1\1c%s\bord0\shad0\pos(%d,%d)}]], opts.font, font_size, hex_to_ass_color(text_color), text_x, text_y))
  ass:append(escape_ass(label))
end

local function render()
  if not state.file_loaded then
    state.overlay:remove()
    return
  end

  refresh_state()
  refresh_shaders_state()
  state.skip_button = nil
  state.hq_button = nil

  local w = state.width
  local h = state.height
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

    draw_button(ass, s_x1, s_y1, s_x2, s_y2, '050505', opts.accent, skip_label, 14, 'ffffff')
  end

  state.overlay.data = ass.text
  state.overlay.res_x = w
  state.overlay.res_y = h
  state.overlay.hidden = false
  state.overlay:update()
end

local function on_left_click()
  refresh_state()
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

mp.observe_property('time-pos', 'number', render)
mp.observe_property('duration', 'number', render)
mp.observe_property('mouse-pos', 'native', render)
mp.observe_property('glsl-shaders', 'string', function()
  refresh_shaders_state()
  render()
end)

mp.register_event('file-loaded', function()
  state.file_loaded = true
  state.skips = parse_skip_times(opts.skip_times)
  refresh_shaders_state()
  render()
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
