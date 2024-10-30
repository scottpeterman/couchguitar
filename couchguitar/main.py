import sys
import simpleaudio as sa
import importlib.resources as pkg_resources

from pydub import AudioSegment
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QFileDialog, QSplitter, QWidget, QTextEdit, QLabel, QHBoxLayout, \
    QFrame, QSpacerItem, QSizePolicy, QMainWindow, QDialog, QPushButton
from qfluentwidgets import (
    NavigationInterface, NavigationItemPosition,
    NavigationPushButton, Slider, ComboBox, FluentIcon as FIF, setTheme, Theme
)
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

from couchguitar import resource


class RecorderThread(QThread):
    data_recorded = pyqtSignal(np.ndarray)

    def __init__(self, fs=44100, channels=2):
        super().__init__()
        self.fs = fs
        self.channels = channels
        self.duration = 900  # Duration of recording in seconds (15 minutes)
        self.warning_duration = 840  # 14 minutes warning (in seconds)
        self.recording = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.warn_time)

    def start_recording(self):
        self.timer.start(1000 * 60 * 14)  # Start timer for 14-minute warning
        self.start()

    def run(self):
        self.recording = sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=self.channels, dtype='float64')
        sd.wait()
        self.data_recorded.emit(self.recording)
        self.timer.stop()  # Stop timer after recording completes

    def warn_time(self):
        self.timer.stop()
        self.parent().show_warning()  # Call the dialog's warning method

class RecordingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Audio")
        self.setGeometry(200, 200, 300, 200)
        self.layout = QVBoxLayout(self)

        # Maximum time label
        self.time_label = QLabel("Note: Maximum recording time is 15 minutes.")
        self.layout.addWidget(self.time_label)

        # Buttons for controlling recording
        self.start_button = QPushButton("Start Recording")
        self.stop_button = QPushButton("Stop Recording")
        self.save_button = QPushButton("Save Recording")
        self.save_button.setEnabled(False)

        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.save_button)

        # Setup recording thread
        self.recorder_thread = RecorderThread()
        self.recorder_thread.data_recorded.connect(self.store_recording)

        # Connect button actions
        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.save_button.clicked.connect(self.save_recording)
        self.recording_data = None

    def start_recording(self):
        self.recorder_thread.start_recording()
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(False)

    def stop_recording(self):
        sd.stop()
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(True)

    def store_recording(self, data):
        self.recording_data = data

    def save_recording(self):
        if self.recording_data is not None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Recording", "", "WAV Files (*.wav)")
            if file_path:
                scaled = np.int16(self.recording_data / np.max(np.abs(self.recording_data)) * 32767)
                write(file_path, self.recorder_thread.fs, scaled)






