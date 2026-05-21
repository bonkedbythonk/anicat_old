download = """
\b
\b\bExamples:
  # Download all episodes:       anicat download -t <title> -r ':'
  # Download latest episode:     anicat download -t <title> -r '-1'
  # Download episode range:      anicat download -t <title> -r '3:8'
  # Merge subs with ffmpeg:      anicat download -t <title> --merge --clean --no-prompt
  # From file:                   anicat download -t "EOF" -r : -f <file-path>
"""
search = """
\b
\b\bExamples:
  # Search and pick episode:     anicat search -t <title>
  # Watch latest episode:        anicat search -t <title> -r '-1'
  # Binge all episodes:          anicat search -t <title> -r ':'
  # Binge episode range:         anicat search -t <title> -r '3:8'
"""
