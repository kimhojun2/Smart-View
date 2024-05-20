import pvporcupine
from pvrecorder import PvRecorder
import os

class Listen():
    def __init__(self):
        super().__init__()
        # self.access_key = "BiQeBmnb2sGBb+/o+rlSbgRVOVR3YHdehy2oziBrO5QJLI2b09/Jgg==" #윈도우용
        self.access_key = "LRG4RkIxexfXfpxirvtavEK2/6hLsNfgFHyZJCESRbnUNv50Za2Exg==" #리눅스용
        self.current_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'wakeword')
        self.keyword_album = os.path.join(self.current_dir, '스마트뷰.ppn')
        self.keyword_next = os.path.join(self.current_dir, '다음사진.ppn')
        self.keyword_previous = os.path.join(self.current_dir, '이전사진.ppn')
        self.model_path = os.path.join(self.current_dir, 'porcupine_params_ko.pv')
        self.porcupine = None
        self.recorder = None

    def run(self):
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.keyword_album, self.keyword_next, self.keyword_previous],
                model_path=self.model_path
            )

            self.recorder = PvRecorder(
                frame_length=self.porcupine.frame_length,
                device_index=0,
            )

            self.recorder.start()

            print("Listening... Press Ctrl+C to exit")

            while True:
                pcm_frame = self.recorder.read()
                if len(pcm_frame) != self.porcupine.frame_length:
                    print(f"Frame length mismatch: {len(pcm_frame)} expected {self.porcupine.frame_length}")
                    continue
                keyword_index = self.porcupine.process(pcm_frame)
                if keyword_index >= 0:
                    self.wake_word_callback(keyword_index)

        except Exception as e:
            print('Stopping...', str(e))
        finally:
            if self.porcupine:
                self.porcupine.delete()
            if self.recorder:
                self.recorder.stop()
                self.recorder.delete()

    def wake_word_callback(self, keyword_index):
        if keyword_index == 0:
            print("Album keyword detected!")
            # STT_dir = os.path.dirname(os.path.abspath(__file__))
            # stt_path = os.path.join(STT_dir, 'STT.py')
            # stt_process = subprocess.Popen(['python', stt_path])
        elif keyword_index == 1:
            print("Next photo keyword detected!")
            # self.display.next_image()
        elif keyword_index == 2:
            print("Previous photo keyword detected!")
            # self.display.previous_image()

if __name__ == "__main__":
    listener = Listen()
    listener.run()
