import json
from pathlib import Path

import pytest

import audio_analysis


EBUR128_OUTPUT = """
[Parsed_ebur128_0 @ 000001] t: 0.399979 TARGET:-23 LUFS M:-18.0 S:-120.7 I:-18.0 LUFS LRA:0.0 LU FTPK: -2.0 -2.0 dBFS TPK: -2.0 -2.0 dBFS
[Parsed_ebur128_0 @ 000001] t: 1.39998 TARGET:-23 LUFS M:-12.0 S:-15.0 I:-14.0 LUFS LRA:2.0 LU FTPK: -0.8 -1.0 dBFS TPK: -0.8 -1.0 dBFS
[Parsed_ebur128_0 @ 000001] t: 2.39998 TARGET:-23 LUFS M:-14.0 S:-14.2 I:-14.1 LUFS LRA:5.0 LU FTPK: -1.2 -1.0 dBFS TPK: -1.2 -1.0 dBFS
[Parsed_ebur128_0 @ 000001] Summary:

  Integrated loudness:
    I:         -14.1 LUFS
    Threshold: -24.1 LUFS

  Loudness range:
    LRA:         7.2 LU
    Threshold: -34.0 LUFS
    LRA low:   -16.2 LUFS
    LRA high:   -9.0 LUFS

  True peak:
    Peak:       -1.2 dBFS
"""


def healthy_metrics(**overrides):
    metrics = {
        "true_peak_dbtp": -1.2,
        "integrated_lufs": -14.1,
        "loudness_range_lu": 7.2,
        "sample_rate_hz": 44100,
        "bit_rate_bps": 320000,
        "codec": "mp3",
    }
    metrics.update(overrides)
    return metrics


def test_parse_ebur128_output_extracts_levels_and_timeline():
    result = audio_analysis.parse_ebur128_output(EBUR128_OUTPUT, timeline_limit=2)

    assert result["integrated_lufs"] == -14.1
    assert result["loudness_range_lu"] == 7.2
    assert result["true_peak_dbtp"] == -1.2
    assert len(result["timeline"]) == 2
    assert result["timeline"][0] == {"seconds": 0.4, "lufs": -18.0}
    assert result["timeline"][-1] == {"seconds": 2.4, "lufs": -14.0}


def test_classify_audio_returns_good_medium_and_bad_with_reasons():
    good = audio_analysis.classify_audio(healthy_metrics())
    medium = audio_analysis.classify_audio(
        healthy_metrics(true_peak_dbtp=-0.5, bit_rate_bps=128000)
    )
    bad = audio_analysis.classify_audio(
        healthy_metrics(true_peak_dbtp=0.2, integrated_lufs=-4.0, bit_rate_bps=64000)
    )

    assert good["rating"] == "good"
    assert good["rating_label"] == "Boa"
    assert medium["rating"] == "medium"
    assert any("Pico real" in reason for reason in medium["reasons"])
    assert bad["rating"] == "bad"
    assert bad["score"] < medium["score"] < good["score"]


def test_lossless_codec_is_not_penalized_for_reported_low_bitrate():
    result = audio_analysis.classify_audio(healthy_metrics(codec="flac", bit_rate_bps=64000))

    assert result["rating"] == "good"
    assert not any("Bitrate" in reason for reason in result["reasons"])


def test_extremely_flat_dynamics_caps_rating_at_medium():
    result = audio_analysis.classify_audio(healthy_metrics(loudness_range_lu=0.4))

    assert result["rating"] == "medium"
    assert any("dinamica muito baixa" in reason for reason in result["reasons"])


def test_analyze_audio_file_combines_probe_loudness_and_classification(monkeypatch, tmp_path):
    source = tmp_path / "track.mp3"
    source.write_bytes(b"audio")
    monkeypatch.setattr(
        audio_analysis,
        "probe_audio_file",
        lambda path: {
            "duration_seconds": 180.0,
            "codec": "mp3",
            "container": "mp3",
            "sample_rate_hz": 44100,
            "channels": 2,
            "bit_rate_bps": 320000,
        },
    )
    monkeypatch.setattr(
        audio_analysis,
        "measure_loudness",
        lambda path, duration: {
            "integrated_lufs": -14.0,
            "loudness_range_lu": 8.0,
            "true_peak_dbtp": -1.1,
            "timeline": [{"seconds": 1.0, "lufs": -14.0}],
        },
    )

    result = audio_analysis.analyze_audio_file(source, display_name="Album/track.mp3")

    assert result["file"] == "Album/track.mp3"
    assert result["rating"] == "good"
    assert result["duration_seconds"] == 180.0
    assert "path" not in result


def test_analyze_library_keeps_errors_and_writes_atomic_report(monkeypatch, tmp_path):
    library = tmp_path / "music"
    library.mkdir()
    (library / "good.mp3").write_bytes(b"good")
    (library / "broken.flac").write_bytes(b"bad")
    output = tmp_path / "report.json"

    def fake_analyze(path, display_name=""):
        if Path(path).name == "broken.flac":
            raise RuntimeError("arquivo corrompido")
        return {
            "file": display_name,
            "rating": "good",
            "rating_label": "Boa",
            "score": 95,
            "reasons": ["OK"],
            "recommendations": [],
            "timeline": [],
        }

    monkeypatch.setattr(audio_analysis, "analyze_audio_file", fake_analyze)

    report = audio_analysis.analyze_library(library, output)
    saved = json.loads(output.read_text(encoding="utf-8"))

    assert report["counts"] == {"total": 2, "good": 1, "medium": 0, "bad": 1, "errors": 1}
    assert saved["counts"] == report["counts"]
    assert saved["items"][0]["rating"] == "bad"
    assert "corrompido" in saved["items"][0]["error"]
    assert not output.with_name("report.json.tmp").exists()


def test_analyze_audio_file_rejects_unsupported_extension(tmp_path):
    source = tmp_path / "track.txt"
    source.write_text("not audio", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Formato nao suportado"):
        audio_analysis.analyze_audio_file(source)
