import sys, os, subprocess, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
S = sys.argv[1]; OUT = sys.argv[2]
CFG = json.load(open(sys.argv[4],encoding='utf-8'))
W, H, FPS = 1080, 1920, 24
FB = "C:/Windows/Fonts/malgunbd.ttf"; FS = "C:/Windows/Fonts/batang.ttc"
GOLD = (236, 195, 90); GOLD2 = (214, 170, 58); CREAM = (240, 232, 212)
F = lambda p, s: ImageFont.truetype(p, s)
src = Image.open(sys.argv[3]).convert("RGB")
sw, sh = src.size; ch = int(sw * 429 / 1080); cy = int(sh * CFG.get('crop_y', 0.305))
top = src.crop((0, cy - ch // 2, sw, cy - ch // 2 + ch)).resize((1080, 429), Image.LANCZOS)

def ctext(d, t, size, y, fill, stroke=0, font=FB, x=W / 2):
    f = F(font, size); w = d.textlength(t, font=f)
    d.text((x - w / 2, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))

base = Image.new("RGB", (W, H), (10, 9, 8)); d = ImageDraw.Draw(base)
for x in range(0, W, 26): d.rectangle([x, 0, x + 1, H], fill=(18, 16, 13))
base.paste(top, (0, 0))
g = Image.new("L", (1080, 429), 0); gd = ImageDraw.Draw(g)
for y in range(429): gd.line([0, y, 1080, y], fill=int(max(0, (y - 150) / 279) ** 1.2 * 235))
base.paste(Image.new("RGB", (1080, 429), (0, 0, 0)), (0, 0), g); d = ImageDraw.Draw(base)
_ts=CFG.get("title_size",76)
ctext(d, CFG["title"], _ts, 258, GOLD, 5)
ctext(d, CFG["subtitle"], 38, 352, CREAM, 3)
d.line([0, 429, 1080, 429], fill=GOLD2, width=3)
BX = (42, 436, 1052, 1856); BW, BH = BX[2] - BX[0] - 6, BX[3] - BX[1] - 6
ctext(d, "금빛사주명식.store · 프로필 링크", 32, 1868, GOLD2)

import glob,os
DL="C:/Users/hyeji/Downloads/"
def bg(key):
    f=max(glob.glob(DL+key+"*.jpg"),key=os.path.getsize)
    im=Image.open(f).convert("RGB")
    r=BW/im.width; im=im.resize((BW,int(im.height*r)+1),Image.LANCZOS)
    canvas=Image.new("RGB",(BW,BH),(8,7,5)); canvas.paste(im,(0,70))
    m=Image.new("L",(BW,BH),0); md=ImageDraw.Draw(m)
    for y in range(BH): md.line([0,y,BW,y],fill=int(max(0,(y-1010)/(BH-1010))**0.8*245))
    canvas.paste(Image.new("RGB",(BW,BH),(8,7,5)),(0,0),m)
    return canvas

segs = [tuple(x) for x in CFG["segs"]]
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", OUT], stdin=subprocess.PIPE)
ease = lambda t: 1 - (1 - min(1, max(0, t))) ** 3
DUR=[float(x) for x in open(f"{S}/tts/dur.txt").read().split()]
GAP=0.4
# intro: collage of 5 mascots
tiles=[bg(k) for *_,k in segs[:5]]
def collage(t):
    c=Image.new("RGB",(BW,BH),(8,7,5))
    pos=[(0,0),(BW//2,0),(0,BH//3),(BW//2,BH//3),(BW//4,2*BH//3-40)]
    for (x,y),tl in zip(pos,tiles):
        th=tl.resize((BW//2,int(BH/2*0.62)))
        c.paste(th.crop((0,0,BW//2,BH//3)),(x,y))
    return c
CO=collage(0)
nI=int((DUR[0]+GAP)*FPS)
for i in range(nI):
    t=i/FPS
    fr=base.copy();fr.paste(CO,(BX[0]+3,BX[1]+3));dd=ImageDraw.Draw(fr)
    dd.rounded_rectangle([140,1130,940,1420],20,fill=(8,7,5),outline=GOLD2,width=4)
    ctext(dd,CFG.get("intro1","1위는 의외입니다"),88,1170,GOLD,6)
    ctext(dd,CFG.get("intro2","끝까지 보세요"),54,1300,(255,255,255),4)
    p.stdin.write(fr.tobytes())
for si,(rank, name, hanja, el, lines, bgn) in enumerate(segs):
    B = bg(bgn); n=int((DUR[si+1]+GAP)*FPS)
    for i in range(n):
        t = i / FPS
        fr = base.copy(); fr.paste(B, (BX[0] + 3, BX[1] + 3)); d = ImageDraw.Draw(fr)
        ox, oy = BX[0] + 3, BX[1] + 3
        # rank numeral
        a = ease(t / 0.35)
        if rank:
            d.text((ox + 40, oy + 20 - (1 - a) * 40), str(rank), font=F(FB, 190), fill=GOLD, stroke_width=6, stroke_fill=(0, 0, 0))
            d.text((ox + 40 + 112, oy + 100), "위", font=F(FB, 68), fill=CREAM, stroke_width=4, stroke_fill=(0, 0, 0))
        else:
            d.text((ox + 36, oy + 40 - (1 - a) * 40), CFG.get("badge", ""), font=F(FB, 64), fill=GOLD, stroke_width=5, stroke_fill=(0, 0, 0))
        # name + hanja chip (top right)
        nm=F(FB,96); nw=d.textlength(name,font=nm)
        right=ox+BW-40; ny=oy+30
        d.text((right-nw,ny),name,font=nm,fill=(255,255,255),stroke_width=7,stroke_fill=(0,0,0))
        cr=48; ccx=right-nw-30-cr; ccy=ny+62
        d.ellipse([ccx-cr,ccy-cr,ccx+cr,ccy+cr],fill=(12,10,6),outline=GOLD,width=4)
        hf=F(FS,66); hw=d.textlength(hanja,font=hf); d.text((ccx-hw/2,ccy-44),hanja,font=hf,fill=GOLD)
        ef=F(FB,36); ew=d.textlength(el+" 기운",font=ef); d.text((right-ew,ny+120),el+" 기운",font=ef,fill=GOLD,stroke_width=2,stroke_fill=(0,0,0))
        # reasoning panel
        pa = ease((t - 0.35) / 0.4)
        panel = Image.new("RGBA", (W, H), (0, 0, 0, 0)); pd = ImageDraw.Draw(panel)
        py = oy + 1090 + int((1 - pa) * 60)
        pd.rounded_rectangle([ox + 30, py, ox + BW - 30, py + 300], 18, fill=(10, 8, 5, int(225 * pa)), outline=GOLD2 + (int(255 * pa),), width=3)
        fr.paste(panel, (0, 0), panel); d = ImageDraw.Draw(fr)
        if pa > 0.05:
            for j, ln in enumerate(lines):
                f = F(FB, 46); w = d.textlength(ln, font=f)
                sz = 46 if w < BW - 130 else int(46 * (BW - 130) / w)
                f = F(FB, sz); w = d.textlength(ln, font=f)
                col = (255, 255, 255) if j == 0 else CREAM
                im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); idr = ImageDraw.Draw(im)
                idr.text((W / 2 - w / 2, py + 52 + j * 106), ln, font=f, fill=col + (int(255 * pa),))
                fr.paste(im, (0, 0), im); d = ImageDraw.Draw(fr)
        p.stdin.write(fr.tobytes())
# end card
end = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"dosa_v2.jpg")).convert("RGB"); r = max(BW / end.width, BH / end.height); end = end.resize((int(end.width * r) + 1, int(end.height * r) + 1))
l = (end.width - BW) // 2; tp = (end.height - BH) // 2; ec = end.crop((l, tp, l + BW, tp + BH))
m = Image.new("L", (BW, BH), 0); md = ImageDraw.Draw(m)
for y in range(BH): md.line([0, y, BW, y], fill=int(max(0, (y - 650) / (BH - 650)) * 235))
for i in range(int((DUR[6]+0.9) * FPS)):
    fr = base.copy(); fr.paste(ec, (BX[0] + 3, BX[1] + 3)); fr.paste(Image.new("RGB", (BW, BH), (0, 0, 0)), (BX[0] + 3, BX[1] + 3), m); d = ImageDraw.Draw(fr)
    ctext(d, CFG.get("end1","내 진짜 순위는?"), 84, 1330, GOLD, 5)
    ctext(d, CFG.get("end2","띠는 연도만 봐요. 태어난 시까지 넣으면 달라집니다"), 36, 1448, CREAM, 3)
    d.rounded_rectangle([190, 1530, 890, 1670], 14, fill=GOLD2); ctext(d, "내 사주 보러 가기 ▶", 56, 1560, (26, 20, 5))
    ctext(d, "프로필 링크 · 금빛사주명식.store", 34, 1710, CREAM, 2)
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait(); print("done")
