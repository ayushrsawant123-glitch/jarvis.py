"""Authentication: voice password and optional face check."""

import cv2

from config import VOICE_PASSWORD, SKIP_FACE_LOGIN, FACE_CAPTURE_MS
from speech import speak, listen


def check_voice_password(password_text=None):
    """
    Verify password.
    - If password_text is given (text API), check it directly.
    - Otherwise listen from microphone.
    Returns (ok: bool, message: str).
    """
    if password_text is None:
        speak("Please say the password to proceed")
        heard, error = listen()
        if error:
            speak(error)
            return False, error
        password_text = heard or ""

    password_text = password_text.strip().lower()
    expected = VOICE_PASSWORD.strip().lower()

    if password_text == expected:
        msg = "Access Granted"
        speak(msg)
        return True, msg

    msg = "Access Denied"
    speak(msg)
    return False, msg


def face_login(force=False):
    """
    Optional camera check. Skipped when SKIP_FACE_LOGIN is True (unless force=True).
    Returns (ok: bool, message: str).
    """
    if SKIP_FACE_LOGIN and not force:
        msg = "Face login skipped"
        print(msg)
        return True, msg

    cam = None
    try:
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            msg = "Camera not available. Continuing without face check."
            speak(msg)
            return False, msg

        result, image = cam.read()
        if not result or image is None:
            msg = "Face not detected"
            speak(msg)
            return False, msg

        cv2.imshow("Face Recognition", image)
        cv2.imwrite("face.jpg", image)
        cv2.waitKey(FACE_CAPTURE_MS)
        cv2.destroyAllWindows()
        msg = "Face captured successfully"
        speak(msg)
        return True, msg
    except Exception as exc:
        msg = f"Face login error: {exc}. Continuing without face check."
        speak(msg)
        return False, msg
    finally:
        if cam is not None:
            cam.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


def authenticate(password_text=None, skip_face=None):
    """
    Full auth flow for voice or text.
    skip_face: None uses config; True/False overrides.
    """
    ok, msg = check_voice_password(password_text)
    if not ok:
        return False, msg

    do_skip = SKIP_FACE_LOGIN if skip_face is None else skip_face
    if not do_skip:
        face_ok, face_msg = face_login(force=True)
        # Soft fail: password is enough if camera fails
        if not face_ok:
            return True, f"{msg}. {face_msg}"
        return True, f"{msg}. {face_msg}"

    return True, msg
