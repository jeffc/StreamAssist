import asyncio
import logging
from .AudioProviders import RTPAudioProvider, AVAudioProvider

_LOGGER = logging.getLogger(__name__)

class Stream:
    def __init__(self):
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()
        #self.provider: AudioProvider | None = None
        self.provider = None

    @property
    def closed(self):
      if self.provider is None:
        return True
      return self.provider.closed

    def open_av(self, file: str, **kwargs):
        _LOGGER.debug(f"av stream open")
        self.provider = AVAudioProvider(file, **kwargs)
        self.provider.start()

    def open_rtp(self, port: int):
        _LOGGER.debug(f"rtp stream open")
        self.provider = RTPAudioProvider(port)
        self.provider.start()

    def run(self, end=True):
        _LOGGER.debug("stream start")

        try:
          for chunk in self.provider.audio_data():
              self.queue.put_nowait(chunk)
        except Exception as e:
            _LOGGER.debug(f"stream exception {type(e)}: {e}")
        finally:
            self.provider.close()

        if end and self.provider.enabled:
            self.queue.put_nowait(b"")

        _LOGGER.debug("stream end")

    def close(self):
        _LOGGER.debug(f"stream close")
        self.provider.close()

    def start(self):
        while self.queue.qsize():
            self.queue.get_nowait()

        self.provider.enable()

    def stop(self):
        self.provider.disable()

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        return await self.queue.get()
