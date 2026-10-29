import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, Building2,
  ChartNoAxesCombined, Check, ChevronRight, Equal, FileText, House, LogOut,
  Moon, Search, Settings, ShieldCheck, Sun, Truck, UserRound, Wallet, X,
} from "lucide-react";
import { apiRequest, loginRequest } from "./api.js";
import "./CashCast.css";

const money = (value) => value === null || value === undefined || value === "" || !Number.isFinite(Number(value)) ? "—" : `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(Number(value))}`;
const pct = (value) => value === null || value === undefined || value === "" || !Number.isFinite(Number(value)) ? "—" : `${Number(value).toFixed(1)}%`;
const roleEmails = { Admin: "admin@bankmuscat.demo", "Cash Ops Officer": "ops@bankmuscat.demo", Viewer: "viewer@bankmuscat.demo" };

function LogoMark({ size = 22 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="3.25" y="7.15" width="17.5" height="9.7" rx="2.15" stroke="currentColor" strokeWidth="2"/><circle cx="12" cy="12" r="2.25" stroke="currentColor" strokeWidth="2"/><path d="M6.4 10.1v3.8M17.6 10.1v3.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>;
}

function Logo({ small = false }) {
  return <span className={`cc-logo${small ? " cc-logo-small" : ""}`} aria-label="CashCast"><LogoMark size={small ? 19 : 22}/></span>;
}

function DashboardPreviewMini() {
  return <section className="cc-dashboard-preview" id="dashboard"><aside className="cc-side-rail"><Logo small/>{[House,ChartNoAxesCombined,FileText,Bell,FileText,Sun].map((Icon,i)=><span key={i} className={`cc-rail-item${i===0?" is-active":""}`}><Icon size={19}/></span>)}</aside><div className="cc-dash-main"><div className="cc-dash-toolbar"><span className="cc-search"><Search size={16}/> Search ATM ID or city</span><nav className="cc-dash-tabs"><span className="selected">Overview</span><span>ATMs</span><span>What-if forecast</span><span>Replenishment</span><span>Alerts</span></nav><span className="cc-briefing">Daily briefing</span></div><div className="cc-dash-heading"><div><h2>Cash Demand<br/>Overview</h2><p>Historical simulation · Bank Muscat Project P_136</p><div className="cc-segment"><span className="selected">Network</span><span>Selected ATM</span></div></div><div className="cc-metric-grid"><article className="cc-metric-card"><b>Forecast accuracy</b><p>Values load from the model API</p><span className="cc-preview-skeleton-line"/></article><article className="cc-metric-card"><b>Cash-out reduction</b><p>Historical replay simulation</p><span className="cc-preview-skeleton-line"/></article><article className="cc-metric-card"><b>ATMs at risk</b><p>Live dataset values after sign in</p><span className="cc-preview-skeleton-line"/></article></div></div><div className="cc-content-grid"><article className="cc-chart-card"><h3>Historical demand</h3><p>Sign in to load actuals and model predictions.</p><div className="cc-preview-placeholder">CashCast model dashboard</div></article><article className="cc-cash-card"><h3>Cash on hand</h3><p>Network totals load after sign in.</p></article></div></div></section>;
}

function Landing({ onOpenDashboard }) {
  const [menuOpen,setMenuOpen]=useState(false),[loginOpen,setLoginOpen]=useState(false);
  const [email,setEmail]=useState(""),[password,setPassword]=useState(""),[role,setRole]=useState("Cash Ops Officer");
  const [loginError,setLoginError]=useState(""),[busy,setBusy]=useState(false);
  const openLogin=()=>{setMenuOpen(false);setLoginError("");setLoginOpen(true);};
  const fillDemo=()=>{setEmail(roleEmails[role]);setPassword("demo123");setLoginError("");};
  useEffect(()=>{const close=(event)=>{if(event.key==="Escape")setLoginOpen(false);};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close);},[]);
  const signIn=async(event)=>{event.preventDefault();setBusy(true);setLoginError("");try{const session=await loginRequest(email.trim(),password,role);onOpenDashboard(session);setLoginOpen(false);}catch(error){setLoginError(error.message);}finally{setBusy(false);}};
  return <main className="cc-landing"><header className="cc-nav"><a className="cc-brand" href="#top"><Logo/><span>CASHCAST</span></a><nav className={menuOpen?"open":""}><span>Product</span><span>Features</span><span>Security</span><span>Forecast</span><span>Contact</span></nav><button className="cc-nav-cta" onClick={openLogin}>Get Started <ArrowRight size={16}/></button><button className="cc-menu-toggle" aria-label="Toggle navigation" onClick={()=>setMenuOpen(!menuOpen)}>{menuOpen?<X/>:<span>☰</span>}</button></header><section className="cc-hero" id="top"><div className="cc-eyebrow"><Activity size={15}/> INTELLIGENT ATM CASH MANAGEMENT</div><h1>Everything you need to<br/> keep ATMs stocked <span>smarter.</span></h1><p>Predict tomorrow’s cash demand for every ATM, see which machines will run low, and plan refills with one clear, connected dashboard.</p><div className="cc-hero-actions"><button className="cc-primary-cta" onClick={openLogin}><i/> Start Free Trial <ArrowRight size={17}/></button><a className="cc-secondary-cta" href="#features">Explore Features <ArrowDownRight size={17}/></a></div><div className="cc-proof"><span><ShieldCheck size={16}/> Bank grade security</span><span><Building2 size={16}/> Built for Bank Muscat</span><span><Activity size={16}/> Historical model insights</span></div></section><div className="cc-preview-wrap"><DashboardPreviewMini/></div><section className="cc-feature-section" id="features"><div className="cc-section-intro"><span className="cc-eyebrow">THE CASHCAST ADVANTAGE</span><h2>Built for the cash operations team.</h2><p>One connected view to help your team predict demand and keep every ATM ready.</p></div><div className="cc-features"><article id="product"><span className="cc-feature-icon"><ChartNoAxesCombined/></span><h3>Demand forecast</h3><p>Review next-day demand predictions from the trained model and historical ATM withdrawals.</p></article><article id="forecast"><span className="cc-feature-icon"><Wallet/></span><h3>Refill plan</h3><p>Use API-backed replenishment recommendations to plan simulated cash dispatches.</p></article><article><span className="cc-feature-icon"><Bell/></span><h3>Actionable alerts</h3><p>Review low-cash risk, demand changes, and machines needing attention.</p></article><article id="security"><span className="cc-feature-icon"><ShieldCheck/></span><h3>Role-aware access</h3><p>Admin, Cash Ops Officer, and Viewer access for this historical simulation.</p></article></div></section><footer className="cc-footer" id="contact"><a className="cc-brand" href="#top"><Logo small/><span>CASHCAST</span></a><span>Bank Muscat · Project P_136 · Historical simulation</span><button onClick={openLogin}>Open your dashboard <ArrowRight size={15}/></button></footer>{loginOpen&&<div className="cc-login-backdrop" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)setLoginOpen(false);}}><section className="cc-login-card" role="dialog" aria-modal="true" aria-labelledby="cc-login-title"><button className="cc-login-close" aria-label="Close sign in" onClick={()=>setLoginOpen(false)}><X size={18}/></button><Logo/><span className="cc-login-kicker">BANK MUSCAT · CASHCAST</span><h2 id="cc-login-title">Welcome back</h2><p className="cc-login-subtitle">Sign in to your cash operations dashboard.</p><form onSubmit={signIn}><label>Email<input type="email" autoComplete="username" value={email} onChange={(e)=>setEmail(e.target.value)} placeholder="you@bankmuscat.com" required/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e)=>setPassword(e.target.value)} placeholder="Enter your password" required/></label><label>Role<select value={role} onChange={(e)=>setRole(e.target.value)}><option>Admin</option><option>Cash Ops Officer</option><option>Viewer</option></select></label>{loginError&&<p className="cc-login-error" role="alert">{loginError}</p>}<button className="cc-login-submit" type="submit" disabled={busy}>{busy?"Signing in…":"Sign in"} <ArrowRight size={16}/></button></form><button className="cc-demo-fill" type="button" onClick={fillDemo}>Fill demo login</button><p className="cc-demo-note">Demo password: demo123 · Choose a role to fill its demo account</p></section></div>}</main>;
}

