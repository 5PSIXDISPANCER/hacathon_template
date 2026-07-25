import ggwave

def rad(file):
    waveform = ggwave.encode(file, protocolId = 1, volume = 20)
    return waveform
