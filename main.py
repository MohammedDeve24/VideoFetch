# Importing Kivy and setting version requirements
import kivy
kivy.require('2.3.0')  # Ensure the Kivy version is compatible

# Configuring Kivy application settings
from kivy.config import Config
Config.set('kivy', 'window_icon', 'assets/icon/download.ico')  # Setting the app icon

# Importing required libraries
from TikTokApi import TikTokApi  # TikTok API for video downloading
import instaloader  # Instagram API for downloading posts
from pytube import YouTube, Playlist  # Library for downloading videos from YouTube
import datetime  # For handling video length and timestamps
import os  # For file and directory operations
from pathlib import Path  # For path manipulations
import threading  # To run tasks in the background
import logging  # For logging errors and debugging information
from hurry.filesize import size  # For converting file size to human-readable format
from kivy import platform  # To detect the current platform (Android, Windows, etc.)
from kivy.clock import mainthread  # To run functions on the main thread
from kivy.lang import Builder  # To load Kivy language (KV) files
from kivy.properties import StringProperty, ListProperty, BooleanProperty, ObjectProperty  # Properties for dynamic binding
from kivy.uix.floatlayout import FloatLayout  # A flexible UI layout
from kivymd.app import MDApp  # KivyMD app base class
from kivymd.toast import toast  # For displaying short messages to the user
from kivymd.uix.boxlayout import MDBoxLayout  # Box layout for arranging widgets
from kivymd.uix.button import MDFloatingActionButton  # Floating button for actions
from kivymd.uix.card import MDCard  # Card component for UI design
from kivymd.uix.screen import MDScreen  # Screen component for multi-screen apps
from kivymd.uix.tooltip import MDTooltip  # Tooltip for additional information
from kivy.clock import Clock  # For scheduling tasks
import ffmpeg  # For merging video and audio files
import shutil  # For file operations like moving files
import re  # For regex operations
from playwright.sync_api import sync_playwright  # For handling TikTok API calls
# to handel downloding videos 
class DownloadCard(MDCard):
    yt = ObjectProperty()
    title = StringProperty('Loading')
    thumbnail = StringProperty()
    resolution = StringProperty('Loading')
    link = StringProperty()
    download_icon = StringProperty('download')
    length = StringProperty('Loading')
    file_size = StringProperty('Loading')
    download = BooleanProperty(False)
    downloading = BooleanProperty(False)
    isNoTDownloadable = BooleanProperty(True)
    
    @mainthread
    def progress_func(self, stream, chunk, bytes_remaining):
        value = round((1 - bytes_remaining / stream.filesize) * 100, 3)
        self.ids.progress_bar.value = value
    @mainthread
    def complete_func(self, *args):
        self.download_icon = 'check-circle'
    
    @mainthread
    def remove_from_list(self):
        app = MDApp.get_running_app()
        app.root.ids.scroll_box.remove_widget(self)
        if self.link in app.root.playlist:
            app.root.playlist.remove(self.link)

    def on_link(self, *args):
        app = MDApp.get_running_app()
        app.isLoading = True
        threading.Thread(target=self.start).start()
    @mainthread
    def start(self):
        self.ids.progress_bar.value = 0
        self.download_icon = 'download'
        app = MDApp.get_running_app()
        # for ticktok
        if "tiktok.com" in self.link:
            try:
                api = TikTokApi()
                video = api.video(url=self.link)
                video_data = video.bytes()
                
                self.title = video.info_full['desc']
                self.thumbnail = video.info_full['cover']
                self.resolution = "N/A"
                self.length = str(datetime.timedelta(seconds=video.info_full['duration']))
                self.file_size = size(len(video_data))
                self.isNoTDownloadable = False

                # Save the TikTok video (temporary path for merging if needed)
                video_path = os.path.join(app.output_path, 'tiktok_video.mp4')
                with open(video_path, 'wb') as f:
                    f.write(video_data)

                # Use FFmpeg to convert video if needed, or save directly
                output_file = os.path.join(app.output_path, f"{self.title}.mp4")
                shutil.move(video_path, output_file)  # Move to final location
                
                self.download_icon = 'check-circle'
                toast(f"TikTok video downloaded successfully")
            except Exception as e:
                logging.error(f"TikTok Download Error: {e}")
                self.remove_from_list()
                toast(f"Error downloading TikTok video: {e}")
        # for instagram
        elif "instagram.com" in self.link:
            # Handle Instagram video download
            try:
                self.title = "Instagram Video"
                self.thumbnail = "Instagram Thumbnail"  # Placeholder, as getting thumbnails directly from Instagram is complex
                self.resolution = "N/A"  # Instagram doesn't provide resolution easily
                self.length = "N/A"  # Instagram doesn't provide length easily
                self.file_size = "N/A"  # File size needs to be determined after download
                self.isNoTDownloadable = False
            except Exception as e:
                self.remove_from_list()
                toast(f'Error fetching Instagram video details: {e}')
        else:
            # Handle YouTube video download (existing functionality)
            try:
                # Extract video ID from the link using regex (optional for better error handling)
                match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", self.link)
                if not match:
                    raise ValueError("Invalid YouTube link format")

                self.yt = YouTube(
                    self.link,
                    on_progress_callback=self.progress_func,
                    on_complete_callback=self.complete_func,
                )

                # Fetch video details
                self.title = self.yt.title or "Unknown Title"
                self.thumbnail = self.yt.thumbnail_url or ""
                self.resolution = self.yt.streams.get_highest_resolution().resolution or "N/A"
                self.length = str(datetime.timedelta(seconds=self.yt.length))
                self.file_size = size(self.yt.streams.get_highest_resolution().filesize)
                self.isNoTDownloadable = False
            except Exception as e:
                logging.error(f"YouTube Download Error: {e}")
                self.remove_from_list()
                toast(f"Error with YouTube video: {e}")


    def download_video(self, yt, operation):
        self.downloading = True
        app = MDApp.get_running_app()
        try:
            if "instagram.com" in self.link:
                # Download video from Instagram
                loader = instaloader.Instaloader()
                try:
                    loader.download_post(instaloader.Post.from_shortcode(loader.context, self.link.split("/")[-2]), target=app.output_path)
                    self.download_icon = 'check-circle'
                    toast(f"Instagram video downloaded successfully")
                except Exception as e:
                    logging.error(f"Instagram Download Error: {e}")
                    toast(f"Error downloading Instagram video: {e}")
             # the logic of ticktok
            elif "tiktok.com" in self.link:
            # Download video from TikTok
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        context = browser.new_context()
                        api = TikTokApi(context=context)  # Pass the context to TikTokApi
                        video = api.video(url=self.link)
                        video_bytes = video.bytes()

                        # Save the video to a file
                        video_path = os.path.join(app.output_path, 'tiktok_video.mp4')
                        with open(video_path, 'wb') as f:
                            f.write(video_bytes)

                        self.download_icon = 'check-circle'
                        toast(f"TikTok video downloaded successfully!")
                        browser.close()
                except Exception as e:
                    logging.error(f"TikTok Download Error: {e}")
                    toast(f"Error downloading TikTok video: {e}")
            else:  # For YouTube
                if operation == "Video and Audio":
                    try:
                        # Select video and audio streams
                        video_stream = yt.streams.get_highest_resolution()
                        audio_stream = yt.streams.filter(only_audio=True).first()

                        # Download video and audio separately
                        video_path = video_stream.download(output_path=app.output_path, filename="temp_video.mp4")
                        audio_path = audio_stream.download(output_path=app.output_path, filename="temp_audio.mp4")

                        # Merge video and audio using FFmpeg
                        output_file = os.path.join(app.output_path, f"{yt.title}.mp4")
                        (
                            ffmpeg
                            .input(video_path)
                            .input(audio_path)
                            .output(output_file, vcodec="copy", acodec="aac", strict="experimental")
                            .run(overwrite_output=True)
                        )

                        # Cleanup temporary files
                        os.remove(video_path)
                        os.remove(audio_path)
                        self.download_icon = "check-circle"
                        toast("Video downloaded successfully with audio")
                    except Exception as e:
                        logging.error(f"Download Error: {e}")
                        toast(f"Error during download: {e}")
                else:
                    try:
                        # Download only audio
                        audio_stream = yt.streams.filter(only_audio=True, file_extension="mp4").first()
                        audio_stream.download(output_path=app.output_path, filename=f"{yt.title}.mp3")
                        self.download_icon = "check-circle"
                        toast("Audio downloaded successfully")
                    except Exception as e:
                        logging.error(f"Audio Download Error: {e}")
                        toast(f"Error downloading audio: {e}")
        except Exception as e:
            self.remove_from_list()
            logging.error(f"Error: {e}")
            toast(text=f'Something went wrong: {e}')