function CashDashboard({ role, email, token, onSignOut }) {
  const [page,setPage]=useState("Overview"),[query,setQuery]=useState(""),[dark,setDark]=useState(false);
  const [metrics,setMetrics]=useState(null),[atmData,setAtmData]=useState([]),[network,setNetwork]=useState(null),[atmForecast,setAtmForecast]=useState(null);
  const [replenishment,setReplenishment]=useState(null),[alerts,setAlerts]=useState([]),[dispatches,setDispatches]=useState([]);
  const [whatif,setWhatif]=useState([]),[festival,setFestival]=useState(false),[holiday,setHoliday]=useState(false),[adjust,setAdjust]=useState(0);
  const [chartMode,setChartMode]=useState("Daily"),[activeAtm,setActiveAtm]=useState(null),[selected,setSelected]=useState([]),[vanCapacity,setVanCapacity]=useState("");
  const [threshold,setThreshold]=useState(3),[criticalThreshold,setCriticalThreshold]=useState(1.5),[profileOpen,setProfileOpen]=useState(false),[briefOpen,setBriefOpen]=useState(false);
  const [loading,setLoading]=useState(true),[error,setError]=useState(""),[pageError,setPageError]=useState(""),[toast,setToast]=useState("");
  const logoutOn401=useCallback(()=>{sessionStorage.removeItem("cashcast.auth");onSignOut();},[onSignOut]);
  const request=useCallback((path,options={})=>apiRequest(path,{...options,token,onUnauthorized:logoutOn401}),[token,logoutOn401]);
  const refreshAlerts=async()=>{const value=await request("/alerts");setAlerts(value.items??[]);};
  const refreshDispatches=async()=>{const value=await request("/dispatches");setDispatches(value.items??[]);};
  const refreshReplenishment=async()=>{const value=await request("/replenishment");setReplenishment(value);};
  useEffect(()=>{let active=true;const load=async()=>{setLoading(true);setError("");try{const [m,a,f,r,al]=await Promise.all([request("/metrics"),request("/atms"),request("/forecast/network"),request("/replenishment"),request("/alerts")]);if(!active)return;setMetrics(m);setAtmData(a.items??[]);setNetwork(f);setReplenishment(r);setAlerts(al.items??[]);try{const d=await request("/dispatches");if(active)setDispatches(d.items??[]);}catch(dispatchError){if(active)setPageError(dispatchError.message);}}catch(loadError){if(active)setError(loadError.message);}finally{if(active)setLoading(false);}};load();return()=>{active=false;};},[request]);
  useEffect(()=>{let active=true;const load=async()=>{try{const params=new URLSearchParams({festival:String(festival),holiday:String(holiday),adjust:String(adjust)});const result=await request(`/whatif?${params}`);if(active)setWhatif(result.items??[]);}catch(loadError){if(active)setPageError(loadError.message);}};load();return()=>{active=false;};},[request,festival,holiday,adjust]);
  useEffect(()=>{let active=true;if(activeAtm){const load=async()=>{try{const result=await request(`/forecast/${encodeURIComponent(activeAtm.id)}`);if(active)setAtmForecast(result);}catch(loadError){if(active)setPageError(loadError.message);}};load();}return()=>{active=false;};},[request,activeAtm]);
  const atmRows=useMemo(()=>atmData.map((a)=>({id:a.ATM_ID,location:a.Location,city:a.City,cash:Number(a.current_cash),cap:Number(a.capacity),forecast:Number(a.forecast),days:Number(a.days_of_cover),accuracy:metrics?.atm_accuracy?.[a.ATM_ID],status:a.risk_level??a.urgency,statusLabel:a.status,atRisk:Boolean(a.at_risk),criticalRisk:Boolean(a.critical_risk),refill:Number(a.recommended_refill),fill:Number(a.cash_level_percent)})),[atmData,metrics]);
  const matches=atmRows.filter((a)=>`${a.id} ${a.location} ${a.city}`.toLowerCase().includes(query.toLowerCase()));
  const selectedRows=atmRows.filter((a)=>selected.includes(a.id));
  const riskRows=atmRows.filter((a)=>a.atRisk),criticalRows=atmRows.filter((a)=>a.criticalRisk);
  const isViewer=role==="Viewer",tabs=["Overview","ATMs","What-if forecast","Replenishment","Alerts","Settings"],icons=[House,Building2,Activity,Truck,Bell,Settings];
  const statusOf=(atm)=>atm.criticalRisk||atm.days<criticalThreshold?"Critical":atm.atRisk||atm.days<threshold?"Refill soon":"OK";
  const notify=(message)=>{setToast(message);window.setTimeout(()=>setToast(""),2700);};
  const navigate=(name)=>{setPage(name);setProfileOpen(false);};
  const acknowledge=async(id)=>{try{await request(`/alerts/${encodeURIComponent(id)}/acknowledge`,{method:"POST"});await refreshAlerts();notify(`${id} alert acknowledged.`);}catch(e){setPageError(e.message);}};
  const dispatch=async(ids)=>{if(isViewer){notify("Viewer role cannot schedule a dispatch.");return;}try{const result=await request("/dispatch",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({atm_ids:ids})});await Promise.all([refreshDispatches(),refreshAlerts(),refreshReplenishment()]);notify(`${result.count} dispatch record(s) saved as a simulation.`);}catch(e){setPageError(e.message);}};
  const copyCsv=async()=>{const text=["ATM_ID,Location,City,Recommended_Refill_INR",...selectedRows.map((a)=>`${a.id},${a.location},${a.city},${a.refill}`)].join("\n");try{await navigator.clipboard.writeText(text);notify("API replenishment rows copied as CSV.");}catch{notify("Clipboard access is unavailable in this browser.");}};
  const chartItems=activeAtm?(atmForecast?.ATM_ID===activeAtm.id?(atmForecast?.items??[]):[]):(network?.items??[]);
  const chartValues=chartMode==="Cumulative"?chartItems.reduce((acc,item,index)=>{acc.push({ ...item, actualCumulative:(acc[index-1]?.actualCumulative??0)+(Number(item.actual)||0), predictedCumulative:(acc[index-1]?.predictedCumulative??0)+(Number(item.predicted)||0)});return acc;},[]):chartItems;
  const maxChart=Math.max(1,...chartValues.flatMap((item)=>[Number(chartMode==="Cumulative"?item.actualCumulative:item.actual)||0,Number(chartMode==="Cumulative"?item.predictedCumulative:item.predicted)||0]));
  const activeAtmName=activeAtm?`${activeAtm.id} · ${activeAtm.location}`:"All ATMs";
  const displayedCash=activeAtm?.cash??Number(metrics?.cash_on_hand??0);
  const displayedCapacity=activeAtm?.cap??Number(metrics?.capacity??0);
  const cashRatio=displayedCapacity>0?displayedCash/displayedCapacity*100:0;
  const accuracyValue=Math.max(0,Math.min(100,Number(activeAtm?.accuracy??metrics?.accuracy_percent)||0));
  const cashoutValue=Math.max(0,Math.min(100,Number(metrics?.cashout_reduction_percent)||0));
  const riskCount=activeAtm?Number(activeAtm.atRisk):riskRows.length;
  const criticalCount=activeAtm?Number(activeAtm.criticalRisk):criticalRows.length;
  const displayAtmCount=activeAtm?1:atmRows.length;
  const riskPercent=atmRows.length?(activeAtm?(activeAtm.atRisk?100:0):riskRows.length/atmRows.length*100):0;
  const days=metrics?.data_start&&metrics?.data_end?`${metrics.data_start} – ${metrics.data_end}`:"historical dataset";
  if(loading)return <main className={`cc-ops-dashboard${dark?" is-dark":""}`}><div className="cc-api-state"><Logo/><h1>Loading CashCast dashboard</h1><p>Fetching historical metrics, ATM forecasts, replenishment and alerts from the API…</p></div></main>;
  if(error)return <main className={`cc-ops-dashboard${dark?" is-dark":""}`}><div className="cc-api-state cc-api-error"><h1>Dashboard data could not be loaded</h1><p>{error}</p><button className="cc-briefing" onClick={()=>window.location.reload()}>Retry</button><button className="cc-secondary-action" onClick={onSignOut}>Sign out</button></div></main>;
  return (
    <main className={`cc-ops-dashboard${dark ? " is-dark" : ""}`}>
      <aside className="cc-ops-rail">
        <button
          className="cc-ops-logo"
          aria-label="CashCast overview"
          onClick={() => navigate("Overview")}
        >
          <LogoMark />
        </button>
        <nav>
          {icons.slice(0, 5).map((Icon, index) => (
            <button
              key={tabs[index]}
              className={`cc-ops-rail-btn${page === tabs[index] ? " active" : ""}`}
              title={tabs[index]}
              aria-label={tabs[index]}
              onClick={() => navigate(tabs[index])}
            >
              <Icon size={20} />
            </button>
          ))}
        </nav>
        <div className="cc-ops-rail-bottom">
          <button
            className="cc-ops-rail-btn"
            title={dark ? "Switch to light theme" : "Switch to dark theme"}
            aria-label="Toggle theme"
            onClick={() => setDark(!dark)}
          >
            {dark ? <Moon size={20} /> : <Sun size={20} />}
          </button>
          <button
            className="cc-ops-rail-btn cc-rail-signout"
            title="Sign out"
            aria-label="Sign out"
            onClick={onSignOut}
          >
            <LogOut size={19} />
          </button>
        </div>
      </aside>
      <div className="cc-ops-main">
        <header className="cc-ops-toolbar">
          <label className="cc-ops-search">
            <Search size={17} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search ATM ID or city"
            />
            <kbd>⌘K</kbd>
          </label>
          <nav className="cc-ops-tabs">
            {tabs.map((tab) => (
              <button
                key={tab}
                className={page === tab ? "active" : ""}
                onClick={() => navigate(tab)}
              >
                {tab}
              </button>
            ))}
          </nav>
          <button className="cc-briefing" onClick={() => setBriefOpen(true)}>
            Daily briefing
          </button>
          <div
            className="cc-profile-wrap"
            onBlur={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget))
                setProfileOpen(false);
            }}
          >
            <button
              className="cc-profile-button"
              aria-label="Open profile"
              aria-expanded={profileOpen}
              onClick={() => setProfileOpen(!profileOpen)}
            >
              <UserRound size={19} />
            </button>
            {profileOpen && (
              <div className="cc-profile-popover">
                <div className="cc-profile-summary">
                  <span className="cc-profile-avatar">
                    <UserRound size={20} />
                  </span>
                  <div>
                    <b>
                      {role === "Admin"
                        ? "CashCast Admin"
                        : role === "Viewer"
                          ? "CashCast Viewer"
                          : "Operations User"}
                    </b>
                    <small>{email}</small>
                  </div>
                </div>
                <div className="cc-profile-detail">
                  <span>Role</span>
                  <b>{role}</b>
                </div>
                <div className="cc-profile-detail">
                  <span>Organization</span>
                  <b>Bank Muscat</b>
                </div>
                <button onClick={() => navigate("Settings")}>
                  Account settings <ChevronRight size={15} />
                </button>
                <button className="cc-profile-signout" onClick={onSignOut}>
                  <LogOut size={15} /> Sign out
                </button>
              </div>
            )}
          </div>
        </header>
        {pageError && (
          <div className="cc-inline-error" role="alert">
            {pageError}
            <button onClick={() => setPageError("")} aria-label="Dismiss error">
              <X size={14} />
            </button>
          </div>
        )}
        {page === "Overview" && (
          <>
            <div className="cc-ops-overview-head">
              <div>
                <h1>
                  Cash Demand
                  <br />
                  Overview
                </h1>
                <p>
                  Bank Muscat · Project P_136 · Historical simulation · {days}
                </p>
                <div className="cc-scope-toggle">
                  <button
                    className={!activeAtm ? "active" : ""}
                    onClick={() => setActiveAtm(null)}
                  >
                    Network
                  </button>
                  <label className={`cc-atm-select-label${activeAtm ? " active" : ""}`}>
                    <span className="cc-visually-hidden">Select ATM</span>
                    <select
                      aria-label="Select ATM"
                      value={activeAtm?.id ?? ""}
                      onChange={(event) =>
                        setActiveAtm(
                          atmRows.find((atm) => atm.id === event.target.value) ??
                            null,
                        )
                      }
                    >
                      <option value="">Select ATM</option>
                      {atmRows.map((atm) => (
                        <option key={atm.id} value={atm.id}>
                          {atm.id} · {atm.city}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
              <div className="cc-kpi-grid">
                <article className="cc-kpi">
                  <div className="cc-kpi-label">
                    <span className="cc-kpi-icon">
                      <ArrowUpRight size={18} />
                    </span>
                    <b>
                      Forecast
                      <br />
                      accuracy
                    </b>
                    <em>
                      Target
                      <br />
                      85%
                    </em>
                  </div>
                  <p>100 − MAPE · model evaluation</p>
                  <strong>{pct(activeAtm?.accuracy ?? metrics?.accuracy_percent)}</strong>
                  <div className="cc-kpi-progress" role="meter" aria-label="Forecast accuracy" aria-valuemin="0" aria-valuemax="100" aria-valuenow={accuracyValue}>
                    <i style={{ width: `${accuracyValue}%` }} />
                  </div>
                </article>
                <article className="cc-kpi">
                  <div className="cc-kpi-label">
                    <span className="cc-kpi-icon">
                      <ArrowDownRight size={18} />
                    </span>
                    <b>
                      Cash-out
                      <br />
                      reduction
                    </b>
                    <em>
                      Target
                      <br />
                      70%
                    </em>
                  </div>
                  <p>Day-by-day backtest · simulation</p>
                  <strong>{pct(metrics?.cashout_reduction_percent)}</strong>
                  <div className="cc-kpi-progress">
                    <i
                      style={{
                        width: `${cashoutValue}%`,
                      }}
                    />
                  </div>
                </article>
                <article className="cc-kpi">
                  <div className="cc-kpi-label">
                    <span className="cc-kpi-icon"><Equal size={18}/></span>
                    <b>ATMs at risk</b>
                    <em className="critical">{criticalCount} critical</em>
                  </div>
                  <p>API cash-cover status</p>
                  <strong>
                    {riskCount} of {displayAtmCount}
                  </strong>
                  <div className="cc-kpi-progress" role="meter" aria-label="ATMs at risk" aria-valuemin="0" aria-valuemax="100" aria-valuenow={riskPercent}>
                    <i style={{ width: `${riskPercent}%` }} />
                  </div>
                </article>
              </div>
            </div>
            <div className="cc-ops-overview-grid">
              <article className="cc-ops-panel cc-withdrawal-chart">
                <div className="cc-panel-heading">
                  <div>
                    <h2>{activeAtmName}</h2>
                    <p>
                      Historical actual withdrawals, model predictions, and the
                      next-day forecast · INR
                    </p>
                  </div>
                  <div className="cc-mode-toggle">
                    <button
                      className={chartMode === "Daily" ? "active" : ""}
                      onClick={() => setChartMode("Daily")}
                    >
                      Daily
                    </button>
                    <button
                      className={chartMode === "Cumulative" ? "active" : ""}
                      onClick={() => setChartMode("Cumulative")}
                    >
                      Cumulative
                    </button>
                  </div>
                </div>
                <div className="cc-ops-chart">
                  <div className="cc-chart-guides">
                    <i />
                    <i />
                    <i />
                    <i />
                  </div>
                  <div className="cc-chart-bars">
                    {chartValues.map((item, index) => {
                      const actual =
                        Number(
                          chartMode === "Cumulative"
                            ? item.actualCumulative
                            : item.actual,
                        ) || 0;
                      const predicted =
                        Number(
                          chartMode === "Cumulative"
                            ? item.predictedCumulative
                            : item.predicted,
                        ) || 0;
                      const isTomorrow = item.tomorrow === true;
                      const plotted = isTomorrow ? predicted : actual;
                      return (
                        <span
                          key={`${item.date}-${index}`}
                          className={isTomorrow ? "tomorrow" : ""}
                          tabIndex={0}
                          aria-label={`${item.date}: actual ${money(actual)}, forecast ${money(predicted)}`}
                          style={{
                            height: `${Math.max(2, (plotted / maxChart) * 100)}%`,
                            "--prediction-height": `${(predicted / maxChart) * 100}%`,
                          }}
                        >
                          <i className="prediction-dot" />
                          <span className="cc-chart-tooltip">
                            {item.date} · {isTomorrow ? "Forecast" : "Actual"} {money(isTomorrow ? predicted : actual)}
                          </span>
                        </span>
                      );
                    })}
                  </div>
                  <div className="cc-chart-labels">
                    {chartValues
                      .filter(
                        (_, i) =>
                          i === 0 ||
                          i === chartValues.length - 1 ||
                          i %
                            Math.max(1, Math.floor(chartValues.length / 5)) ===
                            0,
                      )
                      .map((item, index) => (
                        <span key={`${item.date}-${index}`}>
                          {item.tomorrow
                            ? "Tomorrow"
                            : new Date(
                                `${item.date}T00:00:00`,
                              ).toLocaleDateString("en-IN", {
                                day: "numeric",
                                month: "short",
                              })}
                        </span>
                      ))}
                  </div>
                </div>
              </article>
              <article className="cc-ops-panel cc-cash-on-hand">
                <h2>Cash on hand{activeAtm ? ` · ${activeAtm.id}` : ""}</h2>
                <strong>{money(displayedCash)}</strong>
                <p>
                  of {money(displayedCapacity)} capacity ({pct(cashRatio)}) ·
                  latest dataset day
                </p>
                <ul>
                  {(activeAtm ? [activeAtm] : atmRows.slice(0, 6)).map((atm, index) => (
                    <li key={atm.id}>
                      <i
                        style={{
                          background: `hsl(${(index * 61) % 360} 72% 58%)`,
                        }}
                      />
                      {atm.city} <span>({pct(atm.fill)})</span>
                    </li>
                  ))}
                </ul>
                <div
                  className="cc-cash-gauge"
                  style={{
                    background: `conic-gradient(#e8ed3d 0 ${cashRatio}%,#f1f2f7 ${cashRatio}% 100%)`,
                  }}
                >
                  <div>
                    <b>{pct(cashRatio)}</b>
                    <small>capacity</small>
                  </div>
                </div>
              </article>
            </div>
            <div className="cc-ops-lower-grid">
              <article className="cc-ops-panel">
                <div className="cc-panel-heading">
                  <div>
                    <h2>ATM overview</h2>
                    <p>Current cash and next-day model forecast</p>
                  </div>
                  <button
                    className="cc-link-btn"
                    onClick={() => navigate("ATMs")}
                  >
                    View all <ArrowRight size={15} />
                  </button>
                </div>
                <div className="cc-compact-table">
                  <div className="cc-table-row cc-table-head">
                    <span>ATM</span>
                    <span>Cash</span>
                    <span>Forecast</span>
                    <span>Status</span>
                    <span />
                  </div>
                  {(activeAtm ? [activeAtm] : atmRows.slice(0, 5)).map((a) => (
                    <div className="cc-table-row" key={a.id}>
                      <span>
                        <b>{a.id}</b>
                        <small>
                          {a.location}, {a.city}
                        </small>
                      </span>
                      <span>{money(a.cash)}</span>
                      <span>{money(a.forecast)}</span>
                      <span
                        className={`cc-status ${statusOf(a).toLowerCase().replace(" ", "-")}`}
                      >
                        {statusOf(a)}
                      </span>
                      <button
                        aria-label={`Open ${a.id}`}
                        onClick={() => navigate("ATMs")}
                      >
                        <ChevronRight size={15} />
                      </button>
                    </div>
                  ))}
                </div>
              </article>
              <article className="cc-ops-panel cc-replenish-preview">
                <div className="cc-panel-heading">
                  <div>
                    <h2>Replenishment</h2>
                    <p>API recommendations · simulation</p>
                  </div>
                  <button
                    className="cc-link-btn"
                    onClick={() => navigate("Replenishment")}
                  >
                    Plan <ArrowRight size={15} />
                  </button>
                </div>
                {(replenishment?.items ?? [])
                  .filter((a) => a.refill_required)
                  .slice(0, 4)
                  .map((a) => (
                    <div className="cc-refill-line" key={a.ATM_ID}>
                      <span className="cc-alert-dot" />
                      <b>{a.ATM_ID}</b>
                      <span>{a.City}</span>
                      <strong>{money(a.recommended_refill)}</strong>
                      <button
                        disabled={isViewer}
                        onClick={() => dispatch([a.ATM_ID])}
                      >
                        Dispatch
                      </button>
                    </div>
                  ))}
                {!replenishment?.refill_required_count && (
                  <p className="cc-muted-copy">
                    API reports no refill recommendations.
                  </p>
                )}
              </article>
            </div>
            <div className="cc-ops-lower-grid">
              <article className="cc-ops-panel">
                <div className="cc-panel-heading">
                  <div>
                    <h2>Model performance</h2>
                    <p>Chronological holdout · historical simulation</p>
                  </div>
                </div>
                <div className="cc-performance">
                  <span>
                    Forecast accuracy <b>{pct(activeAtm?.accuracy ?? metrics?.accuracy_percent)}</b>
                  </span>
                  <span>
                    MAPE <b>{pct(metrics?.mape_percent)}</b>
                  </span>
                  <span>
                    MAE <b>{money(metrics?.mae)}</b>
                  </span>
                  <span>
                    R²{" "}
                    <b>
                      {Number.isFinite(Number(metrics?.r2))
                        ? Number(metrics.r2).toFixed(3)
                        : "—"}
                    </b>
                  </span>
                  <span>
                    7-day baseline MAPE{" "}
                    <b>{pct(metrics?.baseline_mape_percent)}</b>
                  </span>
                </div>
              </article>
              <article className="cc-ops-panel">
                <div className="cc-panel-heading">
                  <div>
                    <h2>Cash-out replay</h2>
                    <p>Day-by-day test-period simulation</p>
                  </div>
                </div>
                <div className="cc-insight-row">
                  <span>Fixed-threshold simulated cash-outs</span>
                  <b>{metrics?.backtest?.fixed_threshold?.cashouts ?? "—"}</b>
                </div>
                <div className="cc-insight-row">
                  <span>Forecast-policy simulated cash-outs</span>
                  <b>
                    {metrics?.backtest?.forecast_threshold?.cashouts ?? "—"}
                  </b>
                </div>
                <div className="cc-insight-row">
                  <span>Data ending</span>
                  <b>{metrics?.data_end ?? "—"}</b>
                </div>
              </article>
            </div>
          </>
        )}
        {page === "ATMs" && (
          <section className="cc-ops-page">
            <div className="cc-page-title">
              <div>
                <h1>ATM network</h1>
                <p>
                  {matches.length} of {atmRows.length} ATMs · cash and next-day
                  forecast from the API
                </p>
              </div>
              <button className="cc-briefing" onClick={() => setQuery("")}>
                Clear search
              </button>
            </div>
            <div className="cc-ops-panel cc-page-table">
              <div className="cc-compact-table">
                <div className="cc-table-row cc-table-head atm-table">
                  <span>ATM / Location</span>
                  <span>Capacity</span>
                  <span>Cash</span>
                  <span>Fill</span>
                  <span>Forecast</span>
                  <span>Cover</span>
                  <span>Accuracy</span>
                  <span>Status</span>
                </div>
                {matches.map((a) => (
                  <button
                    className="cc-table-row atm-table"
                    key={a.id}
                    onClick={() => {
                      setActiveAtm(a);
                      setPage("Overview");
                    }}
                  >
                    <span>
                      <b>{a.id}</b>
                      <small>
                        {a.location}, {a.city}
                      </small>
                    </span>
                    <span>{money(a.cap)}</span>
                    <span>{money(a.cash)}</span>
                    <span>{pct(a.fill)}</span>
                    <span>{money(a.forecast)}</span>
                    <span>
                      {Number.isFinite(a.days)
                        ? `${a.days.toFixed(1)} days`
                        : "—"}
                    </span>
                    <span>{pct(a.accuracy)}</span>
                    <span
                      className={`cc-status ${statusOf(a).toLowerCase().replace(" ", "-")}`}
                    >
                      {statusOf(a)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </section>
        )}
        {page === "What-if forecast" && (
          <section className="cc-ops-page">
            <div className="cc-page-title">
              <div>
                <h1>What-if forecast</h1>
                <p>
                  Model estimates from the API with your selected calendar
                  assumptions.
                </p>
              </div>
            </div>
            <div className="cc-whatif-layout">
              <article className="cc-ops-panel cc-whatif-controls">
                <h2>Scenario assumptions</h2>
                <label className="cc-check-row">
                  <input
                    type="checkbox"
                    checked={festival}
                    onChange={(e) => setFestival(e.target.checked)}
                  />
                  <span>
                    <b>Festival tomorrow</b>
                    <small>Set the model’s festival input</small>
                  </span>
                </label>
                <label className="cc-check-row">
                  <input
                    type="checkbox"
                    checked={holiday}
                    onChange={(e) => setHoliday(e.target.checked)}
                  />
                  <span>
                    <b>Public holiday</b>
                    <small>Set the model’s holiday input</small>
                  </span>
                </label>
                <label className="cc-slider-label">
                  Demand adjustment <b>{adjust > 0 ? `+${adjust}` : adjust}%</b>
                  <input
                    type="range"
                    min="-30"
                    max="50"
                    value={adjust}
                    onChange={(e) => setAdjust(Number(e.target.value))}
                  />
                </label>
                <p className="cc-muted-copy">
                  Scenario outputs are estimates, labeled as simulation.
                </p>
              </article>
              <article className="cc-ops-panel cc-scenario-results">
                <h2>Adjusted ATM demand</h2>
                <p>API model estimates · INR</p>
                <div className="cc-compact-table">
                  <div className="cc-table-row cc-table-head">
                    <span>ATM</span>
                    <span>Base forecast</span>
                    <span>Scenario</span>
                    <span>Cash cover</span>
                  </div>
                  {whatif
                    .filter((a) =>
                      `${a.ATM_ID} ${a.Location} ${a.City}`
                        .toLowerCase()
                        .includes(query.toLowerCase()),
                    )
                    .map((a) => (
                      <div className="cc-table-row" key={a.ATM_ID}>
                        <span>
                          <b>{a.ATM_ID}</b>
                          <small>
                            {a.Location}, {a.City}
                          </small>
                        </span>
                        <span>{money(a.base_forecast)}</span>
                        <span>{money(a.forecast)}</span>
                        <span>
                          {a.days_of_cover == null
                            ? "—"
                            : `${a.days_of_cover.toFixed(1)} days`}
                        </span>
                      </div>
                    ))}
                </div>
              </article>
            </div>
          </section>
        )}
        {page === "Replenishment" && (
          <section className="cc-ops-page">
            <div className="cc-page-title">
              <div>
                <h1>Replenishment plan</h1>
                <p>
                  Recommendations and simulated dispatches supplied by the API.
                </p>
              </div>
              <button className="cc-secondary-action" onClick={copyCsv}>
                Copy CSV
              </button>
            </div>
            <div className="cc-whatif-layout">
              <article className="cc-ops-panel">
                <div className="cc-panel-heading">
                  <div>
                    <h2>ATMs to replenish</h2>
                    <p>
                      {replenishment?.refill_required_count ?? 0}{" "}
                      recommendations · select ATMs for a simulated dispatch
                    </p>
                  </div>
                  <button
                    className="cc-link-btn"
                    onClick={() =>
                      setSelected(
                        (replenishment?.items ?? [])
                          .filter((a) => a.refill_required)
                          .map((a) => a.ATM_ID),
                      )
                    }
                  >
                    Select suggested
                  </button>
                </div>
                <div className="cc-replen-list">
                  {(replenishment?.items ?? []).map((a) => (
                    <label className="cc-replen-item" key={a.ATM_ID}>
                      <input
                        type="checkbox"
                        checked={selected.includes(a.ATM_ID)}
                        disabled={!a.refill_required}
                        onChange={(e) =>
                          setSelected((old) =>
                            e.target.checked
                              ? [...old, a.ATM_ID]
                              : old.filter((id) => id !== a.ATM_ID),
                          )
                        }
                      />
                      <span>
                        <b>
                          {a.ATM_ID} · {a.Location}, {a.City}
                        </b>
                        <small>
                          {money(a.current_cash)} cash ·{" "}
                          {a.days_of_cover == null
                            ? "—"
                            : `${a.days_of_cover.toFixed(1)} days cover`}
                        </small>
                      </span>
                      <strong>{money(a.recommended_refill)}</strong>
                      <span
                        className={`cc-status ${String(a.urgency).toLowerCase()}`}
                      >
                        {a.status}
                      </span>
                    </label>
                  ))}
                </div>
                <button
                  className="cc-schedule-btn"
                  disabled={isViewer || selected.length === 0}
                  onClick={() => dispatch(selected)}
                >
                  {isViewer ? "Viewer cannot dispatch" : "Schedule selected"}
                  <ArrowRight size={16} />
                </button>
              </article>
              <article className="cc-ops-panel cc-van-card">
                <h2>Dispatch estimate</h2>
                <p>
                  Enter van capacity to calculate trips; this is a user supplied
                  planning value.
                </p>
                <label>
                  Cash per van (₹ lakh)
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={vanCapacity}
                    onChange={(e) => setVanCapacity(e.target.value)}
                    placeholder="e.g. 20"
                  />
                </label>
                <div className="cc-trip-result">
                  <span>Selected ATMs</span>
                  <b>{selectedRows.length}</b>
                </div>
                <div className="cc-trip-result">
                  <span>Selected refill total</span>
                  <b>
                    {money(selectedRows.reduce((sum, a) => sum + a.refill, 0))}
                  </b>
                </div>
                <div className="cc-trip-result">
                  <span>Estimated trips</span>
                  <b>
                    {Number(vanCapacity) > 0
                      ? Math.ceil(
                          selectedRows.reduce((sum, a) => sum + a.refill, 0) /
                            (Number(vanCapacity) * 100_000),
                        )
                      : "—"}
                  </b>
                </div>
                <h3>Recent dispatches · simulation</h3>
                {dispatches.slice(0, 5).map((d) => (
                  <div className="cc-insight-row" key={d.id}>
                    <span>
                      {d.atm_id} · {d.status}
                    </span>
                    <b>{money(d.amount)}</b>
                  </div>
                ))}
              </article>
            </div>
          </section>
        )}
        {page === "Alerts" && (
          <section className="cc-ops-page">
            <div className="cc-page-title">
              <div>
                <h1>Alerts</h1>
                <p>
                  API-generated cash-cover and replenishment alerts · simulation
                </p>
              </div>
              <span className="cc-status critical">
                {
                  alerts.filter(
                    (a) => a.urgency === "CRITICAL" && !a.acknowledged,
                  ).length
                }{" "}
                critical
              </span>
            </div>
            <div className="cc-alert-list">
              {alerts.map((a) => (
                <article
                  className={`cc-ops-panel cc-alert-card${a.acknowledged ? " acknowledged" : ""}`}
                  key={a.id}
                >
                  <span className="cc-alert-icon">
                    <Bell size={18} />
                  </span>
                  <div>
                    <b>
                      {a.urgency} · {a.ATM_ID}
                    </b>
                    <p>
                      {a.Location}, {a.City} ·{" "}
                      {a.days_of_cover == null
                        ? "—"
                        : `${a.days_of_cover.toFixed(1)} days of cash cover`}{" "}
                      · suggested refill {money(a.recommended_refill)}.
                    </p>
                  </div>
                  <div className="cc-alert-actions">
                    <button
                      disabled={a.acknowledged}
                      onClick={() => acknowledge(a.id)}
                    >
                      {a.acknowledged ? "Acknowledged" : "Acknowledge"}
                    </button>
                    <button
                      disabled={isViewer}
                      onClick={() => dispatch([a.ATM_ID])}
                    >
                      Dispatch
                    </button>
                  </div>
                </article>
              ))}
              {!alerts.length && (
                <article className="cc-ops-panel">
                  <p>No active alerts were returned by the API.</p>
                </article>
              )}
            </div>
          </section>
        )}
        {page === "Settings" && (
          <section className="cc-ops-page">
            <div className="cc-page-title">
              <div>
                <h1>Settings</h1>
                <p>Account access and network cash-cover preferences.</p>
              </div>
              <button className="cc-signout" onClick={onSignOut}>
                Sign out <LogOut size={16} />
              </button>
            </div>
            <div className="cc-settings-layout">
              <article className="cc-ops-panel">
                <h2>Account access</h2>
                <div className="cc-setting-line">
                  <span>Signed in as</span>
                  <b>{email}</b>
                </div>
                <div className="cc-setting-line">
                  <span>Role</span>
                  <b>{role}</b>
                </div>
                <div className="cc-setting-line">
                  <span>Organization</span>
                  <b>Bank Muscat</b>
                </div>
                <p className="cc-muted-copy">
                  Demo only · historical simulation data.
                </p>
              </article>
              <article className="cc-ops-panel">
                <h2>Cash-cover preferences</h2>
                <label className="cc-slider-label">
                  Critical below <b>{criticalThreshold.toFixed(1)} days</b>
                  <input
                    type="range"
                    min="0.5"
                    max="2.5"
                    step="0.1"
                    value={criticalThreshold}
                    disabled={role !== "Admin"}
                    onChange={(e) =>
                      setCriticalThreshold(Number(e.target.value))
                    }
                  />
                </label>
                <label className="cc-slider-label">
                  Refill soon below <b>{threshold.toFixed(1)} days</b>
                  <input
                    type="range"
                    min="1.5"
                    max="6"
                    step="0.5"
                    value={threshold}
                    disabled={role !== "Admin"}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                  />
                </label>
                {role !== "Admin" && (
                  <p className="cc-muted-copy">
                    Only Admin can adjust these local display preferences.
                  </p>
                )}
                <button
                  className="cc-secondary-action"
                  onClick={() => setDark(!dark)}
                >
                  {dark ? "Use light theme" : "Use dark theme"}
                </button>
              </article>
            </div>
          </section>
        )}
      </div>
      {briefOpen && (
        <div
          className="cc-briefing-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setBriefOpen(false);
          }}
        >
          <section
            className="cc-briefing-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cc-briefing-title"
          >
            <button
              className="cc-login-close"
              aria-label="Close briefing"
              onClick={() => setBriefOpen(false)}
            >
              <X size={18} />
            </button>
            <span className="cc-feature-icon">
              <FileText size={21} />
            </span>
            <h2 id="cc-briefing-title">Daily network briefing</h2>
            <p>
              The API reports {metrics?.atm_count ?? "—"} ATMs, forecast
              accuracy {pct(metrics?.accuracy_percent)}, and {alerts.length}{" "}
              active alerts. Forecast-based cash-out reduction is{" "}
              {pct(metrics?.cashout_reduction_percent)} in a day-by-day
              test-period simulation.
            </p>
            <small>
              Historical simulation · dataset coverage {days} · amounts in
              Indian rupees.
            </small>
            <button
              className="cc-schedule-btn"
              onClick={() => {
                setBriefOpen(false);
                navigate("Replenishment");
              }}
            >
              Review replenishment plan <ArrowRight size={16} />
            </button>
          </section>
        </div>
      )}
      {toast && (
        <div className="cc-ops-toast">
          <Check size={17} />
          {toast}
        </div>
      )}
    </main>
  );
}

export function DashboardPreview({ expanded = false, role, email, token, onSignOut }) {
  return expanded ? <CashDashboard role={role} email={email} token={token} onSignOut={onSignOut}/> : <DashboardPreviewMini/>;
}

export default function CashCast({ onOpenDashboard }) {
  return <Landing onOpenDashboard={onOpenDashboard}/>;
}
