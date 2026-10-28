"""Text for the files EU4 reads as Windows-1252 (history, common): what that code page cannot show is flattened."""
import unicodedata


def ascii_(s):
    s = s.translate(str.maketrans({"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ə": "e", "ʻ": "'", "’": "'", "ʼ": "'"}))
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def latin1(s):
    """keep Latin-1 letters, flatten everything else"""
    return "".join(c if ord(c) < 256 else (ascii_(c) or "") for c in s)