# to handel user input 
class YoutubeDownloader(MDScreen):
    link = StringProperty()
    playlist = ListProperty()
    isNotPlayList = BooleanProperty()

    def go(self):
        threading.Thread(target=self.start).start()

    @mainthread
    def start(self):
        self.ids.scroll_box.clear_widgets()
        self.link = self.ids.link_holder.text

        try:
            self.playlist = Playlist(self.link)
            self.isNotPlayList = False

            # to make sure all widgets to scroll_box in the main thread
            for play_list_item in self.playlist:
                card = DownloadCard()
                card.link = play_list_item
                Clock.schedule_once(lambda dt: self.ids.scroll_box.add_widget(card))
        except:
            self.isNotPlayList = True
            card = DownloadCard()
            card.link = self.link
            Clock.schedule_once(lambda dt: self.ids.scroll_box.add_widget(card))

    def download_all(self):
        children = self.ids.scroll_box.children
        for child in children:
            child.download_video(child.yt, child.operation)

# for GUI 
class TopBarIconBox(MDBoxLayout):
    pass


class MobileFloatButton(MDFloatingActionButton, MDTooltip):
    pass


class MobileBottomButton(FloatLayout):
    pass


class App(MDApp):
    isLoading = BooleanProperty(False)
    icon = 'assets/icon/download.ico'
    if platform == 'win':
        output_path = f'{str(Path.home() / "Downloads")}/VideoFetch/'
    elif platform == 'android':
        from android.storage import primary_external_storage_path
        output_path = f'{str(primary_external_storage_path())}/VideoFetch/'

    def build(self):
        root = Builder.load_file('main.kv')
        self.title = 'VideoFetch' #app name 
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'DeepPurple'
        self.theme_cls.accent_palette = 'Amber'

        if platform == 'win':
            root.ids.appbar.add_widget(TopBarIconBox(), 1)
        elif platform == 'android':
            root.add_widget(MobileFloatButton())
            root.add_widget(MobileBottomButton())
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        return root

    def on_start(self):
        try:
            os.mkdir(self.output_path)
        except:
            pass


App().run()
