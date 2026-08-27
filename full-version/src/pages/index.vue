<script setup lang="ts">
import { useRouter } from 'vue-router'

definePage({
  meta: {
    layout: 'blank',
    public: true,
  },
})

const router = useRouter()

function enterPersonal() {
  router.push('/dashboards/fall-risk')
}

function enterCaregiver() {
  router.push('/dashboards/fall-risk-dashboard')
}
</script>

<template>
  <main class="fall-risk-home">
    <div class="home-glow home-glow--top" aria-hidden="true" />
    <div class="home-glow home-glow--bottom" aria-hidden="true" />
    <div class="home-grid" aria-hidden="true" />

    <div class="home-shell">
      <header class="home-header">
        <RouterLink
          to="/"
          class="home-brand"
          aria-label="SafeStride AI homepage"
        >
          <span class="brand-mark">
            <VIcon icon="tabler-shield-heart" size="22" />
          </span>
          <span>
            <strong>SafeStride</strong>
            <small>FALL RISK AI</small>
          </span>
        </RouterLink>

        <div class="home-status">
          <span class="status-dot" aria-hidden="true" />
          <span>AI model service online</span>
        </div>
      </header>

      <section class="home-hero" aria-labelledby="home-title">
        <div class="hero-copy">
          <p class="eyebrow">
            <span class="eyebrow-line" aria-hidden="true" />
            ELDERCARE · FALL PREVENTION
          </p>
          <h1 id="home-title">
            Make every rise<br>
            <span>feel safer</span>
          </h1>
          <p class="hero-description">
            An AI-powered fall-risk assessment system for older adults, delivering clear, timely, and explainable risk insights for individuals and care teams.
          </p>

          <div class="hero-points" aria-label="System capabilities">
            <span><VIcon icon="tabler-chart-donut-4" size="17" />Low / medium / high risk levels</span>
            <span><VIcon icon="tabler-bulb" size="17" />Explainable risk factors</span>
            <span><VIcon icon="tabler-lock-check" size="17" />Secure data storage</span>
          </div>
        </div>

        <div class="hero-visual" aria-label="Fall-risk monitoring visualization">
          <div class="visual-orbit visual-orbit--outer" aria-hidden="true" />
          <div class="visual-orbit visual-orbit--inner" aria-hidden="true" />
          <div class="visual-core">
            <VIcon icon="tabler-shield-check" size="42" />
            <span>Monitoring</span>
          </div>
          <span class="visual-node visual-node--one" aria-hidden="true" />
          <span class="visual-node visual-node--two" aria-hidden="true" />
          <span class="visual-node visual-node--three" aria-hidden="true" />
          <div class="visual-caption">
            <span class="caption-label">RISK SIGNAL</span>
            <strong>Real-time · Actionable</strong>
          </div>
          <div class="visual-scale" aria-hidden="true">
            <span class="scale-high" />
            <span class="scale-medium" />
            <span class="scale-low" />
          </div>
        </div>
      </section>

      <section
        class="role-section"
        aria-labelledby="role-title"
      >
        <div class="section-heading">
          <div>
            <p class="section-kicker">SELECT YOUR EXPERIENCE</p>
            <h2 id="role-title">Choose how you’ll use SafeStride</h2>
          </div>
          <p class="section-hint">Switch modes at any time</p>
        </div>

        <div class="role-grid">
          <button
            type="button"
            class="role-card role-card--personal"
            data-testid="personal-entry"
            aria-label="Individual use, enter a personal fall-risk assessment"
            @click="enterPersonal"
          >
            <span class="role-icon">
              <VIcon icon="tabler-user-heart" size="30" />
            </span>
            <span class="role-card-content">
              <span class="role-label">FOR INDIVIDUALS</span>
              <span class="role-title">Individual use</span>
              <span class="role-description">Enter a few details to get a personalized fall-risk assessment and improvement suggestions.</span>
              <span class="role-features">
                <span><VIcon icon="tabler-check" size="16" />Quick self-check</span>
                <span><VIcon icon="tabler-check" size="16" />Understand your risk factors</span>
              </span>
            </span>
            <span class="role-cta">
              Start personal assessment
              <VIcon icon="tabler-arrow-up-right" size="20" />
            </span>
          </button>

          <button
            type="button"
            class="role-card role-card--caregiver"
            data-testid="caregiver-entry"
            aria-label="Care team use, enter the care workspace"
            @click="enterCaregiver"
          >
            <span class="role-icon">
              <VIcon icon="tabler-building-hospital" size="30" />
            </span>
            <span class="role-card-content">
              <span class="role-label">FOR CARE TEAMS</span>
              <span class="role-title">Care team use</span>
              <span class="role-description">View resident risk distribution, assessment records, and prioritized care recommendations in one place.</span>
              <span class="role-features">
                <span><VIcon icon="tabler-check" size="16" />Resident risk overview</span>
                <span><VIcon icon="tabler-check" size="16" />Records &amp; reports</span>
              </span>
            </span>
            <span class="role-cta">
              Open care workspace
              <VIcon icon="tabler-arrow-up-right" size="20" />
            </span>
          </button>
        </div>
      </section>

      <footer class="home-footer">
        <span><VIcon icon="tabler-sparkles" size="15" />AI-assisted assessment · Results for health-management reference only</span>
        <span class="footer-separator" aria-hidden="true" />
        <span>SafeStride Fall Risk AI</span>
      </footer>
    </div>
  </main>
