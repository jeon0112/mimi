---
name: scroll-video-landing
description: Build an Apple-style interactive scroll-scrubbing product landing page, where a hero video's frames are mapped to scroll position so the product animates as the user scrolls. Use when the user asks for a "스크롤하면 제품이 움직이는" landing page, a scroll-scrub / scroll-scrubbing hero, an interactive product landing page, or references this exact workflow (product interview → reference image → storyboard/콘티 → credit estimate → hero video → frame extraction + build).
---

# 스크롤 스크럽 인터랙티브 랜딩 페이지

출처: https://youtu.be/_gY2J0_gP4Q (클로드 코드 + Higgsfield로 애플 스타일 인터랙티브 히어로 만들기)

## 핵심 원리

영상 하나(보통 5~8초)를 100~150장의 정지 이미지 프레임으로 쪼갠 뒤, 사용자의 스크롤 위치(0~100%)를 프레임 번호에 실시간으로 매핑한다. 사용자는 그냥 스크롤을 내릴 뿐인데, 화면에서는 제품이 회전하거나 열리거나 클로즈업되는 것처럼 보인다. 이걸 "스크롤 스크럽(scroll scrub)"이라 부른다 — 영상 편집 타임라인을 손가락으로 문지르는(scrub) 것을 스크롤로 재현하는 것.

이 스킬은 이미지/영상을 직접 생성하지 못한다 (Claude는 텍스트·코드 모델). 연결된 이미지/영상 생성 도구(예: Higgsfield MCP)와 `ffmpeg`(프레임 추출)이 반드시 필요하다. 세션에 해당 도구가 없으면, 사용자에게 먼저 알리고 어떻게 연결할지 안내한다.

## 언제 이 스킬을 쓰나

- "스크롤하면 제품이 움직이는/살아있는 랜딩페이지 만들어줘"
- "애플 스타일 인터랙티브 히어로"
- "스크롤 스크럽 웹사이트"
- 사용자가 이 스킬의 6단계 워크플로우(제품 인터뷰 → 레퍼런스 → 콘티 → 크레딧 견적 → 영상 → 프레임/빌드)를 언급

## 진행 원칙

**절대 한 번에 다 만들지 않는다.** "멋진 인터랙티브 랜딩페이지 만들어줘" 한 마디에 바로 영상부터 생성하지 말 것 — 결과가 복불복이 되고, 특히 영상 생성은 비용이 커서 실패하면 낭비가 크다. 아래 6단계를 순서대로 밟고, **3단계(콘티)까지는 반드시 사용자 컨펌을 받은 뒤에만 4단계 이상으로 진행한다.**

### 0단계 — 실제 제품인가 가상 제품인가

가장 먼저 확인한다. 실제 제품이면 사진(정면/측면/디테일, 한 장이라도 가능)을 요청한다. 가상 제품(컨셉/데모용)이면 사진 없이 텍스트 정보로 시작한다.

### 1단계 — 제품 정보 인터뷰

대화형으로, 한 번에 몰아 묻지 말고 순서대로:
1. 브랜드명 + 한 줄 소개
2. (실제 제품) 제품 사진 / (가상 제품) 카테고리 + 컨셉
3. 무드·톤 — **추상적인 답("밝은 느낌")에 만족하지 말고 구체화를 유도한다.** "노을 지는 스튜디오, 대리석 바닥" 처럼 시간대·장소·재질까지 구체적으로 나오게 되물어라. 추상적인 지시는 결과가 랜덤해지고 토큰도 낭비된다.
4. 스펙 (제품 상세 정보)
5. 가격
6. 브랜드 컬러 / 전체 디자인 시스템에 쓸 색상

이 단계가 중요한 이유: 이후 만들어지는 레퍼런스 이미지·영상·웹사이트 카피가 전부 이 정보로 통일된 브랜딩을 가져야 하기 때문이다.

### 2단계 — 레퍼런스 이미지 제작

생성 도구로 제품 레퍼런스 이미지를 만든다. 이 이미지가 이후 모든 영상·정적 이미지의 기준(비주얼 앵커)이 된다. 제품이 여러 각도/상태로 등장할 예정이면(예: 케이스+이어폰, 이어폰 단독) 앵글별로 2장 이상 요청하는 것이 좋다 — 하나만 만들면 이후 생성물에서 제품 디테일이 미묘하게 달라지는 경우가 있다.

### 3단계 — 콘티(스토리보드) 확정 — 반드시 영상 생성 전에

