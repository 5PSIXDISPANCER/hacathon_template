import pyaudio
# from ggwave import ...

def Stream(waveform: bytes,rate: int,frames_per_buffer: int, audio_format = pyaudio.paFloat32):
    """
    Принимаем поток байтов waveform и транслируем
    """
    p = pyaudio.PyAudio()

    stream = p.open(
        format=audio_format, 
        channels=1, 
        rate=rate, 
        output=True, 
        frames_per_buffer=frames_per_buffer
    )
    bytes_per_frame = p.get_sample_size(audio_format)
    num_frames = len(waveform) // 4

    stream.write(waveform, num_frames)
    stream.stop_stream()
    stream.close()
    p.terminate()
