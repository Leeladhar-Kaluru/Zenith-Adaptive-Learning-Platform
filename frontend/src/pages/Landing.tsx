import { Link } from 'react-router-dom';
import { Icon } from '../icons/Icon';
import { Button, Card, Reveal } from '../ui/kit';
import s from './pages.module.css';

export function PublicBar() {
  return (
    <header className={s.pubBar}>
      <Link to="/" className={s.logo} aria-label="ZENITH home">
        <svg width="34" height="34" viewBox="0 0 32 32" aria-hidden="true"><path d="M2 27L13 7l5 9 3-5 9 16z" fill="var(--brand)" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" /><circle cx="24" cy="8" r="3.4" fill="var(--hi)" stroke="var(--ink)" strokeWidth="2" /></svg>
        ZENITH
      </Link>
      <div className={s.row}>
        <Button to="/signin" variant="ghost" size="sm">Sign in</Button>
        <Button to="/signup" variant="brand" size="sm">Start climbing</Button>
      </div>
    </header>
  );
}

export default function Landing() {
  return (
    <div className={s.pub}>
      <PublicBar />
      <main className={s.pubMain}>
        <section className={s.hero}>
          <h1>Everyone climbs at their <mark>own pace.</mark></h1>
          <svg className={s.squig} viewBox="0 0 360 14" preserveAspectRatio="none" aria-hidden="true"><path d="M4 8 C 40 0, 70 14, 110 7 S 180 1, 220 8 S 300 13, 356 5" /></svg>
          <p className={s.lead} style={{ margin: '22px auto 0', fontSize: '1.2rem' }}>
            ZENITH finds the missing step beneath whatever you are stuck on, helps you fix it, and shows your teacher exactly who needs help. Classes 6 to 10.
          </p>
          <div className={s.cta}>
            <Button to="/signup" variant="brand" iconRight="arrowR">Start climbing</Button>
            <span className="hand">free for students and teachers</span>
          </div>
        </section>

        <div className={s.three}>
          <Reveal><Card lift className={s.stackCard}>
            <span className={s.tag}>Learn</span><h3>Short lessons that make you think</h3>
            <p className="muted sm">One idea per screen. Try it before you read the answer.</p>
            <svg className={s.art} viewBox="0 0 300 130" aria-hidden="true"><rect x="20" y="20" width="120" height="90" rx="8" fill="var(--brand-soft)" stroke="var(--ink)" strokeWidth="3" /><path d="M40 50h80M40 70h60M40 90h70" stroke="var(--ink)" strokeWidth="3" strokeLinecap="round" /><path d="M170 100c40-70 80-70 110-70" fill="none" stroke="var(--brand)" strokeWidth="4" strokeDasharray="2 9" strokeLinecap="round" /><circle cx="282" cy="30" r="9" fill="var(--hi)" stroke="var(--ink)" strokeWidth="3" /></svg>
          </Card></Reveal>
          <Reveal delay={90}><Card lift>
            <span className={`${s.tag} ${s.tagB}`}>Solve</span><h3>Practice that adapts to you</h3>
            <p className="muted sm">Harder when you are flying, gentler steps when you are stuck.</p>
            <svg className={s.art} viewBox="0 0 300 130" aria-hidden="true"><path d="M20 110h260" stroke="var(--ink)" strokeWidth="3" strokeLinecap="round" /><rect x="40" y="70" width="40" height="40" fill="var(--science-soft)" stroke="var(--ink)" strokeWidth="3" /><rect x="100" y="45" width="40" height="65" fill="var(--science-soft)" stroke="var(--ink)" strokeWidth="3" /><rect x="160" y="20" width="40" height="90" fill="var(--hi)" stroke="var(--ink)" strokeWidth="3" /><path d="M215 60l20-25 20 25" fill="none" stroke="var(--ink)" strokeWidth="3" strokeLinecap="round" /></svg>
          </Card></Reveal>
          <Reveal delay={180}><Card lift>
            <span className={`${s.tag} ${s.tagC}`}>Test</span><h3>Checks that end with a plan</h3>
            <p className="muted sm">Not just a score: what to revisit, what to practise, what is next.</p>
            <svg className={s.art} viewBox="0 0 300 130" aria-hidden="true"><rect x="30" y="14" width="120" height="104" rx="8" fill="var(--surface)" stroke="var(--ink)" strokeWidth="3" /><circle cx="56" cy="44" r="8" fill="var(--ok)" stroke="var(--ink)" strokeWidth="2" /><circle cx="56" cy="72" r="8" fill="var(--gap)" stroke="var(--ink)" strokeWidth="2" /><circle cx="56" cy="100" r="8" fill="var(--ok)" stroke="var(--ink)" strokeWidth="2" /><path d="M76 44h50M76 72h40M76 100h46" stroke="var(--ink)" strokeWidth="3" strokeLinecap="round" /><path d="M170 70h100M170 94h70" stroke="var(--ink-2)" strokeWidth="3" strokeLinecap="round" /><path d="M170 46l8 8 14-16" fill="none" stroke="var(--ok)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </Card></Reveal>
        </div>

        <Reveal className={s.split}>
          <div><h2 className={s.sectionT}>It finds the gap <mark>under</mark> the gap.</h2>
            <p className="muted">Stuck on linear equations? The real problem may be two classes back. ZENITH follows the chain of ideas down and checks each step, then shows you where to start.</p></div>
          <Card>
            <div className={s.chain}>
              <div className={s.node}>Linear equations<small>Class 8</small></div><Icon name="arrowL" size={20} />
              <div className={`${s.node} ${s.nodeNow}`}>Algebraic expressions<small>Class 7</small></div><Icon name="arrowL" size={20} />
              <div className={`${s.node} ${s.nodeGap}`}>Integers<small>Class 6 · gap found</small></div>
            </div>
            <p className="hand" style={{ textAlign: 'center' }}>start here, then climb back up</p>
          </Card>
        </Reveal>

        <Reveal className={s.split}>
          <Card>
            <div className={s.reco}>
              <strong>For your classroom</strong>
              <p className="sm muted">See which students are secure, which are learning, and which have a gap. Every suggestion cites the answers behind it.</p>
              <div className={s.row}><Icon name="people" /><span className="sm">You decide what to assign. ZENITH does the noticing.</span></div>
            </div>
          </Card>
          <div><h2 className={s.sectionT}>Teachers stay in charge.</h2>
            <p className="muted">Class overview, concept heatmap and next-step suggestions grounded in real answers. Built for Indian classrooms, boards and languages: English, Hindi and Telugu explanations, and lessons that work on a shared phone with little data.</p>
            <div className={s.cta} style={{ justifyContent: 'flex-start' }}><Button to="/signup" variant="ghost" icon="people">I am a teacher</Button></div></div>
        </Reveal>
      </main>
      <footer className={s.foot}>ZENITH · Adaptive learning for Classes 6 to 10</footer>
    </div>
  );
}