바로 영상으로 가지 말고 4~6컷짜리 콘티를 먼저 만화 형태로 제시한다. 각 컷을 스크롤 진행률에 매핑한다 (예: 0% / 15% / 35% / 60% / 85% / 100%). 영상 생성은 비용이 들고, 마음에 안 들어 재생성하면 그 비용이 또 들기 때문에 — 이 단계에서 최대한 자세히 사용자 피드백을 받고 컨펌될 때까지 반복한다.

**알려진 실패 패턴 — 콘티에 넣을 때 사용자에게 미리 경고하거나 대안을 제안할 것:**

| 시도 | 문제 | 대안 |
|---|---|---|
| 360도 풀 회전 | 이음새에서 끊기는 경우가 많음(원테이크가 잘 안 됨) | 180도 이하로 제한하거나, 회전 대신 카메라 무빙 사용 |
| 제품 분해/재조립(특히 전자제품) | AI가 내부 부품을 상상으로 채워 넣어 부자연스럽고 부품이 중간에 사라지기도 함 | 피하거나, "실험적 시도이고 실패 가능성이 있다"고 미리 고지 후 진행 |
| 추상적 지시("밝은 분위기로") | 해석이 랜덤해지고 결과 일관성이 떨어짐 | 항상 구체적 디테일(시간대, 장소, 조명, 재질)로 지시 |
| "넣지 말아야 할 것"을 안 정함 | 할루시네이션으로 요청하지 않은 요소가 들어감 | 매 생성마다 금지 요소도 명시적으로 물어보고 반영 |

### 4단계 — 크레딧/비용 견적

영상을 실제로 생성하기 **전에** 반드시 예상 크레딧/비용을 사용자에게 알리고 진행 여부를 확인받는다. 필요한 것들을 목록으로 정리해서 보여준다 (레퍼런스 이미지 N장, 콘티, 정적 이미지 N장, 히어로 영상). 모델 옵션이 여러 개면(저가/중가/프리미엄) 비용과 품질 트레이드오프를 설명하고 선택하게 한다 — 일반적으로 프리미엄 모델일수록 품질이 좋지만 비싸다.

### 5단계 — 히어로 영상 생성

원테이크로 요청한다. 실패하면(끊김, 부자연스러움, 원치 않는 컷) 영상을 계속 재생성하기보다 **3단계 콘티로 돌아가 더 단순하고 구체적인 시나리오로 수정**한 뒤 재생성하는 편이 낭비를 줄인다.

### 6단계 — 프레임 추출 + 웹사이트 빌드

1. `ffmpeg`로 영상을 프레임 시퀀스로 추출한다. 목표는 보통 영상 길이 기준 100~150장.
   ```bash
   # 8초 영상 → 약 15fps로 추출하면 120장
   ffmpeg -i hero.mp4 -vf "fps=15,scale=1600:-1" -q:v 3 frames/frame_%04d.jpg
   ```
2. 웹사이트는 4개 섹션으로 구성한다: **히어로(스크롤 스크럽)** → **특징/스펙** → **가격** → **CTA**. (이 섹션 구성은 기본값이며, 실제 제품/맥락에 맞게 유연하게 바꿔도 된다.)
3. 히어로는 스크롤 가능한 긴 높이의 래퍼 안에 `position: sticky` 캔버스를 넣는 구조로 만든다 — 캔버스 자체가 화면에 고정된 채, 감싸는 wrapper를 스크롤하는 만큼 프레임이 넘어간다:
   ```html
   <section id="scrollTrack" style="height: 400vh; position: relative;">
     <div style="position: sticky; top: 0; height: 100vh; overflow: hidden;">
       <canvas id="heroCanvas"></canvas>
       <div class="hero-text-overlay">브랜드명 / 한 줄 카피</div>
     </div>
   </section>
   ```
4. 스크롤 위치 → 프레임 인덱스 매핑 (핵심 로직):
   ```js
   const frameCount = 120;
   const canvas = document.getElementById('heroCanvas');
   const ctx = canvas.getContext('2d');
   const images = Array.from({ length: frameCount }, (_, i) => {
     const img = new Image();
     img.src = `frames/frame_${String(i + 1).padStart(4, '0')}.jpg`;
     return img;
   });

   function render(index) {
     const img = images[index];
     if (img.complete) ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
   }

   function onScroll() {
     const track = document.getElementById('scrollTrack');
     const rect = track.getBoundingClientRect();
     const scrollable = track.offsetHeight - window.innerHeight;
     const progress = Math.min(Math.max(-rect.top / scrollable, 0), 1);
     const frameIndex = Math.min(frameCount - 1, Math.floor(progress * frameCount));
     requestAnimationFrame(() => render(frameIndex));
   }
   window.addEventListener('scroll', onScroll, { passive: true });
   window.addEventListener('resize', () => render(0));
   ```
