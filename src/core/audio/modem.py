import hashlib
import logging
import os
import struct
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import reedsolo
import scipy.signal
from scipy.io import wavfile

logger = logging.getLogger("modem")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class ModemConfig:
    """Все параметры физического и канального уровня модема в одном месте."""

    fs: int = 44100
    sym_dur: float = 0.15                 # длительность символа, сек
    k_channels: int = 4                   # число параллельных частотных каналов
    f_base: int = 4000                     # стартовая частота, Гц
    channel_spacing: int = 400            # шаг между каналами, Гц
    tone_step: int = 25                   # шаг частот внутри канала, Гц
    n_tones: int = 16                     # 4 бита (nibble) на канал => 16 тонов
    preamble: bytes = b'\xDE\xAD\xBE\xEF'
    ecc_symbols: int = 20                 # символов ECC Рида-Соломона (было 16)
    frame_id_bytes: int = 3               # было 2 => лимит ~4 МБ, теперь ~16.7М кадров
    payload_per_frame: int = 128          # байт полезных данных на кадр (было 64)
    inter_frame_gap: float = 0.3          # пауза между кадрами, сек
    lead_silence: float = 1.0             # тишина в начале/конце записи, сек
    frame_gap_search_margin: float = 2.5  # запас окна поиска следующего кадра
    max_frame_id_gap: int = 5000          # защита от аномальных скачков frame_id

    @property
    def meta_frame_id(self) -> int:
        return 0

    @property
    def packet_bytes_len(self) -> int:
        return self.frame_id_bytes + self.payload_per_frame + self.ecc_symbols


DEFAULT_CONFIG = ModemConfig()


