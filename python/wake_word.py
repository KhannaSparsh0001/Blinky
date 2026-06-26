import argparse
import time
import sys
import os

# Configure ONNX Runtime and OpenMP to be passive and single-threaded to prevent CPU starvation of Ollama
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
os.environ["ORT_MAX_NUM_THREADS"] = "1"

if sys.platform == "win32":
    try:
        import ctypes
        # Set process priority to BELOW_NORMAL_PRIORITY_CLASS (0x4000) so Ollama gets CPU priority
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass

def start_wake_word_detector(model_name="hey_blinky.onnx"):
    try:
        # pyrefly: ignore [missing-import]
        import sounddevice as sd
        import numpy as np
        from openwakeword.model import Model
    except ImportError as e:
        print(f"Error importing dependencies: {e}", file=sys.stderr)
        return

    try:
        # Resolve absolute path to model if it's relative
        if not os.path.isabs(model_name):
            if not os.path.exists(model_name):
                # Try relative to this script's directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                candidate = os.path.join(script_dir, os.path.basename(model_name))
                if os.path.exists(candidate):
                    model_name = candidate

        print(f"Loading openwakeword model: {model_name}", file=sys.stderr)
        
        # Ensure openwakeword required feature models (melspectrogram.onnx, embedding_model.onnx) are downloaded
        import openwakeword.utils
        openwakeword.utils.download_models()
        
        if os.path.exists(model_name) and model_name.endswith('.onnx'):
            owwModel = Model(wakeword_models=[model_name])
        else:
            owwModel = Model(wakeword_models=[model_name])
            
        print("Model loaded successfully. Listening for wake word...", file=sys.stderr)

        audio_queue = []

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(status, file=sys.stderr)
            # The indata is float32 between -1 and 1. OpenWakeWord expects int16.
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            audio_queue.append(audio_data)
            # Prevent queue accumulation/latency lag during heavy LLM activity
            if len(audio_queue) > 5:
                del audio_queue[:-5]

        # OpenWakeWord expects 16kHz, 1-channel, 16-bit PCM audio
        stream = sd.InputStream(samplerate=16000, blocksize=1280, channels=1, dtype='float32', callback=audio_callback)
        
        with stream:
            while True:
                if len(audio_queue) > 0:
                    audio_chunk = audio_queue.pop(0)
                    
                    prediction = owwModel.predict(audio_chunk)
                    
                    for mdl, score in prediction.items():
                        if score > 0.5:  # Threshold can be adjusted
                            print("WAKE_WORD_DETECTED", flush=True)
                            owwModel.reset()
                            audio_queue.clear()
                            time.sleep(2)
                    
                    # Yield CPU briefly so Ollama and Tauri threads are not starved
                    time.sleep(0.005)
                else:
                    time.sleep(0.01)

    except KeyboardInterrupt:
        print("Stopping wake word detector.", file=sys.stderr)
    except Exception as e:
        print(f"Error in wake word detector: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenWakeWord Detector")
    parser.add_argument("--model", type=str, default="hey_blinky.onnx", help="Built-in model name or path to a custom .onnx model (e.g., hey_blinky.onnx)")
    args = parser.parse_args()
    
    start_wake_word_detector(args.model)
