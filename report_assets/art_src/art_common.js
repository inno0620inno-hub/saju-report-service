/* PDF 배경 아트 공용 라이브러리 (Chrome으로 그려 JPG→PDF로 구워 둔다 — 서버에서는 쓰지 않음)
   페이지 크기 220×391.11mm = 832×1478 CSS px (96dpi). 모든 좌표는 이 크기 기준. */
const AW = 832, AH = 1478;
const GOLD_STOPS = [[0, '#fff3c4'], [.5, '#e3bd62'], [1, '#b8892c']];

/* 시드 고정 난수(매번 같은 별자리) */
function rng(seed) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const f1 = n => (+n).toFixed(1);

/* 금박 그라데이션 정의 (userSpaceOnUse: 가로/세로 선에서도 사라지지 않음) */
function defs(id = 'a') {
  return `<defs>
    <linearGradient id="${id}g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="${AH}">${GOLD_STOPS.map(([o, c]) => `<stop offset="${o}" stop-color="${c}"/>`).join('')}</linearGradient>
    <linearGradient id="${id}gh" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="${AW}" y2="0"><stop offset="0" stop-color="#b8892c"/><stop offset=".5" stop-color="#fff3c4"/><stop offset="1" stop-color="#b8892c"/></linearGradient>
    <radialGradient id="${id}glow"><stop offset="0" stop-color="#fff3c4" stop-opacity=".9"/><stop offset=".35" stop-color="#ffd878" stop-opacity=".35"/><stop offset="1" stop-color="#ffd878" stop-opacity="0"/></radialGradient>
    <radialGradient id="${id}vio"><stop offset="0" stop-color="#9a7dff" stop-opacity=".55"/><stop offset="1" stop-color="#9a7dff" stop-opacity="0"/></radialGradient>
    <filter id="${id}blur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>
    <filter id="${id}blur2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
  </defs>`;
}

/* 별밭: 작은 점 + 몇 개의 십자 반짝이.  area=[x,y,w,h], 가운데 글자 영역을 피하려면 avoid=[x,y,w,h] */
function starField({ n = 160, seed = 7, area = [0, 0, AW, AH], avoid = null, alpha = [.18, .8], flares = 8, size = [.5, 1.5] } = {}) {
  const r = rng(seed); let s = '';
  for (let i = 0; i < n; i++) {
    const x = area[0] + r() * area[2], y = area[1] + r() * area[3];
    if (avoid && x > avoid[0] && x < avoid[0] + avoid[2] && y > avoid[1] && y < avoid[1] + avoid[3]) continue;
    const a = alpha[0] + r() * (alpha[1] - alpha[0]), rad = size[0] + r() * (size[1] - size[0]);
    const c = r() < .72 ? '#fff4d0' : (r() < .5 ? '#cbbdff' : '#ffd88a');
    s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(rad)}" fill="${c}" opacity="${a.toFixed(2)}"/>`;
  }
  for (let i = 0; i < flares; i++) {
    const x = area[0] + r() * area[2], y = area[1] + r() * area[3];
    if (avoid && x > avoid[0] && x < avoid[0] + avoid[2] && y > avoid[1] && y < avoid[1] + avoid[3]) continue;
    const L = 5 + r() * 8, a = .5 + r() * .4;
    s += `<g opacity="${a.toFixed(2)}" fill="#fff4d0"><rect x="${f1(x - L)}" y="${f1(y - .5)}" width="${f1(L * 2)}" height="1"/><rect x="${f1(x - .5)}" y="${f1(y - L)}" width="1" height="${f1(L * 2)}"/><circle cx="${f1(x)}" cy="${f1(y)}" r="1.6"/></g>`;
  }
  return s;
}

/* 다이아몬드(마름모) */
const diamond = (cx, cy, w, h, extra = '') => `<path d="M${f1(cx)} ${f1(cy - h / 2)}L${f1(cx + w / 2)} ${f1(cy)}L${f1(cx)} ${f1(cy + h / 2)}L${f1(cx - w / 2)} ${f1(cy)}Z" ${extra}/>`;

/* 면취(모서리 깎은) 사각 테두리 경로 */
function chamfer(x0, y0, x1, y1, c) {
  return `M${x0 + c} ${y0}H${x1 - c}L${x1} ${y0 + c}V${y1 - c}L${x1 - c} ${y1}H${x0 + c}L${x0} ${y1 - c}V${y0 + c}Z`;
}

