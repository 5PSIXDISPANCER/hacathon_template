import base64
import ggwave

# Размер "сырого" (до base64) куска данных, который упаковывается в одно
# ggwave-сообщение. ggwave — это по сути аудио-модем с небольшой полезной
# нагрузкой на одно сообщение (десятки-сотни байт в зависимости от протокола).
# Если декодирование на приёме будет ненадёжным (пропуски чанков) — в первую
# очередь пробуйте УМЕНЬШИТЬ это значение.
CHUNK_RAW_SIZE = 80


def _pack(index: int, total: int, chunk: bytes) -> str:
    """Собирает текстовый payload одного чанка: 'INDEX/TOTAL:base64data'."""
    b64 = base64.b64encode(chunk).decode("ascii")
    return f"{index:05d}/{total:05d}:{b64}"


def _unpack(payload: str):
    """Разбирает payload обратно в (index, total, bytes)."""
    header, _, b64 = payload.partition(":")
    idx_str, _, total_str = header.partition("/")
    index = int(idx_str)
    total = int(total_str)
    chunk = base64.b64decode(b64)
    return index, total, chunk


def encode_file(data: bytes, protocol_id: int = 1, volume: int = 20,
                 chunk_size: int = CHUNK_RAW_SIZE):
    """
    Бьёт бинарные данные (например, содержимое .7z архива) на чанки
    и кодирует каждый в отдельную ggwave-волну.

    Возвращает список waveform'ов (bytes) в порядке, в котором их нужно
    проигрывать/передавать.
    """
    if len(data) == 0:
        chunks = [b""]
    else:
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    total = len(chunks)
    waveforms = []
    for index, chunk in enumerate(chunks):
        payload = _pack(index, total, chunk)
        waveform = ggwave.encode(payload, protocolId=protocol_id, volume=volume)
        waveforms.append(waveform)

    return waveforms


def decode_chunk(instance, audio_buffer: bytes):
    """
    Пытается декодировать один буфер аудио (кусок, прочитанный с микрофона).

    Возвращает (index, total, chunk_bytes) если в буфере нашлось валидное
    ggwave-сообщение нашего формата, иначе None.
    """
    raw = ggwave.decode(instance, audio_buffer)
    if raw is None:
        return None
    try:
        payload = raw.decode("utf-8")
        return _unpack(payload)
    except Exception:
        # Либо это чужой/битый сигнал, либо шум был ошибочно распознан как сообщение
        return None
