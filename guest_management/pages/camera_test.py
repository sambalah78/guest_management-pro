# camera_test.py
import reflex as rx

GOLD = "#D4AF37"
BLACK = "#111111"
DARK_GRAY = "#1A1A1A"


class CameraTestState(rx.DrawState):
    camera_active: bool = False
    camera_error: str = ""
    camera_permission: bool = False

    def start_camera(self):
        self.camera_active = True
        self.camera_error = ""

    def stop_camera(self):
        self.camera_active = False

    def handle_permission_error(self):
        self.camera_error = "Camera permission denied. Please check browser settings."
        self.camera_active = False


def camera_test_page():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Camera Test", size="6", color=GOLD),

                # Camera status
                rx.cond(
                    CameraTestState.camera_error,
                    rx.callout(
                        CameraTestState.camera_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                ),

                # Camera view
                rx.cond(
                    CameraTestState.camera_active,
                    rx.box(
                        rx.html(
                            """
                            <style>
                                #test-video { width: 100%; max-width: 500px; border: 2px solid """ + GOLD + """; border-radius: 8px; }
                            </style>
                            <video id="test-video" autoplay playsinline style="width: 100%;"></video>
                            <div id="test-status" style="text-align: center; margin-top: 10px; color: white;"></div>

                            <script>
                                (function() {
                                    const video = document.getElementById('test-video');
                                    const status = document.getElementById('test-status');

                                    status.innerHTML = '⏳ Requesting camera...';

                                    navigator.mediaDevices.getUserMedia({ video: true })
                                        .then(function(stream) {
                                            video.srcObject = stream;
                                            status.innerHTML = '✅ Camera working!';
                                        })
                                        .catch(function(err) {
                                            status.innerHTML = '❌ Error: ' + err.message;
                                            fetch('/_event/CameraTestState/handle_permission_error', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' }
                                            });
                                        });
                                })();
                            </script>
                            """
                        ),
                        width="100%",
                    ),
                    rx.vstack(
                        rx.icon(tag="camera-off", size=50, color="gray"),
                        rx.text("Camera is off", color="gray"),
                        rx.button(
                            "Start Camera",
                            on_click=CameraTestState.start_camera,
                            bg=GOLD,
                            color=BLACK,
                            _hover={"opacity": 0.9},
                        ),
                        spacing="4",
                        padding="2em",
                    ),
                ),

                spacing="4",
                width="100%",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
            padding="2em",
            width="500px",
        ),
        bg=BLACK,
        height="100vh",
    )