/* 액자: 이중 금선 + 모서리 부채꼴 문양 + 상하좌우 중앙 장식.  opts.cartouche=true면 하단 중앙에 쪽번호 타원 */
function frameSVG(id, { m1 = 26, m2 = 40, c1 = 26, c2 = 16, cartouche = true, rich = 1 } = {}) {
  const G = `url(#${id}g)`;
  let s = `<g filter="url(#${id}blur)" opacity=".55"><path d="${chamfer(m1, m1, AW - m1, AH - m1, c1)}" fill="none" stroke="${G}" stroke-width="3"/></g>`;
  s += `<path d="${chamfer(m1, m1, AW - m1, AH - m1, c1)}" fill="none" stroke="${G}" stroke-width="2.4"/>`;
  s += `<path d="${chamfer(m2, m2, AW - m2, AH - m2, c2)}" fill="none" stroke="${G}" stroke-width="1" opacity=".8"/>`;
  // 구슬 띠: 바깥선과 안쪽선 사이를 작은 점으로 잇는다(모서리·중앙 장식 구간은 위에서 덮음)
  const bead = (m1 + m2) / 2;
  s += `<path d="${chamfer(bead, bead, AW - bead, AH - bead, (c1 + c2) / 2)}" fill="none" stroke="${G}" stroke-width="2" stroke-dasharray="0.1 11" stroke-linecap="round" opacity=".7"/>`;
  s += `<path d="${chamfer(m1 - 9, m1 - 9, AW - m1 + 9, AH - m1 + 9, c1 + 6)}" fill="none" stroke="${G}" stroke-width=".7" opacity=".45"/>`;   // 가장 바깥 헤어라인
  // 모서리 문양 (좌상단 기준을 만들어 4방향 복제): 연꽃잎 부채 + 호 + 마름모
  const corner = (() => {
    let g = '';
    const ox = m2 + 4, oy = m2 + 4;                       // 부채의 중심(안쪽 프레임 모서리 안쪽)
    const petal = (len, wid) => `M0 0C${f1(len * .3)} ${f1(-wid)} ${f1(len * .78)} ${f1(-wid * .9)} ${f1(len)} 0C${f1(len * .78)} ${f1(wid * .9)} ${f1(len * .3)} ${f1(wid)} 0 0Z`;
    [[0, 62], [22.5, 50], [45, 68], [67.5, 50], [90, 62]].forEach(([deg, len], i) => {
      g += `<path d="${petal(len, 9)}" transform="translate(${ox} ${oy}) rotate(${deg})" fill="rgba(212,175,90,${i === 2 ? .22 : .12})" stroke="${G}" stroke-width="${i === 2 ? 1.5 : 1}" opacity="${i === 2 ? 1 : .85}"/>`;
      g += `<circle cx="${f1(ox + Math.cos(deg * Math.PI / 180) * (len + 6))}" cy="${f1(oy + Math.sin(deg * Math.PI / 180) * (len + 6))}" r="${i === 2 ? 2.6 : 1.8}" fill="${G}"/>`;
    });
    [[16, 1.4, 1], [28, .9, .75], [40, .7, .5]].forEach(([r, w, o]) => {     // 부채 중심 둘레의 동심호(남→동, 반시계)
      g += `<path d="M${ox} ${oy + r}A${r} ${r} 0 0 0 ${ox + r} ${oy}" fill="none" stroke="${G}" stroke-width="${w}" opacity="${o}"/>`;
    });
    g += diamond(m1 + 5, m1 + 5, 17, 17, `fill="${G}"`);   // 바깥 모서리 마름모
    g += diamond(m1 + 5, m1 + 5, 7, 7, 'fill="#1a0f33"');
    g += `<circle cx="${ox}" cy="${oy}" r="4.2" fill="${G}"/><circle cx="${ox}" cy="${oy}" r="1.8" fill="#1a0f33"/>`;
    return g;
  })();
  const flip = [['', 'TL'], [`translate(${AW} 0) scale(-1 1)`, 'TR'], [`translate(${AW} ${AH}) scale(-1 -1)`, 'BR'], [`translate(0 ${AH}) scale(1 -1)`, 'BL']];
  flip.forEach(([t]) => { s += `<g ${t ? `transform="${t}"` : ''}>${corner}</g>`; });
  // 변 중앙 장식
  const mid = (cx, cy, rot) => {
    let g = `<g transform="rotate(${rot} ${cx} ${cy})">`;
    g += `<rect x="${cx - 70}" y="${cy - 5}" width="140" height="10" fill="#07040f"/>`;                       // 선을 끊는 바탕
    g += diamond(cx, cy, 26, 26, `fill="none" stroke="${G}" stroke-width="1.6"`);
    g += diamond(cx, cy, 12, 12, `fill="${G}"`);
    [-1, 1].forEach(d => {
      g += diamond(cx + d * 30, cy, 8, 8, `fill="${G}"`);
      g += `<line x1="${cx + d * 38}" y1="${cy}" x2="${cx + d * 66}" y2="${cy}" stroke="${G}" stroke-width="1.2"/>`;
      g += `<circle cx="${cx + d * 70}" cy="${cy}" r="2" fill="${G}"/>`;
    });
    return g + '</g>';
  };
  s += mid(AW / 2, m1, 0);
  s += `<g transform="rotate(180 ${AW / 2} ${AH / 2})">${''}</g>`;
  if (!cartouche) s += mid(AW / 2, AH - m1, 0);
  const side = (cx, cy) => diamond(cx, cy, 14, 14, `fill="none" stroke="${G}" stroke-width="1.4"`) + diamond(cx, cy, 5, 5, `fill="${G}"`);
  s += side(m1, AH / 2) + side(AW - m1, AH / 2);
  if (cartouche) {                                         // 하단 중앙: 쪽번호 타원 (번호는 글자 층이 찍는다)
    const cx = AW / 2, cy = AH - m1, w = 92, h = 34;
    s += `<rect x="${cx - 120}" y="${cy - 6}" width="240" height="12" fill="#07040f"/>`;
    s += `<rect x="${cx - w / 2}" y="${cy - h / 2}" width="${w}" height="${h}" rx="${h / 2}" fill="#10091f" stroke="${G}" stroke-width="1.8"/>`;
    s += `<rect x="${cx - w / 2 + 5}" y="${cy - h / 2 + 5}" width="${w - 10}" height="${h - 10}" rx="${(h - 10) / 2}" fill="none" stroke="${G}" stroke-width=".7" opacity=".7"/>`;
    [-1, 1].forEach(d => {
      s += diamond(cx + d * (w / 2 + 16), cy, 9, 9, `fill="${G}"`);
      s += `<line x1="${cx + d * (w / 2 + 24)}" y1="${cy}" x2="${cx + d * (w / 2 + 70)}" y2="${cy}" stroke="${G}" stroke-width="1.2"/>`;
      s += `<circle cx="${cx + d * (w / 2 + 75)}" cy="${cy}" r="2" fill="${G}"/>`;
    });
  }
  return s;
}

