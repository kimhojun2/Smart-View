import sounddevice as sd
from pvrecorder import PvRecorder

def list_audio_devices():
    print("Available audio devices:")
    devices = sd.query_devices()
    for idx, device in enumerate(devices):
        print(f"Index: {idx}, Name: {device['name']}, Input Channels: {device['max_input_channels']}, Output Channels: {device['max_output_channels']}")




def list_audio_device():
    devices = PvRecorder.get_available_devices()
    print("Available audio devices:")
    for i, device in enumerate(devices):
        print(f"Index: {i}, Device Info: {device}")

if __name__ == "__main__":
    list_audio_devices()
    list_audio_device()