</template>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  min-block-size: 100%;
}

:global(body) {
  background: #07111f;
}

.fall-risk-home {
  --ink: #eaf4ff;
  --muted: #91a8bf;
  --cyan: #62e4d2;
  --blue: #74a7ff;
  position: relative;
  min-block-size: 100dvh;
  overflow: hidden;
  background:
    radial-gradient(circle at 9% 7%, rgb(41 108 135 / 22%), transparent 34%),
    radial-gradient(circle at 90% 13%, rgb(66 75 174 / 21%), transparent 32%),
    #07111f;
  color: var(--ink);
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.home-shell {
  position: relative;
  z-index: 1;
  inline-size: min(1180px, calc(100% - 48px));
  margin-inline: auto;
  padding-block: 28px 24px;
}

.home-glow {
  position: absolute;
  z-index: 0;
  border-radius: 999px;
  filter: blur(2px);
  pointer-events: none;
}

.home-glow--top {
  inset-block-start: -240px;
  inset-inline-end: 13%;
  inline-size: 470px;
  block-size: 470px;
  background: rgb(62 190 174 / 12%);
}

.home-glow--bottom {
  inset-block-end: -300px;
  inset-inline-start: 10%;
  inline-size: 560px;
  block-size: 560px;
  background: rgb(74 110 224 / 12%);
}

.home-grid {
  position: absolute;
  z-index: 0;
  inset: 0;
  opacity: 0.19;
  background-image: linear-gradient(rgb(153 192 219 / 8%) 1px, transparent 1px), linear-gradient(90deg, rgb(153 192 219 / 8%) 1px, transparent 1px);
  background-size: 54px 54px;
  mask-image: linear-gradient(to bottom, black, transparent 86%);
  pointer-events: none;
}

.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.home-brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  color: var(--ink);
  text-decoration: none;
}

.home-brand > span:last-child {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.home-brand strong {
  font-size: 16px;
  font-weight: 720;
  letter-spacing: 0.02em;
}

.home-brand small {
  color: #7792aa;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.brand-mark {
  display: grid;
  place-items: center;
  inline-size: 39px;
  block-size: 39px;
  border: 1px solid rgb(119 228 210 / 33%);
  border-radius: 13px;
  background: linear-gradient(145deg, rgb(91 221 201 / 25%), rgb(73 117 225 / 25%));
  color: var(--cyan);
  box-shadow: 0 8px 30px rgb(43 189 173 / 15%);
}

.home-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgb(136 168 195 / 18%);
  border-radius: 999px;
  background: rgb(18 37 58 / 58%);
  color: #9bb1c6;
  font-size: 11px;
}

.status-dot {
  inline-size: 7px;
  block-size: 7px;
  border-radius: 50%;
  background: #58e4be;
  box-shadow: 0 0 0 4px rgb(88 228 190 / 12%), 0 0 16px rgb(88 228 190 / 60%);
}

.home-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.14fr) minmax(330px, 0.86fr);
  align-items: center;
  gap: clamp(38px, 7vw, 90px);
  padding-block: clamp(44px, 6vh, 68px) 34px;
}

.hero-copy {
  max-inline-size: 620px;
}