/* ===== 마법진 (웹 신청 폼과 같은 구성: 12지·8괘·오행 상생 오각형+상극 오각별·중심 글자) ===== */
const ELEM = [['木', '#6fd37c'], ['火', '#ff7a45'], ['土', '#e9c24d'], ['金', '#e8edf5'], ['水', '#5fb4ff']];
const TRI = [[1,1,1],[0,1,1],[1,0,1],[0,0,1],[1,1,0],[0,1,0],[1,0,0],[0,0,0]];
const BRANCH = [...'子丑寅卯辰巳午未申酉戌亥'];
const pol = (cx, cy, r, d) => { const a = (d - 90) * Math.PI / 180; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
/* 지름 D(px)인 마법진을 (cx,cy)에 그린다. 400단위 좌표계를 scale로 키움 */
function magicCircle(id, cx, cy, D, { glyph = '', orbs = true, text = true, core = true, alpha = 1, glow = false } = {}) {
  const k = D / 400, G = `url(#${id}g)`;
  const P = (r, d) => pol(200, 200, r, d);
  let b = '';
  const ring = (r, w, o = 1) => `<circle cx="200" cy="200" r="${r}" fill="none" stroke="${G}" stroke-width="${w}" opacity="${o}"/>`;
  b += ring(188, 1.8) + ring(182, .7, .8) + ring(150, 1.3) + ring(145, .6, .8) + ring(130, .9) + ring(100, 1.4) + ring(95, .6, .8);
  const per = 2 * Math.PI * 174 / 72;
  b += `<circle cx="200" cy="200" r="174" fill="none" stroke="${G}" stroke-width="3" stroke-dasharray="1.4 ${(per - 1.4).toFixed(2)}" opacity=".85"/>`;
  BRANCH.forEach((c, i) => {
    const [x, y] = P(162, i * 30), [dx, dy] = P(162, i * 30 + 15);
    if (text) b += `<text x="${f1(x)}" y="${f1(y)}" dy=".35em" text-anchor="middle" font-size="15" font-weight="700" font-family="'Noto Serif KR',serif" fill="${G}" transform="rotate(${i * 30} ${f1(x)} ${f1(y)})">${c}</text>`;
    b += `<path d="M${f1(dx)} ${f1(dy - 5)}l3.2 5-3.2 5-3.2-5z" fill="${G}" transform="rotate(${i * 30 + 15} ${f1(dx)} ${f1(dy)})"/>`;
  });
  TRI.forEach((t, i) => {
    let g = '';
    t.forEach((yang, kk) => {
      const y = 78 + kk * 6.5;
      g += yang ? `<rect x="188" y="${y}" width="24" height="2.8" rx="1.4" fill="${G}"/>`
                : `<rect x="188" y="${y}" width="10" height="2.8" rx="1.4" fill="${G}"/><rect x="202" y="${y}" width="10" height="2.8" rx="1.4" fill="${G}"/>`;
    });
    b += `<g transform="rotate(${i * 45} 200 200)">${g}</g>`;
    const [x, y] = P(130, i * 45 + 22.5); b += `<circle cx="${f1(x)}" cy="${f1(y)}" r="2.2" fill="${G}"/>`;
  });
  if (orbs) {
    const V = ELEM.map((_, i) => P(80, i * 72));
    const path = ks => ks.map((q, j) => `${j ? 'L' : 'M'}${f1(V[q][0])} ${f1(V[q][1])}`).join('') + 'Z';
    b += `<path d="${path([0,1,2,3,4])}" fill="none" stroke="${G}" stroke-width="1.1" opacity=".75"/><path d="${path([0,2,4,1,3])}" fill="none" stroke="${G}" stroke-width="1.5"/>`;
    ELEM.forEach(([kk, c], i) => {
      const [x, y] = V[i];
      b += `<circle cx="${f1(x)}" cy="${f1(y)}" r="15" fill="#0a0714" stroke="${c}" stroke-width="1.6"/><circle cx="${f1(x)}" cy="${f1(y)}" r="15" fill="${c}" opacity=".18"/>`;
      if (text) b += `<text x="${f1(x)}" y="${f1(y)}" dy=".35em" text-anchor="middle" font-size="15" font-weight="700" font-family="'Noto Serif KR',serif" fill="${c}">${kk}</text>`;
    });
  }
  if (core) {
    b += `<circle cx="200" cy="200" r="46" fill="rgba(10,6,24,.86)" stroke="${G}" stroke-width="1.6"/><circle cx="200" cy="200" r="40" fill="none" stroke="${G}" stroke-width=".7"/>`;
    if (glyph) b += `<text x="200" y="200" dy=".36em" text-anchor="middle" font-size="46" font-weight="900" font-family="'Noto Serif KR',serif" fill="${G}">${glyph}</text>`;
  }
  const g = `<g transform="translate(${f1(cx - D / 2)} ${f1(cy - D / 2)}) scale(${k.toFixed(4)})" opacity="${alpha}">${b}</g>`;
  return glow ? `<g filter="url(#${id}blur2)" opacity=".55">${g}</g>${g}` : g;       // glow: 같은 그림을 흐리게 한 번 더 깔아 빛 번짐
}

/* 떠다니는 금빛·보랏빛 빛망울(보케) */
function bokeh({ n = 18, seed = 3, area = [0, 0, AW, AH], r = [6, 24], alpha = [.05, .16], avoid = null } = {}) {
  const rg = rng(seed); let s = '';
  for (let i = 0; i < n; i++) {
    const x = area[0] + rg() * area[2], y = area[1] + rg() * area[3], rad = r[0] + rg() * (r[1] - r[0]);
    if (avoid && x > avoid[0] && x < avoid[0] + avoid[2] && y > avoid[1] && y < avoid[1] + avoid[3]) continue;
    const gold = rg() < .66;
    s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(rad)}" fill="${gold ? '#ffd27a' : '#9a7dff'}" opacity="${(alpha[0] + rg() * (alpha[1] - alpha[0])).toFixed(3)}" filter="url(#zblur)"/>`;
  }
  return s;
}

/* 페이지 바탕 CSS(보라 비네트 + 은은한 세로 줄무늬) */
function pageBG(extra = '', stripes = true) {
  return `background:
    ${extra}
    radial-gradient(90% 38% at 50% -4%, rgba(86,52,196,.34), transparent 70%),
    radial-gradient(80% 30% at 50% 104%, rgba(168,118,40,.20), transparent 70%),
    radial-gradient(120% 90% at 50% 50%, transparent 55%, rgba(0,0,0,.45) 100%),
    ${stripes ? 'repeating-linear-gradient(90deg, rgba(255,255,255,.022) 0 1px, transparent 1px 9px),' : ''}
    #07040f;`;
}
