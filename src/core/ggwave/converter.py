import ggwave

def encoded(file):
    waveform = ggwave.encode(str(file), protocolId = 1, volume = 20)
    print(str(file))
    return waveform