.eyebrow,
.section-kicker,
.role-label,
.caption-label {
  margin: 0;
  color: #81a5c2;
  font-size: 10px;
  font-weight: 760;
  letter-spacing: 0.2em;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eyebrow-line {
  inline-size: 28px;
  block-size: 1px;
  background: linear-gradient(90deg, var(--cyan), transparent);
}

.hero-copy h1 {
  margin: 21px 0 20px;
  color: #f2f8ff;
  font-size: clamp(42px, 5.4vw, 73px);
  font-weight: 680;
  letter-spacing: -0.055em;
  line-height: 1.11;
}

.hero-copy h1 span {
  background: linear-gradient(100deg, #a9f8e9 2%, #83c7ff 92%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-description {
  max-inline-size: 510px;
  margin: 0;
  color: #a1b5c8;
  font-size: 16px;
  line-height: 1.85;
}

.hero-points {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-block-start: 28px;
  color: #9eb6ca;
  font-size: 12px;
}

.hero-points span,
.role-features span,
.home-footer span:first-child {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.hero-points .v-icon {
  color: var(--cyan);
}

.hero-visual {
  position: relative;
  display: grid;
  place-items: center;
  min-block-size: 280px;
  isolation: isolate;
}

.visual-orbit {
  position: absolute;
  border: 1px solid rgb(117 198 215 / 20%);
  border-radius: 50%;
  transform: rotate(-20deg);
}

.visual-orbit::after {
  position: absolute;
  inset-block-start: 13%;
  inset-inline-end: 6%;
  inline-size: 8px;
  block-size: 8px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 20px 6px rgb(98 228 210 / 37%);
  content: "";
}

.visual-orbit--outer {
  inline-size: 310px;
  block-size: 230px;
}

.visual-orbit--inner {
  inline-size: 230px;
  block-size: 170px;
  border-color: rgb(117 165 241 / 27%);
  transform: rotate(32deg);
}

.visual-orbit--inner::after {
  inset-block-start: auto;
  inset-inline-end: auto;
  inset-block-end: 7%;
  inset-inline-start: 10%;
  background: #83acff;
  box-shadow: 0 0 20px 6px rgb(131 172 255 / 36%);
}

.visual-core {
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  inline-size: 122px;
  block-size: 122px;
  border: 1px solid rgb(143 239 224 / 42%);
  border-radius: 38px;
  background: linear-gradient(145deg, rgb(38 88 103 / 84%), rgb(28 46 82 / 90%));
  color: #a7f7e9;
  box-shadow: 0 20px 65px rgb(8 208 188 / 15%), inset 0 1px 0 rgb(255 255 255 / 10%);
}

.visual-core span {
  color: #c1d9e7;
  font-size: 11px;
  letter-spacing: 0.14em;
}

.visual-node {
  position: absolute;
  inline-size: 5px;
  block-size: 5px;
  border-radius: 50%;
  background: #a6bcff;
  box-shadow: 0 0 15px 4px rgb(117 162 255 / 52%);
}

.visual-node--one { inset-block-start: 29px; inset-inline-start: 21%; }
.visual-node--two { inset-block-end: 33px; inset-inline-end: 22%; background: #72ead6; box-shadow: 0 0 15px 4px rgb(114 234 214 / 48%); }
.visual-node--three { inset-block-start: 47%; inset-inline-end: 7%; inline-size: 4px; block-size: 4px; }

.visual-caption {
  position: absolute;
  inset-block-end: 2px;
  inset-inline-start: 8%;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.visual-caption strong {
  color: #c7d9e8;
  font-size: 13px;
  font-weight: 600;
}

.visual-scale {
  position: absolute;
  inset-block-end: 9px;
  inset-inline-end: 8%;
  display: flex;
  gap: 4px;
  align-items: end;
}

.visual-scale span {
  display: block;
  inline-size: 5px;
  border-radius: 99px;
}

.scale-high { block-size: 12px; background: #f07887; }
.scale-medium { block-size: 20px; background: #f0be73; }
.scale-low { block-size: 29px; background: var(--cyan); }

.role-section {
  padding-block: 2px 12px;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin-block-end: 18px;
}

.section-heading h2 {
  margin: 8px 0 0;
  color: #e8f3fc;
  font-size: clamp(22px, 2.7vw, 30px);
  font-weight: 650;
  letter-spacing: -0.03em;
}

.section-hint {
  margin: 0 0 4px;
  color: #7e99b2;
  font-size: 12px;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.role-card {
  position: relative;
  display: flex;
  min-block-size: 286px;
  flex-direction: column;
  align-items: flex-start;
  padding: 28px 30px 25px;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 23px;
  text-align: start;
  cursor: pointer;
  transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
}

.role-card::after {
  position: absolute;
  inset-block-start: -95px;
  inset-inline-end: -70px;
  inline-size: 240px;
  block-size: 240px;
  border: 1px solid currentColor;
  border-radius: 50%;
  opacity: 0.13;
  content: "";
}

.role-card:hover {
  transform: translateY(-4px);
}

.role-card:focus-visible {
  outline: 3px solid rgb(139 243 224 / 84%);
  outline-offset: 4px;
}

.role-card--personal {
  border-color: rgb(130 221 210 / 31%);
  background: linear-gradient(135deg, #dffaf4 0%, #c9e8f4 100%);
  color: #123447;
  box-shadow: 0 20px 55px rgb(16 146 155 / 12%);
}

.role-card--personal:hover { box-shadow: 0 26px 65px rgb(39 193 187 / 22%); }

.role-card--caregiver {
  border-color: rgb(126 157 239 / 36%);
  background: linear-gradient(135deg, #1f3d74 0%, #253267 58%, #352b68 100%);
  color: #eff5ff;
  box-shadow: 0 20px 55px rgb(20 31 86 / 36%);
}

.role-card--caregiver:hover { box-shadow: 0 26px 65px rgb(52 73 176 / 42%); }

.role-icon {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  inline-size: 56px;
  block-size: 56px;
  border-radius: 17px;
}

.role-card--personal .role-icon {
  background: rgb(255 255 255 / 58%);
  color: #187d80;
}

.role-card--caregiver .role-icon {
  background: rgb(137 181 255 / 16%);
  color: #a9c8ff;
}

.role-card-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-block-start: 21px;
}

.role-card--personal .role-label { color: #4d8790; }
.role-card--caregiver .role-label { color: #a5bcde; }

.role-title {
  margin-block-start: 7px;
  font-size: 28px;
  font-weight: 720;
  letter-spacing: -0.04em;
}

.role-description {
  max-inline-size: 390px;
  margin-block-start: 9px;
  font-size: 13px;
  line-height: 1.7;
  opacity: 0.79;
}

.role-features {
  display: flex;
  flex-wrap: wrap;
  gap: 9px 18px;
  margin-block-start: 15px;
  font-size: 11px;
  font-weight: 600;
  opacity: 0.78;
}

.role-card--personal .role-features .v-icon { color: #168d83; }
.role-card--caregiver .role-features .v-icon { color: #91b9ff; }

.role-cta {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-block-start: auto;
  padding-block-start: 22px;
  font-size: 12px;
  font-weight: 720;
}

.role-card--personal .role-cta { color: #126d70; }
.role-card--caregiver .role-cta { color: #c9dcff; }

.home-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-block-start: 34px;
  color: #68829b;
  font-size: 10px;
  letter-spacing: 0.02em;
}

.home-footer .v-icon { color: #6dd9c7; }
.footer-separator { inline-size: 3px; block-size: 3px; border-radius: 50%; background: #46617b; }

@media (max-width: 900px) {
  .home-hero {
    grid-template-columns: 1fr;
    gap: 24px;
    padding-block: 48px 34px;
  }

  .hero-visual {
    min-block-size: 250px;
  }

  .role-card { min-block-size: 300px; }
}

@media (max-width: 620px) {
  .home-shell { inline-size: min(100% - 32px, 520px); padding-block-start: 20px; }
  .home-status { padding: 7px 9px; font-size: 10px; }
  .home-status span:last-child { display: none; }
  .home-hero { padding-block-start: 55px; }
  .hero-copy h1 { font-size: clamp(40px, 12vw, 58px); }
  .hero-description { font-size: 14px; }
  .hero-points { flex-direction: column; gap: 8px; }
  .hero-visual { transform: scale(0.9); transform-origin: center; }
  .section-heading { display: block; }
  .section-hint { margin-block-start: 10px; }
  .role-grid { grid-template-columns: 1fr; }
  .role-card { min-block-size: 276px; padding: 25px 24px 22px; }
  .role-title { font-size: 25px; }
  .home-footer { flex-wrap: wrap; row-gap: 7px; margin-block-start: 26px; }
  .footer-separator { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .role-card { transition: none; }
}
</style>
