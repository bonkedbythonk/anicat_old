local mp = mp
local msg = require 'mp.msg'
local options = require 'mp.options'

local opts = {
  skip_times = '',
  auto_next = 'no',
}

options.read_options(opts, 'anicat_ui')

local state = {
  overlay = mp.create_osd_overlay('ass-events'),
  width = 1280,
  height = 720,
  position = 0,
  duration = 0,
  skips = {},
  active_skip = nil,
  shaders_on = false,
  file_loaded = false,
}

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

  if not force and not active_changed then
    return
  end

  if w <= 0 or h <= 0 then
    return
  end
end

local function render_forced()
  render(true)
end

local function render_unforced()
  render(false)
end

-- Mouse clicks handled by ModernZ OSC and keyboard shortcuts

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

msg.info('Anicat overlay loaded: ctrl+1 = Upscaling On, ctrl+2 = Upscaling Off')
