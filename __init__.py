import os.path
import random
import time
from os.path import dirname, exists, join
from ovos_bus_client.message import Message
from ovos_bus_client.session import SessionManager, Session
from ovos_number_parser import extract_number
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill
from ovos_utils.log import LOG


class WebcamSkill(OVOSSkill):

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   gui_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   requires_gui=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True,
                                   no_gui_fallback=True)

    def initialize(self):
        self.sess2cam = {}
        if "play_sound" not in self.settings:
            self.settings["play_sound"] = True
        self.add_event("ovos.phal.camera.pong", self.handle_pong)
        self.bus.emit(Message("ovos.phal.camera.ping"))

    def handle_pong(self, message: Message):
        sess = SessionManager.get(message)
        LOG.info(f"Camera available for session: {sess.session_id}")
        self.sess2cam[sess.session_id] = True

    @property
    def pictures_folder(self) -> str:
        return self.settings.get("pictures_folder", "~/Pictures")

    def play_camera_sound(self):
        if self.settings["play_sound"]:
            s = self.settings.get("camera_sound_path") or \
                join(dirname(__file__), "camera.wav")
            if exists(s):
                self.play_audio(s, instant=True)

    def sess_has_camera(self, message) -> bool:
        sess = SessionManager.get(message)
        # check if this session has the camera PHAL plugin installed
        has_camera = (self.sess2cam.get(sess.session_id) is not None or
                      self.bus.wait_for_response(message.forward("ovos.phal.camera.ping"),
                                                "ovos.phal.camera.pong",
                                                timeout=0.5))
        LOG.debug(f"has camera: {has_camera}")
        if has_camera and sess.session_id not in self.sess2cam:
            self.sess2cam[sess.session_id] = True
        return has_camera

    @intent_handler("have_camera.intent")
    def handle_camera_check(self, message):
        if self.sess_has_camera(message):
            self.speak_dialog("camera_yes")
        else:
            self.speak_dialog("camera_error")

    @intent_handler("picture_location.intent")
    def handle_picture_location(self, message):
        self.speak_dialog("picture.location", {"path": self.pictures_folder})

    def do_countdown(self, seconds: int):
        # need time to allow sensor to stabilize
        for n in range(seconds, 0, -1):
            self.gui.show_text(str(n))
            self.speak(str(n), wait=True)

    @intent_handler("take_picture.intent")
    def handle_take_picture(self, message):
        if not self.sess_has_camera(message):
            self.speak_dialog("camera_error")
            return

        self.speak_dialog("get_ready", wait=True)

        countdown = extract_number(message.data.get("countdown", ""), lang=self.lang)
        if countdown:
            self.do_countdown(int(countdown))
        elif self.settings.get("countdown"):
            self.do_countdown(3)

        pic_path = join(self.pictures_folder, time.strftime("%Y-%m-%d_%H-%M-%S") + ".jpg")
        self.bus.emit(message.forward("ovos.phal.camera.get", {"path": pic_path}))

        self.play_camera_sound()

        self.gui.clear()
        self.gui.show_image(os.path.expanduser(pic_path))
        if random.choice([True, False]):
            self.speak_dialog("picture")