class SongInterface(QWidget):
    """ Interface for displaying song text with auto-scrolling """

    def __init__(self):
        super().__init__()

        # Frame for styling and padding around the text area
        frame = QFrame(self)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(10, 10, 10, 10)  # Add padding around the text
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("background-color: #2b2b2b; border-radius: 8px;")  # Matching dark theme

        # Song text display
        self.text_edit = QTextEdit(frame)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 14))  # Default monospace font
        frame_layout.addWidget(self.text_edit)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addWidget(frame)

        # Timer for auto-scrolling
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.auto_scroll)
        self.scroll_speed = 5  # Default scroll speed

        self.setLayout(layout)

    def load_text(self, text):
        """ Load text content into QTextEdit """
        self.text_edit.setPlainText(text)

    def auto_scroll(self):
        """ Automatically scroll the text display """
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().value() + 1
        )

    def toggle_scroll(self, enable):
        """ Enable or disable scrolling based on toggle """
        if enable:
            self.scroll_timer.start(200 // self.scroll_speed)
        else:
            self.scroll_timer.stop()

    def set_scroll_speed(self, speed):
        """ Set scroll speed from slider """
        self.scroll_speed = speed
        if self.scroll_timer.isActive():
            self.scroll_timer.start(200 // self.scroll_speed)


class ControlInterface(QWidget):
    """ Interface for file controls, playback, and settings """

    def __init__(self, song_interface):
        super().__init__()
        self.song_interface = song_interface

        # Main layout setup
        layout = QVBoxLayout(self)
        # Load image using importlib.resources
        self.image_label = QLabel(self)
        with pkg_resources.path(resource, "guitar.png") as image_path:
            pixmap = QPixmap(str(image_path))
            self.image_label.setPixmap(
                pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        layout.addWidget(self.image_label)

        self.record_audio_button = NavigationPushButton(FIF.MICROPHONE, "Record Audio", isSelectable=False)
        self.record_audio_button.clicked.connect(self.open_recording_dialog)
        layout.addWidget(self.record_audio_button)

        # File controls
        self.open_file_button = NavigationPushButton(FIF.DOCUMENT, "Open Text File", isSelectable=False)
        self.open_file_button.clicked.connect(self.open_file)
        layout.addWidget(self.open_file_button)

        self.load_audio_button = NavigationPushButton(FIF.MUSIC, "Load WAV", isSelectable=False)
        self.load_audio_button.clicked.connect(self.load_audio)
        layout.addWidget(self.load_audio_button)

        # Playback controls
        self.play_button = NavigationPushButton(FIF.PLAY, "Play", isSelectable=False)
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_audio)
        layout.addWidget(self.play_button)

        self.pause_button = NavigationPushButton(FIF.PAUSE, "Pause", isSelectable=False)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_audio)
        layout.addWidget(self.pause_button)

        self.stop_button = NavigationPushButton(FIF.CLOSE, "Stop", isSelectable=False)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_audio)
        layout.addWidget(self.stop_button)

        # Spacer to push image down below playback controls
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))


        # Spacer to push the controls to the bottom
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Font size and scroll speed controls
        control_frame = QFrame()
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(0, 0, 0, 0)

        # Font size selector
        control_layout.addWidget(QLabel("Font Size:"))
        self.font_size_selector = ComboBox()
        self.font_size_selector.addItems([str(i) for i in range(8, 25)])
        self.font_size_selector.setCurrentText("14")
        self.font_size_selector.currentTextChanged.connect(self.set_font_size)
        control_layout.addWidget(self.font_size_selector)

        control_layout.addWidget(QLabel("Scroll Speed:"))
        self.scroll_speed_slider = Slider(Qt.Orientation.Horizontal)
        self.scroll_speed_slider.setRange(1, 20)
        self.scroll_speed_slider.setValue(5)
        self.scroll_speed_slider.valueChanged.connect(self.song_interface.set_scroll_speed)
        control_layout.addWidget(self.scroll_speed_slider)

        # Play/Pause scroll button
        self.play_pause_scroll_button = NavigationPushButton(FIF.PLAY, "Play Scroll", isSelectable=False)
        self.play_pause_scroll_button.clicked.connect(self.toggle_scroll)
        control_layout.addWidget(self.play_pause_scroll_button)

        # Add control frame to main layout at the bottom
        layout.addWidget(control_frame)

        # Audio playback variables
        self.audio_segment = None
        self.play_obj = None
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback_position)
        self.is_paused = False
        self.current_position = 0
    def set_font_size(self, size):
        """ Update font size in the song interface """
        font = QFont("Courier", int(size))
        self.song_interface.text_edit.setFont(font)

    def open_recording_dialog(self):
        self.recording_dialog = RecordingDialog(self)
        self.recording_dialog.show()

    def open_file(self):
        """ Open text file and display content in song interface """
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Open Song File", "", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "r") as file:
                self.song_interface.load_text(file.read())

    def load_audio(self):
        """ Load an audio file for playback """
        file_path, _ = QFileDialog.getOpenFileName(self, "Load WAV File", "", "WAV Files (*.wav)")
        if file_path:
            self.audio_segment = AudioSegment.from_wav(file_path)
            self.current_position = 0
            self.is_paused = False
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)

    def play_audio(self):
        """ Play or resume audio """
        if self.audio_segment:
            # Determine the segment to play based on current position
            if self.is_paused:
                segment = self.audio_segment[self.current_position:]
            else:
                segment = self.audio_segment
            raw_data = segment.raw_data
            sample_rate = segment.frame_rate
            num_channels = segment.channels
            sample_width = segment.sample_width

            # Play the audio
            self.play_obj = sa.play_buffer(raw_data, num_channels, sample_width, sample_rate)
            self.is_paused = False
            self.playback_start_time = 0
            self.playback_timer.start(100)  # Update playback position every 100ms

    def pause_audio(self):
        """ Safely pause the audio playback """
        if self.play_obj and not self.is_paused:
            # Stop current playback and save position
            self.play_obj.stop()
            self.playback_timer.stop()
            self.current_position += self.playback_start_time  # Update current position with playback time
            self.is_paused = True

    def stop_audio(self):
        """ Stop the audio playback """
        if self.play_obj:
            self.play_obj.stop()
            self.playback_timer.stop()
            self.is_paused = False
            self.current_position = 0

    def update_playback_position(self):
        """ Update playback position tracker """
        self.playback_start_time += 100  # Increment playback time by 100ms
    def toggle_scroll(self):
        """ Toggle scrolling in song interface """
        is_scrolling = not self.song_interface.scroll_timer.isActive()
        self.song_interface.toggle_scroll(is_scrolling)
        self.play_pause_scroll_button.setText("Pause Scroll" if is_scrolling else "Play Scroll")


class MainFluentWindow(QMainWindow):
    """ Main application window with Fluent navigation """

    def __init__(self):
        super().__init__()

        # Apply dark theme
        setTheme(Theme.DARK)
        self.songInterface = SongInterface()

        self.controlInterface = ControlInterface(self.songInterface)

        # Create a main layout for the window
        main_layout = QVBoxLayout()
        central_widget = QWidget()
        self.label_graphic = central_widget
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Create a splitter to allocate more space to the SongInterface
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Set stretch factors so the SongInterface takes most of the space
        splitter.addWidget(self.controlInterface)
        splitter.addWidget(self.songInterface)
        splitter.setStretchFactor(1, 3)  # Make SongInterface take 3x more space than ControlInterface

        # Add the splitter to the main layout
        main_layout.addWidget(splitter)
        # Resize the window to 90% of screen width and 80% of screen height

        self.setWindowTitle('Couch Guitar')

    def resizeEvent(self, event):
        """ Override resize event to dynamically hide/show image based on window height """
        self.controlInterface.image_label.hide()
        window_height = self.height()
        threshold_height = 400  # Set a threshold for hiding the image

        # Show or hide the image based on the window height
        if window_height < threshold_height:
            self.controlInterface.image_label.hide()
        else:
            # pass

            self.controlInterface.image_label.show()

        # Call the original resizeEvent
        super().resizeEvent(event)



def main():
    app = QApplication(sys.argv)
    window = MainFluentWindow()

    # Get screen dimensions
    screen_geometry = QApplication.primaryScreen().geometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()

    # Set window dimensions to half of the screen dimensions
    width = int(screen_width * 0.9)
    height = int(screen_height * 0.8)
    print(f"Height: {height} Width:{width}")
    window.resize(width, height)

    # Calculate the x and y position to center the window
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.move(x, y - 20)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()