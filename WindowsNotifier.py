import winotify
import os

class WindowsNotifier:
    def __init__(self, tag: str) -> None:
        registry = winotify.Registry(tag, winotify.PY_EXE, os.path.abspath(__file__))
        self.NOTIFIER = winotify.Notifier(registry)
    
    def showSnackbar(
        self,
        title: str,
        message: str,
        icon: str = '',
        duration: str = 'short'
    ):
        snackbar = self.NOTIFIER.create_notification(
            title = title,
            msg = message,
            duration = duration,
            icon = icon
        )
        snackbar.set_audio(winotify.audio.Mail, loop=False)
        snackbar.show()