class Modem:
    """Кодер/декодер файлов в аудиосигнал по схеме многоканального M-FSK."""

    def __init__(self, config: ModemConfig = DEFAULT_CONFIG):
        self.cfg = config
        self._rs = reedsolo.RSCodec(config.ecc_symbols)
        self._ref_cache: dict = {}  # n_samples_per_symbol -> (cos_ref, sin_ref)

    # ------------------------------------------------------------------ #
    # Общие вспомогательные методы
    # ------------------------------------------------------------------ #
    def _freqs(self) -> np.ndarray:
        cfg = self.cfg
        return np.array([
            [cfg.f_base + k * cfg.channel_spacing + s * cfg.tone_step for s in range(cfg.n_tones)]
            for k in range(cfg.k_channels)
        ])

    def _get_reference_waveforms(self, n_samples: int):
        """cos/sin опорные сигналы не зависят от входных данных — кэшируем."""
        cached = self._ref_cache.get(n_samples)
        if cached is not None:
            return cached
        cfg = self.cfg
        t = np.arange(n_samples) / cfg.fs
        freqs = self._freqs()                                   # (K, n_tones)
        cos_ref = np.cos(2 * np.pi * freqs[:, :, None] * t)      # (K, n_tones, N)
        sin_ref = np.sin(2 * np.pi * freqs[:, :, None] * t)
        self._ref_cache[n_samples] = (cos_ref, sin_ref)
        return cos_ref, sin_ref

    # ------------------------------------------------------------------ #
    # Кодирование
    # ------------------------------------------------------------------ #
    def generate_frame_signal(self, chunk: bytes, frame_id: int) -> np.ndarray:
        """Оборачивает кусок данных в защищённый M-FSK пакет с номером кадра."""
        cfg = self.cfg
        header = frame_id.to_bytes(cfg.frame_id_bytes, byteorder='big')
        raw_packet = header + chunk
        protected_data = bytes(self._rs.encode(raw_packet))
        full_data = cfg.preamble + protected_data

        nibbles = []
        for byte in full_data:
            nibbles.append(byte >> 4)
            nibbles.append(byte & 0x0F)

        pad_len = (cfg.k_channels - (len(nibbles) % cfg.k_channels)) % cfg.k_channels
        if pad_len:
            nibbles.extend([0] * pad_len)

        num_symbols = len(nibbles) // cfg.k_channels
        n_samples = int(cfg.fs * cfg.sym_dur)
        t = np.arange(n_samples) / cfg.fs

        fade_len = int(cfg.fs * 0.002)
        window = np.ones(n_samples)
        if fade_len > 0:
            window[:fade_len] = np.linspace(0, 1, fade_len)
            window[-fade_len:] = np.linspace(1, 0, fade_len)

        signal = np.zeros(num_symbols * n_samples, dtype=np.float64)
        for i in range(num_symbols):
            sym_nibbles = nibbles[i * cfg.k_channels:(i + 1) * cfg.k_channels]
            sym_wave = np.zeros(n_samples, dtype=np.float64)
            for k_idx, nib in enumerate(sym_nibbles):
                freq = cfg.f_base + k_idx * cfg.channel_spacing + nib * cfg.tone_step
                sym_wave += np.sin(2 * np.pi * freq * t)
            sym_wave *= window
            signal[i * n_samples:(i + 1) * n_samples] = sym_wave

        max_val = np.max(np.abs(signal))
        if max_val > 0:
            signal = signal / max_val
        return signal

    def encode_large_file(self, input_file_path: str, output_wav_path: str) -> int:
        """
        Разбивает файл на пакеты, первым кадром передаёт размер файла и его
        SHA-256, пишет итоговое аудио в WAV. Возвращает исходный размер файла
        в байтах (0 — при ошибке), как и раньше, для совместимости с main.py.
        """
        cfg = self.cfg
        if not os.path.exists(input_file_path):
            logger.error("Файл %s не найден.", input_file_path)
            return 0

        file_size = os.path.getsize(input_file_path)
        logger.info("Исходный файл: %d байт (~%.1f КБ)", file_size, file_size / 1024)

        max_capacity = ((1 << (cfg.frame_id_bytes * 8)) - 2) * cfg.payload_per_frame
        if file_size > max_capacity:
            logger.error(
                "Файл слишком велик: %d байт > предел протокола %d байт "
                "(frame_id_bytes=%d, payload_per_frame=%d байт).",
                file_size, max_capacity, cfg.frame_id_bytes, cfg.payload_per_frame,
            )
            return 0

        with open(input_file_path, 'rb') as f:
            file_bytes = f.read()
        file_hash = hashlib.sha256(file_bytes).digest()  # 32 байта

        audio_accumulator = [np.zeros(int(cfg.fs * cfg.lead_silence))]  # тишина в начале

        # --- Кадр метаданных (frame_id = 0): размер файла + SHA-256 ---
        meta_chunk = (struct.pack('<Q', file_size) + file_hash).ljust(cfg.payload_per_frame, b'\x00')
        audio_accumulator.append(self.generate_frame_signal(meta_chunk, frame_id=cfg.meta_frame_id))
        audio_accumulator.append(np.zeros(int(cfg.fs * 0.005)))
        logger.info("Кадр метаданных (размер файла + SHA-256) закодирован.")

        # --- Кадры с данными (frame_id = 1, 2, ...) ---
        frame_id = 1
        offset = 0
        total_frames = max(1, (len(file_bytes) + cfg.payload_per_frame - 1) // cfg.payload_per_frame)
        while offset < len(file_bytes):
            chunk = file_bytes[offset:offset + cfg.payload_per_frame]
            if len(chunk) < cfg.payload_per_frame:
                chunk = chunk.ljust(cfg.payload_per_frame, b'\x00')

            audio_accumulator.append(self.generate_frame_signal(chunk, frame_id))
            audio_accumulator.append(np.zeros(int(cfg.fs * cfg.inter_frame_gap)))

            offset += cfg.payload_per_frame
            frame_id += 1
            if frame_id % 50 == 0 or offset >= len(file_bytes):
                logger.info("Сгенерировано пакетов данных: %d / %d", frame_id - 1, total_frames)

        audio_accumulator.append(np.zeros(int(cfg.fs * cfg.lead_silence)))  # тишина в конце

        logger.info("Финализация: сохранение аудио на диск...")
        full_signal = np.concatenate(audio_accumulator)
        full_signal_int16 = (full_signal * 32767 * 0.8).astype(np.int16)

        out_dir = os.path.dirname(output_wav_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)  # ФИКС: раньше падало без существующей папки
        wavfile.write(output_wav_path, cfg.fs, full_signal_int16)

        logger.info(
            "Аудиофайл создан: %s (длительность %.1f сек)",
            output_wav_path, len(full_signal_int16) / cfg.fs,
        )
        return file_size

    # ------------------------------------------------------------------ #
    # Декодирование
    # ------------------------------------------------------------------ #
    def bandpass_filter(self, samples: np.ndarray, fs: int, lowcut: float, highcut: float,
                         order: int = 5) -> np.ndarray:
        """Полосовой фильтр с защитой от падения filtfilt на коротких сигналах."""
        nyq = 0.5 * fs
        safe_order = order
        while safe_order >= 1:
            b, a = scipy.signal.butter(safe_order, [lowcut / nyq, highcut / nyq], btype='band')
            padlen = 3 * max(len(a), len(b))
            if len(samples) > padlen:
                return scipy.signal.filtfilt(b, a, samples)
            safe_order -= 1
        logger.warning(
            "Сигнал слишком короткий для полосового фильтра (%d сэмплов) — фильтрация пропущена.",
            len(samples),
        )
        return samples

    def soft_demodulate(self, samples: np.ndarray, fs: int, sym_dur: float,
                         K_channels: int, freqs: np.ndarray) -> np.ndarray:
        """
        Векторизованная демодуляция: энергия каждого тона для каждого символа
        вычисляется сразу для всей записи через einsum, без Python-цикла
        по символам (это была основная точка замедления в старой версии).
        """
        N = int(fs * sym_dur)
        num_sym = len(samples) // N
        if num_sym == 0:
            return np.zeros((0, K_channels, freqs.shape[1]))

        blocks = samples[:num_sym * N].reshape(num_sym, N)
        cos_ref, sin_ref = self._get_reference_waveforms(N)  # (K, n_tones, N)

        iq_i = np.einsum('sn,ktn->skt', blocks, cos_ref, optimize=True)
        iq_q = np.einsum('sn,ktn->skt', blocks, sin_ref, optimize=True)
        return iq_i ** 2 + iq_q ** 2  # (num_sym, K, n_tones)

    def bytes_to_nibbles(self, bs: bytes) -> np.ndarray:
        seq = []
        for byte in bs:
            seq.extend([byte >> 4, byte & 0x0F])
        return np.array(seq, dtype=int)

    def find_flag_soft(self, soft: np.ndarray, flag_nibbles: np.ndarray, K_channels: int,
                        search_start: int = 0, search_limit: Optional[int] = None) -> int:
        """
        Векторизованный поиск преамбулы (без Python-цикла по стартовым позициям):
        score считается сразу для всего окна кандидатов через numpy.

        search_limit=None => искать до конца доступного сигнала (полный скан,
        используется как fallback, если в ограниченном окне ничего не найдено).
        """
        L = len(flag_nibbles)
        syms_needed = int(np.ceil(L / K_channels))
        num_sym = soft.shape[0]

        max_start = num_sym - syms_needed
        if search_limit is not None:
            max_start = min(max_start, search_start + search_limit)
        if max_start < search_start:
            return -1

        starts = np.arange(search_start, max_start + 1)
        scores = np.zeros(len(starts))

        for off in range(syms_needed):
            sym_idx = starts + off                # (n_starts,)
            block = soft[sym_idx]                  # (n_starts, K, n_tones)
            for k in range(K_channels):
                pos = off * K_channels + k
                if pos < L:
                    nib = flag_nibbles[pos]
                    scores += block[:, k, nib]

        if len(scores) == 0:
            return -1
        best_idx = int(np.argmax(scores))
        return search_start + best_idx

    def decode_large_file_from_samples(self, samples: np.ndarray, output_file_path: str) -> bool:
        """
        Декодирует массив семплов (записанных с микрофона) в файл.

        Возвращает True, если контрольная сумма SHA-256 совпала (файл собран
        корректно), False — если она не совпала или отсутствовала (кадр
        метаданных был потерян и проверить целостность нечем).
        """
        cfg = self.cfg
        t0 = time.time()
        sig = samples.astype(np.float64) / 32768.0

        lowcut = cfg.f_base - 50
        highcut = (cfg.f_base + (cfg.k_channels - 1) * cfg.channel_spacing
                   + (cfg.n_tones - 1) * cfg.tone_step + 50)
        sig = self.bandpass_filter(sig, cfg.fs, lowcut, highcut)

        freqs = self._freqs()
        soft = self.soft_demodulate(sig, cfg.fs, cfg.sym_dur, cfg.k_channels, freqs)

        pre_nib = self.bytes_to_nibbles(cfg.preamble)
        packet_bytes_len = cfg.packet_bytes_len
        packet_nibbles_len = packet_bytes_len * 2
        pad_len_nibbles = (cfg.k_channels - (packet_nibbles_len % cfg.k_channels)) % cfg.k_channels
        total_nibbles_per_packet = packet_nibbles_len + pad_len_nibbles
        syms_per_packet = total_nibbles_per_packet // cfg.k_channels
        pre_syms = int(np.ceil(len(pre_nib) / cfg.k_channels))

        # Ожидаемое расстояние (в символах) до начала следующего кадра.
        gap_syms = int(np.ceil((cfg.inter_frame_gap) / cfg.sym_dur)) + 1
        window_syms = int((pre_syms + syms_per_packet + gap_syms) * cfg.frame_gap_search_margin)

        reconstructed = bytearray()
        expected_frame_id = 1
        extracted_file_size: Optional[int] = None
        expected_hash: Optional[bytes] = None

        logger.info("Начинаем поиск и сборку кадров (символов в записи: %d)...", soft.shape[0])

        current_search_start = 0
        frames_found = 0
        frames_lost = 0

        while True:
            # Сначала быстрый ограниченный поиск рядом с ожидаемой позицией,
            # затем — полный скан как fallback (на случай большого разрыва/тишины).
            rel_start = self.find_flag_soft(
                soft, pre_nib, cfg.k_channels,
                search_start=current_search_start, search_limit=window_syms,
            )
            if rel_start == -1:
                rel_start = self.find_flag_soft(
                    soft, pre_nib, cfg.k_channels,
                    search_start=current_search_start, search_limit=None,
                )
            if rel_start == -1:
                break

            data_start = rel_start + pre_syms
            data_end = data_start + syms_per_packet

            if data_end > soft.shape[0]:
                logger.warning("Обнаружен неполный кадр в конце записи — отбрасываем.")
                break

            nibbles = []
            for sym in range(data_start, data_end):
                for k in range(cfg.k_channels):
                    nibbles.append(int(np.argmax(soft[sym, k])))

            raw_bytes = bytearray()
            for i in range(0, len(nibbles) - 1, 2):
                raw_bytes.append((nibbles[i] << 4) | nibbles[i + 1])

            current_search_start = data_end

            try:
                decoded_packet, _, _ = self._rs.decode(bytes(raw_bytes[:packet_bytes_len]))
                frame_id = int.from_bytes(decoded_packet[:cfg.frame_id_bytes], byteorder='big')
                chunk_data = decoded_packet[cfg.frame_id_bytes:]
            except Exception:
                logger.warning("Ошибка FEC в найденном кадре — пакет отброшен целиком.")
                frames_found += 1
                continue

            if frame_id == cfg.meta_frame_id:
                extracted_file_size = struct.unpack('<Q', chunk_data[:8])[0]
                expected_hash = bytes(chunk_data[8:40])
                logger.info("Метаданные получены: размер файла = %d байт.", extracted_file_size)
                frames_found += 1
                continue

            # --- Валидация последовательности frame_id ---
            if frame_id < expected_frame_id:
                logger.warning(
                    "Повторный/устаревший кадр frame_id=%d (ожидался %d) — игнорируем.",
                    frame_id, expected_frame_id,
                )
                frames_found += 1
                continue

            gap = frame_id - expected_frame_id
            if gap > 0:
                if gap <= cfg.max_frame_id_gap:
                    logger.warning(
                        "Пропущено %d кадр(ов) перед frame_id=%d — заполняем нулями.", gap, frame_id,
                    )
                    reconstructed.extend(b'\x00' * (gap * cfg.payload_per_frame))
                    frames_lost += gap
                else:
                    logger.warning(
                        "Аномальный скачок frame_id (%d -> %d) — похоже на ложное обнаружение "
                        "преамбулы. Кадр отброшен, порядок не сдвигаем.",
                        expected_frame_id, frame_id,
                    )
                    frames_found += 1
                    continue

            reconstructed.extend(chunk_data)
            expected_frame_id = frame_id + 1
            frames_found += 1

            if frames_found % 50 == 0:
                logger.info("Обработано пакетов: %d (потеряно: %d)", frames_found, frames_lost)

        elapsed = time.time() - t0
        logger.info(
            "Поиск завершён: найдено кадров %d, потеряно %d, за %.2f сек.",
            frames_found, frames_lost, elapsed,
        )

        # --- Финальная обрезка и проверка целостности ---
        checksum_ok = False
        if extracted_file_size is not None:
            final_data = bytes(reconstructed[:extracted_file_size])
            if expected_hash is not None:
                actual_hash = hashlib.sha256(final_data).digest()
                checksum_ok = actual_hash == expected_hash
                if checksum_ok:
                    logger.info("Контрольная сумма SHA-256 совпала — файл собран корректно.")
                else:
                    logger.error(
                        "Контрольная сумма SHA-256 НЕ совпала — файл повреждён "
                        "(потерянные и/или незамеченные испорченные кадры)."
                    )
        else:
            logger.warning(
                "Кадр метаданных потерян: размер и SHA-256 неизвестны. "
                "Обрезаем не более одного кадра паддинга нулями с конца, "
                "чтобы не срезать значащие данные."
            )
            trimmed = 0
            while reconstructed and reconstructed[-1] == 0 and trimmed < cfg.payload_per_frame - 1:
                reconstructed.pop()
                trimmed += 1
            final_data = bytes(reconstructed)

        out_dir = os.path.dirname(output_file_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_file_path, 'wb') as f:
            f.write(final_data)

        logger.info("Файл сохранён: %s (%d байт).", output_file_path, len(final_data))
        return checksum_ok
