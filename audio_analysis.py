import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".flac", ".wav", ".ogg", ".opus", ".aac"}
LOSSLESS_CODECS = {"flac", "alac", "wavpack", "ape"}
ANALYSIS_METHOD_VERSION = 2


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _finite_number(value: object) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def resolve_media_binary(name: str) -> str:
    executable_name = f"{name}.exe" if sys.platform == "win32" else name
    configured_dir = str(os.environ.get("IMD_FFMPEG_DIR") or "").strip()
    if configured_dir:
        configured = Path(configured_dir) / executable_name
        if configured.is_file():
            return str(configured)
    roots = [
        Path(str(getattr(sys, "_MEIPASS", "") or ".")),
        Path(sys.executable).resolve().parent,
        Path(__file__).resolve().parent,
    ]
    for root in roots:
        for candidate in (
            root / "vendor" / "ffmpeg" / executable_name,
            root / "_internal" / "vendor" / "ffmpeg" / executable_name,
        ):
            if candidate.is_file():
                return str(candidate)
    discovered = shutil.which(name)
    if discovered:
        return discovered
    raise RuntimeError(f"{name} nao foi encontrado. Reinstale o IMD para restaurar o FFmpeg incluido.")


def _run(command: List[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def probe_audio_file(path: Path, ffprobe: Optional[str] = None) -> Dict[str, Any]:
    command = [
        ffprobe or resolve_media_binary("ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration,bit_rate,format_name:stream=index,codec_type,codec_name,sample_rate,channels,bit_rate",
        "-of",
        "json",
        str(path),
    ]
    completed = _run(command, timeout=60)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "arquivo de audio invalido").strip()
        raise RuntimeError(f"FFprobe nao conseguiu ler o arquivo: {detail[-500:]}")
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("FFprobe retornou metadados invalidos.") from exc

    streams = payload.get("streams") or []
    stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not stream:
        raise RuntimeError("O arquivo nao contem uma faixa de audio reconhecida.")
    format_data = payload.get("format") or {}

    def integer(value: object) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "duration_seconds": _finite_number(format_data.get("duration")),
        "codec": str(stream.get("codec_name") or format_data.get("format_name") or "desconhecido"),
        "container": str(format_data.get("format_name") or ""),
        "sample_rate_hz": integer(stream.get("sample_rate")),
        "channels": integer(stream.get("channels")),
        "bit_rate_bps": integer(stream.get("bit_rate") or format_data.get("bit_rate")),
    }


def _regex_number(pattern: str, text: str) -> Optional[float]:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return _finite_number(match.group(1)) if match else None


def _downsample_timeline(points: List[Dict[str, float]], limit: int) -> List[Dict[str, float]]:
    if len(points) <= limit:
        return points
    if limit <= 1:
        return [points[-1]]
    indexes = {round(index * (len(points) - 1) / (limit - 1)) for index in range(limit)}
    return [points[index] for index in sorted(indexes)]


def parse_ebur128_output(output: str, timeline_limit: int = 160) -> Dict[str, Any]:
    summary = output.rsplit("Summary:", 1)[-1]
    integrated = _regex_number(r"Integrated loudness:\s*.*?\bI:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*LUFS", summary)
    loudness_range = _regex_number(r"Loudness range:\s*.*?\bLRA:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*LU", summary)
    true_peak = _regex_number(r"True peak:\s*.*?\bPeak:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dBFS", summary)

    points: List[Dict[str, float]] = []
    pattern = re.compile(
        r"\bt:\s*(\d+(?:\.\d+)?)\s+TARGET:.*?\bM:\s*(-?(?:inf|\d+(?:\.\d+)?))\s+S:",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(output):
        seconds = _finite_number(match.group(1))
        loudness = _finite_number(match.group(2))
        if seconds is None or loudness is None or loudness < -90:
            continue
        points.append({"seconds": round(seconds, 2), "lufs": round(loudness, 2)})

    return {
        "integrated_lufs": round(integrated, 2) if integrated is not None else None,
        "loudness_range_lu": round(loudness_range, 2) if loudness_range is not None else None,
        "true_peak_dbtp": round(true_peak, 2) if true_peak is not None else None,
        "timeline": _downsample_timeline(points, max(1, timeline_limit)),
    }


def measure_loudness(path: Path, duration_seconds: Optional[float] = None, ffmpeg: Optional[str] = None) -> Dict[str, Any]:
    command = [
        ffmpeg or resolve_media_binary("ffmpeg"),
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-filter:a",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    timeout = max(90, min(900, int((duration_seconds or 0) * 0.75 + 45)))
    completed = _run(command, timeout=timeout)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "falha desconhecida").strip()
        raise RuntimeError(f"FFmpeg nao conseguiu medir o audio: {detail[-700:]}")
    result = parse_ebur128_output(completed.stderr or completed.stdout or "")
    if result["integrated_lufs"] is None and result["true_peak_dbtp"] is None:
        raise RuntimeError("FFmpeg nao retornou medidas de loudness para este arquivo.")
    return result


def _is_lossless(codec: str) -> bool:
    normalized = str(codec or "").lower()
    return normalized in LOSSLESS_CODECS or normalized.startswith("pcm_")


def classify_audio(metrics: Dict[str, Any]) -> Dict[str, Any]:
    score = 100
    critical_issue = False
    medium_cap = False
    strengths: List[str] = []
    reasons: List[str] = []
    recommendations: List[str] = []
    peak = _finite_number(metrics.get("true_peak_dbtp"))
    loudness = _finite_number(metrics.get("integrated_lufs"))
    loudness_range = _finite_number(metrics.get("loudness_range_lu"))
    sample_rate = _finite_number(metrics.get("sample_rate_hz"))
    bit_rate = _finite_number(metrics.get("bit_rate_bps"))
    codec = str(metrics.get("codec") or "")

    if peak is None:
        score -= 5
        reasons.append("Nao foi possivel medir o pico real.")
    elif peak >= 6:
        score -= 15
        medium_cap = True
        reasons.append(f"Pico real muito alto: {peak:.1f} dBTP. Isso pode indicar clipping ou ganho excessivo.")
        recommendations.append("Reduza o ganho e limite o true peak abaixo de -1 dBTP.")
    elif peak >= 3:
        score -= 10
        reasons.append(f"Pico real alto: {peak:.1f} dBTP. Verifique se ha distorcao audivel.")
        recommendations.append("Se houver distorcao, reduza o ganho e limite o true peak abaixo de -1 dBTP.")
    elif peak >= 1:
        score -= 7
        reasons.append(f"Pico real acima do limite digital: {peak:.1f} dBTP.")
        recommendations.append("Use o pico como alerta de masterizacao; ele nao reduz sozinho a qualidade da codificacao.")
    elif peak >= 0:
        score -= 5
        reasons.append(f"Pico real em {peak:.1f} dBTP, no limite digital.")
        recommendations.append("Para maior margem de reproducao, limite o true peak abaixo de -1 dBTP.")
    elif peak > -1:
        score -= 2
        reasons.append(f"Pico real em {peak:.1f} dBTP, muito proximo do limite digital.")
        recommendations.append("Deixe pelo menos 1 dB de margem no true peak.")
    else:
        strengths.append(f"Margem de pico segura: {peak:.1f} dBTP.")

    if loudness is None:
        score -= 10
        medium_cap = True
        reasons.append("Nao foi possivel medir a loudness integrada.")
    elif loudness > -3 or loudness < -35:
        score -= 35
        critical_issue = True
        reasons.append(f"Loudness integrada extrema: {loudness:.1f} LUFS.")
        recommendations.append("Revise ganho, limitacao e normalizacao da faixa.")
    elif loudness > -5 or loudness < -30:
        score -= 20
        medium_cap = True
        reasons.append(f"Loudness bem fora da faixa usual para musica: {loudness:.1f} LUFS.")
    elif loudness < -24:
        score -= 10
        medium_cap = True
        reasons.append(f"Loudness baixa para a maior parte das musicas: {loudness:.1f} LUFS.")
    elif loudness < -20:
        score -= 4
        reasons.append(f"Loudness um pouco baixa, mas ainda utilizavel: {loudness:.1f} LUFS.")
    else:
        strengths.append(f"Loudness dentro da faixa usual para musica: {loudness:.1f} LUFS.")

    if loudness_range is not None:
        if loudness_range < 0.5:
            score -= 12
            medium_cap = True
            reasons.append(f"Faixa dinamica muito baixa: {loudness_range:.1f} LU.")
            recommendations.append("Verifique excesso de compressao ou limitacao.")
        elif loudness_range < 1:
            score -= 6
            medium_cap = True
            reasons.append(f"Faixa dinamica baixa: {loudness_range:.1f} LU.")
        elif loudness_range > 25:
            score -= 8
            reasons.append(f"Faixa dinamica muito ampla: {loudness_range:.1f} LU.")
        else:
            strengths.append(f"Faixa dinamica aproveitavel: {loudness_range:.1f} LU.")

    if sample_rate is not None:
        if sample_rate < 22050:
            score -= 45
            critical_issue = True
            reasons.append(f"Taxa de amostragem muito baixa: {int(sample_rate)} Hz.")
        elif sample_rate < 32000:
            score -= 30
            medium_cap = True
            reasons.append(f"Taxa de amostragem baixa para musica: {int(sample_rate)} Hz.")
        elif sample_rate < 44100:
            score -= 12
            medium_cap = True
            reasons.append(f"Taxa de amostragem abaixo de 44,1 kHz: {int(sample_rate)} Hz.")
        else:
            strengths.append(f"Taxa de amostragem adequada: {sample_rate / 1000:g} kHz.")

    if _is_lossless(codec):
        strengths.append(f"Formato sem perdas: {codec.upper()}.")
    elif bit_rate is not None:
        kbps = bit_rate / 1000
        if kbps < 96:
            score -= 50
            critical_issue = True
            reasons.append(f"Bitrate baixo para musica: {kbps:.0f} kbps.")
            recommendations.append("Procure uma fonte com bitrate maior ou lossless.")
        elif kbps < 128:
            score -= 35
            medium_cap = True
            reasons.append(f"Bitrate baixo para musica: {kbps:.0f} kbps.")
        elif kbps < 160:
            score -= 25
            medium_cap = True
            reasons.append(f"Bitrate limitado: {kbps:.0f} kbps.")
        elif kbps < 192:
            score -= 15
            medium_cap = True
            reasons.append(f"Bitrate moderado: {kbps:.0f} kbps.")
        elif kbps < 256:
            score -= 5
            strengths.append(f"Bitrate adequado: {kbps:.0f} kbps.")
        else:
            strengths.append(f"Bitrate alto: {kbps:.0f} kbps.")

    score = max(0, min(100, score))
    if critical_issue or score < 55:
        rating = "bad"
    elif medium_cap or score < 80:
        rating = "medium"
    else:
        rating = "good"
    labels = {"good": "Boa", "medium": "Média", "bad": "Ruim"}
    return {
        "rating": rating,
        "rating_label": labels[rating],
        "score": score,
        "strengths": strengths,
        "reasons": reasons,
        "recommendations": recommendations,
    }


def analyze_audio_file(path: Path | str, display_name: str = "") -> Dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise RuntimeError("Arquivo de audio nao encontrado.")
    if source.suffix.lower() not in AUDIO_EXTENSIONS:
        raise RuntimeError(f"Formato nao suportado: {source.suffix or 'sem extensao'}.")

    metadata = probe_audio_file(source)
    loudness = measure_loudness(source, metadata.get("duration_seconds"))
    metrics = {**metadata, **loudness}
    classification = classify_audio(metrics)
    return {
        "file": display_name or source.name,
        "extension": source.suffix.lower(),
        "analyzed_at": now_iso(),
        "method_version": ANALYSIS_METHOD_VERSION,
        **classification,
        **metrics,
    }


def iter_audio_files(root: Path | str) -> List[Path]:
    folder = Path(root).resolve()
    if not folder.is_dir():
        return []
    return sorted(
        (path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS),
        key=lambda path: str(path).lower(),
    )


def summarize_results(items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    rows = list(items)
    return {
        "total": len(rows),
        "good": sum(item.get("rating") == "good" for item in rows),
        "medium": sum(item.get("rating") == "medium" for item in rows),
        "bad": sum(item.get("rating") == "bad" for item in rows),
        "errors": sum(bool(item.get("error")) for item in rows),
    }


def write_report(path: Path | str, payload: Dict[str, Any]) -> None:
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)


def analyze_library(root: Path | str, output: Optional[Path | str] = None) -> Dict[str, Any]:
    folder = Path(root).resolve()
    if not folder.is_dir():
        raise RuntimeError(f"Pasta da biblioteca nao encontrada: {folder}")
    files = iter_audio_files(folder)
    print(f"Analise: arquivos={len(files)}", flush=True)
    items: List[Dict[str, Any]] = []
    for index, source in enumerate(files, start=1):
        relative_name = source.relative_to(folder).as_posix()
        print(f"Analisando [{index}/{len(files)}]: {relative_name}", flush=True)
        try:
            result = analyze_audio_file(source, display_name=relative_name)
            print(
                f"Resultado: {result['rating_label']} | score={result['score']} | "
                f"LUFS={result.get('integrated_lufs')} | pico={result.get('true_peak_dbtp')}",
                flush=True,
            )
        except Exception as exc:
            result = {
                "file": relative_name,
                "rating": "bad",
                "rating_label": "Ruim",
                "score": 0,
                "strengths": [],
                "reasons": ["O arquivo nao pode ser analisado."],
                "recommendations": ["Verifique se o arquivo esta integro e em um formato suportado."],
                "error": str(exc),
                "analyzed_at": now_iso(),
                "method_version": ANALYSIS_METHOD_VERSION,
                "timeline": [],
            }
            print(f"Falha: {relative_name} | {exc}", flush=True)
        items.append(result)

    items.sort(key=lambda item: ({"bad": 0, "medium": 1, "good": 2}.get(str(item.get("rating")), 3), str(item.get("file")).lower()))
    counts = summarize_results(items)
    report = {
        "ok": True,
        "generated_at": now_iso(),
        "library": str(folder),
        "method": "EBU R128 via FFmpeg; classificacao tecnica IMD",
        "method_version": ANALYSIS_METHOD_VERSION,
        "counts": counts,
        "items": items,
    }
    if output:
        write_report(output, report)
    print(
        "Analise concluida: "
        f"arquivos={counts['total']} | boas={counts['good']} | medias={counts['medium']} | "
        f"ruins={counts['bad']} | falhas={counts['errors']}",
        flush=True,
    )
    return report


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Analise tecnica de audio do IMD")
    parser.add_argument("--library", required=True, help="Pasta da biblioteca")
    parser.add_argument("--output", required=True, help="Arquivo JSON do relatorio")
    args = parser.parse_args(argv)
    analyze_library(args.library, args.output)


if __name__ == "__main__":
    main()
