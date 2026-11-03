"use client";

import { useState } from "react";
import { ArrowRight, BookOpen, CalendarCheck, ChartNoAxesColumnIncreasing, Check, ChevronDown, GraduationCap, Menu, ShieldCheck, Sparkles, Users, X } from "lucide-react";

type Role = "Teacher" | "Student" | "Parent";

const roleCopy: Record<Role, { heading: string; sub: string; bullets: string[] }> = {
  Teacher: { heading: "Your tuition center, in control.", sub: "Spend less time managing records and more time teaching.", bullets: ["Mark attendance in seconds", "Keep batches and student records together", "Track fee status and learning progress"] },
  Student: { heading: "Know where you stand.", sub: "A clear view of your classes, attendance, and progress.", bullets: ["See your attendance record", "Keep track of class schedules", "Review progress and updates"] },
  Parent: { heading: "Stay connected to learning.", sub: "Understand how your child is doing, without chasing updates.", bullets: ["Follow attendance and class activity", "View fee status and reminders", "Stay informed about progress"] },
};

export default function Home() {
  const [role, setRole] = useState<Role>("Teacher");
  const [loginOpen, setLoginOpen] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState("");

  function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("Authentication is not connected yet. Configure Supabase to enable secure sign-in.");
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#" aria-label="VIDYA-PATH home"><span className="brand-mark"><GraduationCap size={22} /></span><span>VIDYA<span className="brand-dash">-</span>PATH</span></a>
        <nav className={mobileMenu ? "nav-links open" : "nav-links"}>
          <a href="#features" onClick={() => setMobileMenu(false)}>Features</a>
          <a href="#how-it-works" onClick={() => setMobileMenu(false)}>How it works</a>
          <a href="#who-its-for" onClick={() => setMobileMenu(false)}>Who it’s for</a>
        </nav>
        <div className="nav-actions">
          <button className="text-button" onClick={() => setLoginOpen(true)}>Sign in</button>
          <button className="button button-small" onClick={() => setLoginOpen(true)}>Get started <ArrowRight size={16} /></button>
        </div>
        <button className="mobile-toggle" aria-label="Toggle navigation" onClick={() => setMobileMenu(!mobileMenu)}>{mobileMenu ? <X /> : <Menu />}</button>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> THE TUITION CENTER, CONNECTED</div>
          <h1>Good teaching.<br /><span>Clear progress.</span></h1>
          <p className="hero-description">One calm, simple place for teachers to manage classes—and for students and parents to stay in the loop.</p>
          <div className="hero-actions"><button className="button" onClick={() => setLoginOpen(true)}>Explore VIDYA-PATH <ArrowRight size={17} /></button><a className="quiet-link" href="#features">See what’s included <span>↓</span></a></div>
          <div className="trust-line"><ShieldCheck size={16} /> Built around clarity, privacy, and learning.</div>
        </div>
        <div className="hero-visual" aria-label="Preview of the tuition dashboard">
          <div className="visual-glow" />
          <div className="dashboard-preview">
            <div className="preview-top"><div className="mini-brand"><span className="mini-dot" /> VIDYA-PATH</div><span className="preview-tag">TEACHER VIEW</span></div>
            <div className="preview-welcome"><div><span className="tiny-label">MONDAY, 03 NOVEMBER</span><h3>Your class overview</h3></div><div className="avatar">T</div></div>
            <div className="stat-grid"><div className="stat-card"><span>Active students</span><strong>64</strong><small><span className="green">↗ 8%</span> this month</small></div><div className="stat-card"><span>Attendance today</span><strong>92<span className="percent">%</span></strong><small>Across 4 batches</small></div></div>
            <div className="preview-section-head"><strong>Today’s classes</strong><span>View schedule <ArrowRight size={13} /></span></div>
            <div className="class-row"><div className="class-icon blue"><BookOpen size={17} /></div><div className="class-info"><strong>Mathematics · Grade 10</strong><span>4:00 PM – 5:00 PM</span></div><span className="class-count">24 students</span></div>
            <div className="class-row"><div className="class-icon orange"><CalendarCheck size={17} /></div><div className="class-info"><strong>Physics · Grade 12</strong><span>5:30 PM – 6:30 PM</span></div><span className="class-count">18 students</span></div>
            <div className="preview-footer"><span><span className="status-dot" /> All records up to date</span><span>Preview data</span></div>
          </div>
          <div className="floating-note"><span className="note-icon"><Check size={15} /></span><span><strong>Attendance recorded</strong><small>Batch 10A · Today</small></span></div>
        </div>
      </section>

      <section className="proof-strip"><div><span className="proof-icon"><Users size={18} /></span><strong>One tuition center</strong><span>Connected people</span></div><div><span className="proof-icon"><CalendarCheck size={18} /></span><strong>Every class</strong><span>Organized records</span></div><div><span className="proof-icon"><ChartNoAxesColumnIncreasing size={18} /></span><strong>Clear progress</strong><span>Useful insights</span></div></section>

      <section className="features section" id="features">
        <div className="section-heading"><span className="eyebrow">MADE FOR THE WAY TUITION WORKS</span><h2>Less admin. More <span>learning.</span></h2><p>The essential tools for a tuition center—designed to work together, not get in your way.</p></div>
        <div className="feature-grid"><article className="feature-card"><div className="feature-icon lavender"><Users /></div><h3>People & batches</h3><p>Keep student profiles, parent contacts, and class groups organized in one place.</p><span className="feature-number">01</span></article><article className="feature-card"><div className="feature-icon mint"><CalendarCheck /></div><h3>Attendance, simplified</h3><p>Record daily attendance and give families a reliable view of class participation.</p><span className="feature-number">02</span></article><article className="feature-card"><div className="feature-icon peach"><ChartNoAxesColumnIncreasing /></div><h3>Progress that’s clear</h3><p>Bring assessments and learning updates together to make progress easier to understand.</p><span className="feature-number">03</span></article></div>
      </section>

      <section className="role-section section" id="who-its-for"><div className="role-panel"><div className="role-left"><span className="eyebrow">EVERYONE IN THE SAME LOOP</span><h2>One platform.<br /><span>Three perspectives.</span></h2><p>VIDYA-PATH connects the people who make learning happen.</p><div className="role-tabs">{(["Teacher", "Student", "Parent"] as Role[]).map(item => <button key={item} className={role === item ? "role-tab active" : "role-tab"} onClick={() => setRole(item)}>{item}<ChevronDown size={14} /></button>)}</div></div><div className="role-right"><div className="role-spark"><Sparkles size={20} /></div><h3>{roleCopy[role].heading}</h3><p>{roleCopy[role].sub}</p><ul>{roleCopy[role].bullets.map(item => <li key={item}><span><Check size={13} /></span>{item}</li>)}</ul><button className="role-cta" onClick={() => setLoginOpen(true)}>Continue as {role.toLowerCase()} <ArrowRight size={16} /></button></div></div></section>

      <section className="how section" id="how-it-works"><div className="section-heading"><span className="eyebrow">SIMPLE BY DESIGN</span><h2>Start with the <span>essentials.</span></h2><p>Built to grow with your tuition center, one useful step at a time.</p></div><div className="steps"><div className="step"><span className="step-number">01</span><h3>Set up your center</h3><p>Organize your classes, batches, and people.</p></div><div className="step-line" /><div className="step"><span className="step-number">02</span><h3>Run your daily classes</h3><p>Keep attendance and class activity in sync.</p></div><div className="step-line" /><div className="step"><span className="step-number">03</span><h3>Keep everyone informed</h3><p>Share meaningful updates with students and parents.</p></div></div></section>

      <section className="closing"><div><span className="eyebrow">A BETTER ROUTINE STARTS HERE</span><h2>Make room for<br />what matters.</h2><p>Bring your tuition center into one clear, connected space.</p><button className="button button-light" onClick={() => setLoginOpen(true)}>Get started <ArrowRight size={17} /></button></div><div className="closing-art"><div className="art-circle circle-one" /><div className="art-circle circle-two" /><GraduationCap size={100} strokeWidth={1} /></div></section>
      <footer><a className="brand footer-brand" href="#"><span className="brand-mark"><GraduationCap size={20} /></span><span>VIDYA<span className="brand-dash">-</span>PATH</span></a><span>Thoughtfully built for learning.</span><span>© 2026 VIDYA-PATH</span></footer>

      {loginOpen && <div className="modal-backdrop" onClick={() => { setLoginOpen(false); setNotice(""); }}><section className="login-modal" role="dialog" aria-modal="true" aria-labelledby="login-title" onClick={event => event.stopPropagation()}><button className="modal-close" aria-label="Close sign in" onClick={() => { setLoginOpen(false); setNotice(""); }}><X size={19} /></button><div className="modal-mark"><GraduationCap size={24} /></div><span className="eyebrow">WELCOME TO VIDYA-PATH</span><h2 id="login-title">Sign in to continue</h2><p>Access your tuition center workspace.</p><form onSubmit={signIn}><label htmlFor="phone">Phone number</label><input id="phone" type="tel" inputMode="numeric" placeholder="Enter your phone number" value={phone} onChange={event => setPhone(event.target.value)} required /><label htmlFor="password">Password</label><input id="password" type="password" placeholder="Enter your password" value={password} onChange={event => setPassword(event.target.value)} required /><button className="button modal-submit" type="submit">Sign in <ArrowRight size={16} /></button></form>{notice && <div className="form-notice" role="status">{notice}</div>}<div className="modal-foot">Secure sign-in will be enabled after Supabase setup.</div></section></div>}
    </main>
  );
}