5. **접근성/성능 필수 처리:**
   - `prefers-reduced-motion: reduce`면 스크럽 대신 정적 히어로 이미지(콘티의 대표 프레임 하나)로 대체한다.
   - 100~150장 프리로드에 시간이 걸리므로 로딩 진행률(퍼센트 또는 스피너)을 보여준다.
   - 모바일은 대역폭이 부담될 수 있다 — 프레임 수를 줄이거나(예: 60장), 스크럽 대신 자동재생 영상으로 폴백하는 것도 고려한다.
   - 부드러운 보간이 필요하면 Lenis 같은 smooth-scroll 라이브러리를 붙이거나, 프레임 인덱스 자체를 lerp(선형보간)해서 뚝뚝 끊기지 않게 한다.

## 대안: ffmpeg 프레임 추출이 불가능할 때 (video currentTime 스크럽)

Claude Code 환경에 따라 생성된 영상 파일을 직접 다운로드하지 못할 수 있다(네트워크 정책으로 생성 도구의 CDN 도메인이 막혀 있는 경우 등). 이럴 땐 프레임 시퀀스 추출 없이, `<video>` 엘리먼트의 `currentTime`을 스크롤 위치에 직접 매핑해도 동일한 스크럽 효과를 낼 수 있다 — 실전에서 검증됨.

```html
<section style="height: 280vh; position: relative;">
  <div style="position: sticky; top: 0; height: 100vh; overflow: hidden;">
    <video id="scrubVideo" src="영상URL" poster="대표프레임URL" muted playsinline preload="auto"></video>
  </div>
</section>
```
```js
const scrubVideo = document.getElementById('scrubVideo');
const track = scrubVideo.closest('section');
let ready = false;
scrubVideo.addEventListener('loadedmetadata', () => {
  ready = true;
  scrubVideo.play().then(() => scrubVideo.pause()).catch(() => {}); // 디코더 프라이밍
});
let ticking = false;
function update() {
  if (ready && scrubVideo.duration) {
    const scrollable = track.offsetHeight - window.innerHeight;
    const rect = track.getBoundingClientRect();
    const progress = Math.min(Math.max(-rect.top / scrollable, 0), 1);
    scrubVideo.currentTime = progress * scrubVideo.duration;
  }
  ticking = false;
}
window.addEventListener('scroll', () => {
  if (!ticking) { ticking = true; requestAnimationFrame(update); }
}, { passive: true });
```

장점: ffmpeg·프레임 저장 공간·프리로드 대기 시간이 전혀 필요 없다. 단점: 프레임 시퀀스 방식보다 미세하게 덜 매끄러울 수 있고(코덱의 키프레임 간격에 따라), 모바일 Safari에서 프로그래밍 방식 seek가 가끔 불안정하다 — 프로덕션에서는 두 방식 다 실제로 테스트해볼 것.

## 이 프로젝트(블루바이오)에 적용한 사례

`bluebio-website`의 브랜드 히어로(`#about` 섹션)에 실제로 적용했다. "물리적 AI가 소상공인·이동권·공공조달·안전·문화예술을 돕는다"는 컨셉으로 Higgsfield(`cinematic_studio_2_5` 이미지 모델 + `cinematic_studio_video_v2` 영상 모델)에서:

1. 레퍼런스 이미지 1장(로봇 디자인 확정) → 이 이미지를 참조로 나머지 4장(섹션별 컬러 액센트: 코랄/틸/블루/바이올렛/레인보우) 생성
2. 콘티 확정(단순 카메라 푸시인 + 제스처, 회전·분해 없음) → 사용자 컨펌
3. 크레딧 견적(Standard 6크레딧 vs Pro 9크레딧) → 사용자가 Standard 선택
4. 6초 히어로 영상 생성 (레퍼런스 이미지 1을 start_image로 사용)
5. ffmpeg 프레임 추출이 네트워크 제약으로 불가능해서 → 위 "video currentTime 스크럽" 대안으로 구현
6. 나머지 4장은 각 섹션(`#mobility`, `#system`, `#safety`, `#gallery`)의 `.section-portrait` 이미지로 배치

이 순서 자체가 재사용 가능한 패턴이다: 레퍼런스 1장 → 그걸 참조로 나머지 배리에이션 생성 → 그중 하나만 영상화 → 나머지는 정적 이미지로.
