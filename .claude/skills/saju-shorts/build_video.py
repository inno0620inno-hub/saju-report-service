"""사주쇼츠 한 편 조립: python -I build_video.py <workdir> <hook.jpg> <config.json> <out.mp4>
workdir/tts/0.mp3..N.mp3 (0=후킹, 1..N-2=장면, N-1=엔딩). 무음 렌더 → 음성+BGM+딩 믹스. 길이 60초 미만 검사."""
import sys, os, subprocess, random, glob, json
W, HOOK, CFG, OUT = sys.argv[1:5]
HERE = os.path.dirname(os.path.abspath(__file__))
n = len(glob.glob(f"{W}/tts/[0-9]*.mp3"))
def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())
d = [dur(f"{W}/tts/{i}.mp3") for i in range(n)]
open(f"{W}/tts/dur.txt", "w").write(" ".join(map(str, d)))
sil = OUT + ".silent.mp4"
subprocess.run(["python", "-I", f"{HERE}/saju_short.py", W, sil, HOOK, CFG], check=True)
G = 0.4
starts = [0.0]
for i in range(n - 1): starts.append(starts[-1] + d[i] + G)
total = starts[-1] + d[-1] + 0.9
if total >= 59: print("WARNING: 59초 이상!", total)
bgms = sorted(glob.glob("C:/Users/hyeji/Downloads/쇼핑쇼츠/bgm/*.mp3"))
bgm = random.choice(bgms)
inp = []
for i in range(n): inp += ["-i", f"{W}/tts/{i}.mp3"]
inp += ["-stream_loop", "-1", "-i", bgm, "-i", sil]
fc = []
for i in range(n): fc.append(f"[{i}:a]adelay={int(starts[i]*1000)}|{int(starts[i]*1000)}[v{i}]")
for k, st in enumerate(starts[1:n]):
    ms = int(max(0, st - 0.05) * 1000)
    fc.append(f"sine=f=1568:d=0.35,afade=t=out:st=0.05:d=0.3,volume=0.35,adelay={ms}|{ms}[s{k}]")
fc.append("[%d:a]volume=0.12,atrim=0:%.2f,afade=t=out:st=%.2f:d=1.7[bg]" % (n, total, total - 1.7))
mix = "".join(f"[v{i}]" for i in range(n)) + "".join(f"[s{k}]" for k in range(n - 1)) + "[bg]"
fc.append(f"{mix}amix=inputs={2*n}:normalize=0:duration=longest,atrim=0:{total:.2f}[aout]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", f"{n+1}:v", "-map", "[aout]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], check=True)
os.remove(sil)
print("done", OUT, "len", dur(OUT), "bgm", os.path.basename(bgm))
