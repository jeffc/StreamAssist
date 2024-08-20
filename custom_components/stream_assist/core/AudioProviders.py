import av
from av.audio.resampler import AudioResampler
from av.container.input import InputContainer
import logging

_LOGGER = logging.getLogger(__name__)

class AudioProvider:
  """Interface for providing audio data.

  This is a base class; should not be directly instantiated."""

  def __init__(self):
    self._closed: bool = False
    self._enabled: bool = False

  def enable(self):
    self._enabled = True

  def disable(self):
    self._enabled = False

  @property
  def closed(self):
    return self._closed

  def close(self):
    """Trigger any cleanup"""
    self._closed = True

  def start(self):
    """start any background work and prepare to yield audio data"""
    pass

  def audio_data(self):
    """Yield chunks of raw audio data in s16 16kHz PCM

    This is run in an executor loop, so blocking operations are allowed
    """
    pass

class AVAudioProvider(AudioProvider):

  def __init__(self, file, **kwargs):
    super().__init__()
    self._container: InputContainer | None = None
    self._file: str = file
    self._av_kwargs = kwargs

  def start(self):
    _LOGGER.debug("starting...")
    if "options" not in self._av_kwargs:
        self._av_kwargs["options"] = {
            "fflags": "nobuffer",
            "flags": "low_delay",
            "timeout": "5000000",
        }

        if self._file.startswith("rtsp"):
            self._av_kwargs["options"]["rtsp_flags"] = "prefer_tcp"
            self._av_kwargs["options"]["allowed_media_types"] = "audio"

    self._av_kwargs.setdefault("timeout", 5)

    # https://pyav.org/docs/9.0.2/api/_globals.html
    self._container = av.open(self._file, **self._av_kwargs)
    _LOGGER.debug("started")

  def audio_data(self):
    resampler = AudioResampler(format="s16", layout="mono", rate=16000)

    try:
        for frame in self._container.decode(audio=0):
            if self._closed:
                return
            if not self._enabled:
                continue
            for frame_raw in resampler.resample(frame):
                chunk = frame_raw.to_ndarray().tobytes()
                yield chunk
    except Exception as e:
        _LOGGER.debug(f"stream exception {type(e)}: {e}")
    finally:
        self._container.close()
        self._container = None
