<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中国中铁物联网平台 · 技术汇报演讲稿</title>
<meta name="description" content="中国中铁物联网平台技术汇报演讲稿：信创可扩展、自主可控、AI 辅助、融合终端接入、腾讯云 IoT 兼容。">
<style>
:root{
  --ink:#101b2d; --ink-2:#1d2b42; --ink-3:#4a5a72; --ink-4:#7d8ba0;
  --paper:#f6f5f1; --card:#ffffff; --line:#e3e0d8; --line-2:#cfcbc0;
  --accent:#0e7c6b; --accent-2:#0b5f52; --accent-soft:#e7f3f0;
  --amber:#b4690e; --amber-soft:#fbf1e2;
  --red:#a63a34; --red-soft:#f9e9e7;
  --blue:#2f5d8a; --blue-soft:#eaf0f7;
  --mono:"Cascadia Code","JetBrains Mono",Consolas,"Courier New",monospace;
  --sans:"PingFang SC","Microsoft YaHei","Noto Sans SC","Segoe UI",system-ui,-apple-system,sans-serif;
  --serif:"Source Han Serif SC","Songti SC","Noto Serif SC","STSong",serif;
  --shadow:0 1px 2px rgba(16,27,45,.05),0 8px 28px -18px rgba(16,27,45,.25);
  --radius:10px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--sans); font-size:16px; line-height:1.85;
  -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(rgba(16,27,45,.025) 1px, transparent 1px);
  background-size:22px 22px;
}
::selection{background:#bfe5dd; color:var(--ink)}

/* ============ 顶栏 ============ */
.topbar{
  position:fixed; inset:0 0 auto 0; height:54px; z-index:60;
  display:flex; align-items:center; gap:16px; padding:0 22px;
  background:rgba(246,245,241,.88); backdrop-filter:blur(10px);
  border-bottom:1px solid var(--line);
}
.topbar .brand{font-weight:700; letter-spacing:.02em; font-size:14px; display:flex; align-items:center; gap:9px; white-space:nowrap}
.topbar .brand .dot{width:9px; height:9px; border-radius:2px; background:var(--accent); box-shadow:0 0 0 3px var(--accent-soft)}
.topbar .sep{color:var(--line-2)}
.topbar .doc{color:var(--ink-3); font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.topbar .spacer{flex:1}
.topbar .tools{display:flex; align-items:center; gap:6px}
.btn{
  border:1px solid var(--line-2); background:var(--card); color:var(--ink-2);
  font:inherit; font-size:12.5px; line-height:1; padding:8px 12px; border-radius:7px;
  cursor:pointer; display:inline-flex; align-items:center; gap:6px; white-space:nowrap;
  transition:border-color .15s, background .15s, color .15s;
}
.btn:hover{border-color:var(--accent); color:var(--accent-2)}
.btn.on{background:var(--accent); border-color:var(--accent); color:#fff}
.btn.ghost{background:transparent}
.progress{position:fixed; top:54px; left:0; height:2px; width:0%; background:linear-gradient(90deg,var(--accent),#3aa08f); z-index:61; transition:width .1s linear}

/* ============ 侧栏目录 ============ */
.side{
  position:fixed; top:54px; bottom:0; left:0; width:258px; z-index:50;
  overflow-y:auto; padding:24px 18px 40px 22px; border-right:1px solid var(--line);
  background:rgba(250,249,246,.72); backdrop-filter:blur(6px);
}
.side h4{
  margin:18px 0 8px; font-size:11px; letter-spacing:.16em; color:var(--ink-4);
  font-weight:700; text-transform:uppercase;
}
.side h4:first-child{margin-top:0}
.side a{
  display:flex; gap:9px; align-items:baseline; padding:5px 8px 5px 10px; margin:1px 0;
  color:var(--ink-3); text-decoration:none; font-size:13px; line-height:1.5;
  border-left:2px solid transparent; border-radius:0 6px 6px 0;
}
.side a:hover{color:var(--ink); background:#f0eee8}
.side a .no{
  font-family:var(--mono); font-size:10.5px; color:var(--ink-4); min-width:22px;
  flex:none; padding-top:1px;
}
.side a.active{color:var(--accent-2); border-left-color:var(--accent); background:var(--accent-soft); font-weight:600}
.side a.active .no{color:var(--accent)}
.side .meta{margin-top:22px; padding-top:14px; border-top:1px dashed var(--line-2); font-size:11.5px; color:var(--ink-4); line-height:1.7}

/* ============ 主体 ============ */
main{margin-left:258px; padding:54px 0 120px}
.wrap{max-width:1080px; margin:0 auto; padding:0 40px}
section{scroll-margin-top:76px}

/* 封面 */
.cover{position:relative; overflow:hidden; padding:84px 0 64px; border-bottom:1px solid var(--line)}
.cover:before{
  content:""; position:absolute; right:-160px; top:-120px; width:560px; height:560px;
  background:radial-gradient(circle at 30% 30%, rgba(14,124,107,.14), rgba(14,124,107,0) 62%);
  pointer-events:none;
}
.cover .kicker{
  display:inline-flex; align-items:center; gap:8px; font-size:12px; letter-spacing:.14em;
  color:var(--accent-2); background:var(--accent-soft); border:1px solid #cfe7e1;
  padding:5px 11px; border-radius:999px; font-weight:600;
}
.cover h1{
  font-family:var(--serif); font-size:clamp(34px,4.2vw,52px); line-height:1.22;
  margin:22px 0 14px; letter-spacing:.01em; font-weight:700;
}
.cover h1 em{font-style:normal; color:var(--accent-2); position:relative; white-space:nowrap}
.cover h1 em:after{
  content:""; position:absolute; left:0; right:0; bottom:-4px; height:8px;
  background:linear-gradient(90deg, rgba(14,124,107,.18), rgba(14,124,107,.02)); z-index:-1;
}
.cover .sub{font-size:17.5px; color:var(--ink-3); max-width:760px; margin:0 0 26px}
.cover .meta-row{display:flex; flex-wrap:wrap; gap:10px 26px; font-size:13px; color:var(--ink-4); margin-bottom:34px}
.cover .meta-row b{color:var(--ink-2); font-weight:600}

/* 五柱 */
.pillars{display:grid; grid-template-columns:repeat(5,1fr); gap:10px}
.pillar{
  background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  padding:14px 14px 15px; box-shadow:var(--shadow); position:relative;
}
.pillar .n{font-family:var(--mono); font-size:11px; color:var(--accent); letter-spacing:.08em}
.pillar h3{font-size:14.5px; margin:6px 0 6px; line-height:1.35}
.pillar p{margin:0; font-size:11.8px; color:var(--ink-4); line-height:1.65}
.pillar.demo{border-color:#cfe7e1; background:linear-gradient(180deg,#fff, #f7fcfb)}
.pillar.demo:after{
  content:"演示"; position:absolute; top:-8px; right:10px; font-size:10px; font-weight:700;
  color:#fff; background:var(--accent); padding:2px 7px; border-radius:999px; letter-spacing:.05em;
}

/* 章节头 */
.chapter{padding:64px 0 8px; border-top:1px solid var(--line); margin-top:8px}
.chapter .num{
  font-family:var(--mono); font-size:13px; color:var(--accent); letter-spacing:.22em;
  display:flex; align-items:center; gap:12px;
}
.chapter .num:after{content:""; height:1px; width:64px; background:var(--accent); opacity:.4}
.chapter h2{font-family:var(--serif); font-size:30px; margin:10px 0 8px; letter-spacing:.01em}
.chapter .lede{color:var(--ink-3); font-size:15px; max-width:820px; margin:0}
.chapter .chips{display:flex; flex-wrap:wrap; gap:8px; margin-top:16px}
.chip{
  font-size:12px; color:var(--ink-3); background:var(--card); border:1px solid var(--line);
  padding:4px 10px; border-radius:999px;
}
.chip b{color:var(--ink); font-weight:600}

/* 页面卡片 = 一页 PPT */
.slide{
  background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  box-shadow:var(--shadow); margin:26px 0; overflow:hidden;
  break-inside:avoid;
}
.slide .bar{
  display:flex; align-items:center; gap:12px; padding:11px 18px;
  border-bottom:1px solid var(--line); background:#fcfbf8;
}
.slide .bar .pg{
  font-family:var(--mono); font-size:11px; font-weight:700; color:#fff; background:var(--ink-2);
  padding:2px 7px; border-radius:4px; letter-spacing:.04em;
}
.slide .bar .ttl{font-weight:700; font-size:13.5px; letter-spacing:.01em}
.slide .bar .tag{
  margin-left:auto; font-size:11px; color:var(--ink-4); border:1px solid var(--line-2);
  padding:2px 8px; border-radius:999px; white-space:nowrap;
}
.slide .bar .tag.blue{color:var(--blue); border-color:#cfddeb; background:var(--blue-soft)}
.slide .bar .tag.green{color:var(--accent-2); border-color:#cfe7e1; background:var(--accent-soft)}
.slide .bar .tag.amber{color:var(--amber); border-color:#eddcc0; background:var(--amber-soft)}
.slide .body{padding:22px 26px 8px}
.slide h3.pt{font-size:20px; line-height:1.45; margin:0 0 4px; letter-spacing:.005em}
.slide .subpt{color:var(--ink-3); font-size:13.5px; margin:0 0 16px}
.slide .hint{margin:2px 0 16px; font-size:12.5px; color:var(--ink-4); display:flex; gap:8px; align-items:flex-start}
.slide .hint:before{content:"版式"; flex:none; font-size:10px; letter-spacing:.08em; color:var(--accent-2); border:1px solid #cfe7e1; background:var(--accent-soft); padding:1px 6px; border-radius:4px; margin-top:3px}

/* 讲稿区 */
.note{
  display:grid; grid-template-columns:104px 1fr; gap:18px;
  padding:18px 26px 22px; border-top:1px dashed var(--line-2); background:#fbfaf7;
}
.note .label{
  font-size:11px; letter-spacing:.14em; color:var(--ink-4); font-weight:700;
  text-transform:uppercase; padding-top:3px;
}
.note .label small{display:block; letter-spacing:0; text-transform:none; font-weight:400; color:var(--ink-4); font-size:10.5px; margin-top:3px}
.note .say{font-size:15.2px; line-height:1.95; color:#26344b; margin:0}
.note .say p{margin:0 0 10px}
.note .say p:last-child{margin-bottom:0}
.note .say strong{color:var(--ink); font-weight:700; background:linear-gradient(transparent 62%, #d8ece7 62%)}
.note .say .q{color:var(--accent-2); font-weight:600}
.note .say .beat{color:var(--amber); font-size:12.5px; border:1px solid #eddcc0; background:var(--amber-soft); padding:1px 7px; border-radius:4px; white-space:nowrap}

/* 要点列表 */
ul.pts{list-style:none; margin:0 0 16px; padding:0; display:grid; gap:10px}
ul.pts li{position:relative; padding-left:22px; font-size:15px; line-height:1.75; color:var(--ink-2)}
ul.pts li:before{
  content:""; position:absolute; left:2px; top:.62em; width:7px; height:7px; border-radius:2px;
  background:var(--accent); opacity:.85;
}
ul.pts li b{font-weight:700; color:var(--ink)}
ul.pts li span{display:block; color:var(--ink-4); font-size:13px; line-height:1.7; margin-top:2px}
ul.pts.tight{gap:7px}
ul.pts.tight li{font-size:14.5px}

/* 表格 */
.tbl{width:100%; border-collapse:collapse; margin:4px 0 18px; font-size:13.6px}
.tbl th,.tbl td{border:1px solid var(--line); padding:9px 12px; text-align:left; vertical-align:top; line-height:1.6}
.tbl th{background:#f3f1eb; font-weight:700; color:var(--ink); white-space:nowrap}
.tbl td{color:var(--ink-2)}
.tbl tr:nth-child(even) td{background:#fcfbf8}
.tbl .num{font-family:var(--mono); font-size:13px; white-space:nowrap}
.tbl.cmp td:first-child{font-weight:600; white-space:nowrap}
.mark{font-weight:700; color:var(--accent-2)}
.mark.bad{color:var(--red)}

/* 双栏 / 三栏 */
.cols{display:grid; gap:16px; margin:0 0 18px}
.cols.c2{grid-template-columns:1fr 1fr}
.cols.c3{grid-template-columns:repeat(3,1fr)}
.cardlet{border:1px solid var(--line); border-radius:8px; padding:14px 16px; background:#fcfbf8}
.cardlet h4{margin:0 0 6px; font-size:14px; display:flex; align-items:center; gap:7px}
.cardlet h4 .ic{font-family:var(--mono); font-size:11px; color:#fff; background:var(--accent); border-radius:4px; padding:1px 5px}
.cardlet p{margin:0; font-size:13px; color:var(--ink-3); line-height:1.7}
.cardlet.amber{background:var(--amber-soft); border-color:#eddcc0}
.cardlet.red{background:var(--red-soft); border-color:#eed3d0}
.cardlet.blue{background:var(--blue-soft); border-color:#cfddeb}

/* 演示块 */
.demo{border:1px solid #c9e4de; border-radius:var(--radius); overflow:hidden; margin:22px 0}
.demo .hd{
  display:flex; align-items:center; gap:12px; padding:13px 20px;
  background:linear-gradient(90deg, #0e7c6b, #137f6d 55%, #1a8a76); color:#fff;
}
.demo .hd .badge{font-size:10.5px; letter-spacing:.14em; border:1px solid rgba(255,255,255,.45); padding:2px 7px; border-radius:999px; font-weight:700}
.demo .hd .t{font-weight:700; font-size:15px}
.demo .hd .dur{margin-left:auto; font-family:var(--mono); font-size:11.5px; opacity:.85; white-space:nowrap}
.demo .bd{padding:16px 20px 8px; background:#fbfdfc}
.demo .goal{font-size:13.5px; color:var(--ink-3); margin:0 0 14px}
.demo .goal b{color:var(--accent-2)}
.steps{list-style:none; counter-reset:s; margin:0 0 14px; padding:0; display:grid; gap:9px}
.steps li{counter-increment:s; position:relative; padding-left:34px; font-size:13.8px; line-height:1.7; color:var(--ink-2)}
.steps li:before{
  content:counter(s); position:absolute; left:0; top:.15em; width:22px; height:22px; border-radius:50%;
  background:#fff; border:1.5px solid var(--accent); color:var(--accent-2); font-family:var(--mono);
  font-size:11px; font-weight:700; display:flex; align-items:center; justify-content:center;
}
.steps li b{color:var(--ink)}
.steps li code{font-family:var(--mono); font-size:12.5px; background:#eef5f3; border:1px solid #dbebe7; padding:1px 5px; border-radius:4px; color:#0b5f52; white-space:nowrap}
.demo .expect{
  border-top:1px dashed #cfe7e1; padding:11px 0 4px; margin-top:2px;
  display:grid; grid-template-columns:78px 1fr; gap:12px; font-size:13.4px;
}
.demo .expect .k{font-size:11px; letter-spacing:.08em; color:var(--accent-2); font-weight:700; padding-top:2px}
.demo .expect .v{color:var(--ink-3)}
.demo .expect .v b{color:var(--ink)}
.fallback{
  margin:12px 0 14px; border:1px solid #eddcc0; background:var(--amber-soft); border-radius:8px;
  padding:10px 14px; font-size:13px; color:#6b4a14; line-height:1.7;
}
.fallback b{color:#8a5a10}
.fallback .k{font-size:10.5px; letter-spacing:.1em; font-weight:700; margin-right:8px; color:#8a5a10}

/* 演讲提示（口播替代） */
.spoken{
  border-left:3px solid var(--accent); background:#fff; padding:11px 15px; margin:14px 0 16px;
  font-size:13.6px; color:var(--ink-2); line-height:1.8; border-radius:0 8px 8px 0;
}
.spoken:before{content:"现场口播"; display:block; font-size:10.5px; letter-spacing:.12em; color:var(--accent-2); font-weight:700; margin-bottom:3px}

/* 代码 */
pre{
  background:#101b2d; color:#d7e2f0; border-radius:8px; padding:14px 16px; overflow-x:auto;
  font-family:var(--mono); font-size:12.6px; line-height:1.65; margin:0 0 16px; position:relative;
}
pre .c{color:#7d93ad}
pre .k{color:#7fd0bd}
pre .s{color:#e6c07b}
code.inl{font-family:var(--mono); font-size:.9em; background:#eff1ee; border:1px solid var(--line); padding:1px 5px; border-radius:4px; color:#0b5f52}

/* 分节提示条 */
.rule{display:flex; align-items:center; gap:14px; margin:44px 0 4px; color:var(--ink-4); font-size:11.5px; letter-spacing:.14em}
.rule:before,.rule:after{content:""; height:1px; flex:1; background:var(--line-2)}

/* 时间轴 */
.timeline{display:grid; gap:0; margin:6px 0 18px; border-left:2px solid var(--line-2); padding-left:0}
.timeline .row{display:grid; grid-template-columns:96px 1fr; gap:16px; padding:9px 0 9px 18px; position:relative}
.timeline .row:before{content:""; position:absolute; left:-5px; top:18px; width:8px; height:8px; border-radius:50%; background:var(--accent); border:2px solid var(--paper)}
.timeline .t{font-family:var(--mono); font-size:12.5px; color:var(--accent-2); font-weight:700; padding-top:3px}
.timeline .d{font-size:13.6px; color:var(--ink-2); line-height:1.65}
.timeline .d b{color:var(--ink)}
.timeline .d span{display:block; color:var(--ink-4); font-size:12.5px}

/* 页脚 */
footer{margin:70px 0 0; padding:28px 0 0; border-top:1px solid var(--line); color:var(--ink-4); font-size:12.5px; line-height:1.8}
footer b{color:var(--ink-3)}
.backtop{position:fixed; right:26px; bottom:26px; z-index:55}

/* 演示模式（放大口播） */
body.speak .slide .body{opacity:.34; filter:grayscale(.4); transition:.25s}
body.speak .demo .bd{opacity:.4; filter:grayscale(.4)}
body.speak .note .say{font-size:19px; line-height:2.05}
body.speak .spoken{font-size:15.5px}
body.speak .slide{border-color:#d7d2c6}

@media (max-width:1180px){
  .pillars{grid-template-columns:repeat(3,1fr)}
  .pillars .pillar:nth-child(4),.pillars .pillar:nth-child(5){grid-column:span 1}
}
@media (max-width:960px){
  .side{display:none}
  main{margin-left:0}
  .wrap{padding:0 22px}
  .cols.c2,.cols.c3{grid-template-columns:1fr}
  .pillars{grid-template-columns:1fr 1fr}
  .note{grid-template-columns:1fr; gap:6px}
  .topbar .doc{display:none}
}
@media print{
  @page{size:A4; margin:14mm 13mm}
  body{background:#fff; font-size:11.5pt}
  .topbar,.side,.progress,.backtop,.tools{display:none!important}
  main{margin:0; padding:0}
  .wrap{max-width:none; padding:0}
  .slide,.demo{box-shadow:none; break-inside:avoid; page-break-inside:avoid; margin:14px 0}
  .chapter{break-before:page; border-top:none; padding-top:0}
  .note{background:#fafafa}
  pre{background:#f4f4f2; color:#1d2b42; border:1px solid #ddd}
  pre .c{color:#6b7a8d} pre .k{color:#0b5f52} pre .s{color:#8a5a10}
  body.speak .slide .body{opacity:1; filter:none}
  footer{break-before:auto}
}
</style>
</head>
<body>
<div class="progress" id="progress"></div>

<header class="topbar">
  <div class="brand"><span class="dot"></span>技术汇报演讲稿</div>
  <span class="sep">/</span>
  <div class="doc">中国中铁物联网平台 · 信创底座与智能化演进</div>
  <div class="spacer"></div>
  <div class="tools">
    <button class="btn ghost" id="btnSpeak" title="放大讲稿、淡化屏显（快捷键 P）">演示模式</button>
    <button class="btn ghost" id="btnPrint" title="打印或导出 PDF（Ctrl+P）">打印 / PDF</button>
  </div>
</header>
