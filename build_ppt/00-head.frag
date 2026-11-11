<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中国中铁物联网平台 · 技术汇报</title>
<meta name="description" content="中国中铁物联网平台技术汇报投屏版：信创可扩展、自主可控、AI 辅助、融合终端接入、腾讯云 IoT 兼容。">
<style>
:root{
  --paper:#f2f1ec; --card:#ffffff; --ink:#0f1a2b; --ink-2:#233248; --ink-3:#5a6879; --ink-4:#8a95a5;
  --line:#dfdcd3; --line-2:#c9c4b8;
  --teal:#0e7c6b; --teal-2:#0a5f52; --teal-soft:#e6f2ef;
  --amber:#b4690e; --amber-soft:#fbf1e2;
  --red:#a63a34; --red-soft:#f9e9e7;
  --navy:#0b1523; --navy-2:#122135;
  --sans:"PingFang SC","Microsoft YaHei","Noto Sans SC","Segoe UI",system-ui,sans-serif;
  --serif:"Source Han Serif SC","Songti SC","Noto Serif SC","STSong",serif;
  --mono:"Cascadia Mono",Consolas,"Courier New",monospace;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#0a0f17;overflow:hidden}
body{font-family:var(--sans);color:var(--ink);-webkit-font-smoothing:antialiased}

/* ===== 舞台：16:9 ===== */
#stage{position:absolute; left:50%; top:50%; width:1280px; height:720px; transform:translate(-50%,-50%); background:var(--paper); overflow:hidden; box-shadow:0 30px 90px rgba(0,0,0,.55)}
.deck{position:absolute; inset:0}
.slide{position:absolute; inset:0; padding:64px 86px 74px; display:none; background:var(--paper); overflow:hidden}
.slide.on{display:block}
.slide:after{content:""; position:absolute; left:0; right:0; bottom:0; height:4px; background:linear-gradient(90deg,var(--teal),#3aa08f 60%,transparent)}
.slide.dark{background:radial-gradient(1200px 620px at 78% 12%, #16384a 0%, #0e2231 46%, #0a1622 100%); color:#e9eef4}
.slide.dark:after{height:5px; background:linear-gradient(90deg,#37b39c,#7fd0bd 55%,transparent)}

/* 页眉 */
.head{position:relative; margin-bottom:30px}
.kicker{display:inline-flex; align-items:center; gap:8px; font-size:12.5px; letter-spacing:.16em; font-weight:700; color:var(--teal-2); text-transform:uppercase}
.kicker:before{content:""; width:20px; height:2px; background:var(--teal)}
.title{font-family:var(--serif); font-size:41px; line-height:1.24; margin:12px 0 0; letter-spacing:.01em; font-weight:700; color:var(--ink)}
.title.sm{font-size:35px}
.sub{font-size:16.5px; color:var(--ink-3); margin:10px 0 0; line-height:1.6}
.dark .title{color:#fff}
.dark .kicker{color:#7fd0bd}
.dark .sub{color:#a9b8c8}

/* 页脚 */
.foot{position:absolute; left:86px; right:86px; bottom:28px; display:flex; align-items:center; gap:14px; font-size:11.5px; color:var(--ink-4); letter-spacing:.04em}
.foot .bar{flex:1; height:2px; background:var(--line); position:relative; overflow:hidden}
.foot .bar i{position:absolute; inset:0 auto 0 0; width:0; background:var(--teal)}
.foot .pg{font-family:var(--mono); font-size:12px; color:var(--ink-3); white-space:nowrap}
.dark .foot{color:#8fa2b4}
.dark .foot .bar{background:rgba(255,255,255,.14)}
.dark .foot .bar i{background:#7fd0bd}
.dark .foot .pg{color:#a9b8c8}

/* 通用文本块 */
.lead{font-size:19px; line-height:1.75; color:var(--ink-2); margin:0 0 22px}
.lead b{color:var(--ink); font-weight:700}
ul.b{list-style:none; margin:0; padding:0; display:grid; gap:14px}
ul.b li{position:relative; padding-left:20px; font-size:18.5px; line-height:1.6; color:var(--ink-2)}
ul.b li:before{content:""; position:absolute; left:0; top:.58em; width:8px; height:8px; border-radius:2px; background:var(--teal)}
ul.b li b{color:var(--ink); font-weight:700}
ul.b li span{color:var(--ink-3); font-size:16px}
ul.b.sm li{font-size:17px}

/* 大数字 */
.bignum{font-family:var(--serif); font-size:96px; line-height:1; color:var(--teal-2); font-weight:700; letter-spacing:-.02em}
.bignum small{font-size:26px; font-family:var(--sans); font-weight:600; color:var(--ink-3); letter-spacing:0; margin-left:10px}
.bignum .plus{font-size:56px; color:var(--teal)}

/* 卡片栅格 */
.grid{display:grid; gap:16px}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:1fr 1fr 1fr}
.g4{grid-template-columns:repeat(4,1fr)}
.card{background:var(--card); border:1px solid var(--line); border-radius:10px; padding:19px 20px}
.card h4{margin:0 0 8px; font-size:18px; display:flex; align-items:center; gap:9px; color:var(--ink)}
.card h4 .no{font-family:var(--mono); font-size:11.5px; color:#fff; background:var(--teal); border-radius:4px; padding:2px 6px; letter-spacing:.02em}
.card p{margin:0; font-size:14.5px; line-height:1.65; color:var(--ink-3)}
.card p b{color:var(--ink-2)}
.card.teal{background:var(--teal-soft); border-color:#c7e4dd}
.card.amber{background:var(--amber-soft); border-color:#ecdcbf}
.card.red{background:var(--red-soft); border-color:#eed3d0}
.card.flat{background:transparent; border-style:dashed}

/* 对比表 */
.cmp{width:100%; border-collapse:collapse; font-size:15px}
.cmp th,.cmp td{border-bottom:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; line-height:1.55}
.cmp th{font-size:12.5px; letter-spacing:.06em; color:var(--ink-4); font-weight:700; text-transform:uppercase; border-bottom:1.5px solid var(--line-2)}
.cmp td{color:var(--ink-2)}
.cmp td:first-child{color:var(--ink); font-weight:600; white-space:nowrap}
.cmp .ok{color:var(--teal-2); font-weight:700}
.cmp .no{color:var(--red); font-weight:700}
.cmp tr:last-child td{border-bottom:none}

/* 编号流程 */
.flow{display:grid; gap:12px}
.chip-flow{display:flex; align-items:center; gap:12px; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 16px; font-size:16px; color:var(--ink-2)}
.chip-flow .n{font-family:var(--mono); font-size:12px; font-weight:700; color:var(--teal-2); background:var(--teal-soft); border-radius:4px; padding:3px 7px}
.chip-flow b{color:var(--ink)}
.chip-flow .arr{margin-left:auto; color:var(--line-2); font-family:var(--mono)}

/* 架构条 */
.stack{display:grid; gap:10px}
.layer{display:flex; align-items:center; gap:16px; border:1px solid var(--line); background:var(--card); border-radius:8px; padding:13px 18px}
.layer .name{font-weight:700; font-size:17px; color:var(--ink); min-width:110px}
.layer .desc{font-size:14.5px; color:var(--ink-3); line-height:1.5}
.layer .tag{margin-left:auto; font-size:12px; color:var(--teal-2); background:var(--teal-soft); border:1px solid #c7e4dd; border-radius:999px; padding:3px 10px; white-space:nowrap}

/* 页脚水印编号 */
.slide[data-num]{position:absolute}
.slide[data-num]:before{
  content:attr(data-num); position:absolute; right:50px; bottom:30px; z-index:0; pointer-events:none;
  font-family:var(--serif); font-size:118px; font-weight:700; line-height:.82; letter-spacing:-.03em;
  color:rgba(14,124,107,.07); font-feature-settings:"tnum";
}
.slide > *{position:relative; z-index:1}
.slide > .foot{z-index:2}
.slide.dark[data-num]:before{display:none}

/* 页脚要点条 */
.kt-bar{
  position:absolute; left:86px; bottom:52px; z-index:1; max-width:900px;
  display:inline-flex; align-items:center; gap:11px;
  font-size:12.5px; letter-spacing:.03em; color:var(--ink-3); white-space:nowrap;
  border-left:3px solid var(--teal); background:rgba(14,124,107,.055); border-radius:0 4px 4px 0;
  padding:5px 14px 5px 11px;
}
.kt-bar b{font-size:10.5px; letter-spacing:.14em; color:var(--teal-2); font-weight:800; flex:none}
.kt-bar span{overflow:hidden; text-overflow:ellipsis}
.slide.dark .kt-bar{display:none}

/* 演示角标 */
.demo-tag{position:absolute; top:40px; right:86px; display:flex; align-items:center; gap:9px; font-size:13px; font-weight:800; letter-spacing:.14em; color:#fff; background:var(--teal); padding:8px 14px; border-radius:6px; box-shadow:0 6px 18px rgba(14,124,107,.25)}
.demo-tag i{width:7px; height:7px; border-radius:50%; background:#fff; animation:pulse 1.6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
.steps{list-style:none; counter-reset:s; margin:0; padding:0; display:grid; gap:13px}
.steps li{counter-increment:s; position:relative; padding-left:42px; font-size:17px; line-height:1.55; color:var(--ink-2)}
.steps li:before{content:counter(s); position:absolute; left:0; top:.05em; width:27px; height:27px; border-radius:50%; border:2px solid var(--teal); color:var(--teal-2); background:#fff; font-family:var(--mono); font-size:12.5px; font-weight:700; display:flex; align-items:center; justify-content:center}
.steps li b{color:var(--ink)}
.done-row{display:flex; gap:12px; margin-top:22px}
.done{flex:1; border-radius:8px; border:1px solid #c7e4dd; background:var(--teal-soft); padding:12px 15px; font-size:14.5px; line-height:1.55; color:var(--teal-2)}
.done b{display:block; font-size:12px; letter-spacing:.1em; margin-bottom:3px}

/* 封面 */
.cover{position:absolute; inset:0; padding:88px 90px; display:flex; flex-direction:column; justify-content:center}
.cover .eyebrow{display:inline-flex; gap:10px; align-items:center; font-size:13px; letter-spacing:.2em; color:#7fd0bd; font-weight:700}
.cover .eyebrow:before{content:""; width:34px; height:2px; background:#37b39c}
.cover h1{font-family:var(--serif); font-size:64px; line-height:1.16; margin:24px 0 0; color:#fff; font-weight:700; letter-spacing:.01em}
.cover h1 em{font-style:normal; color:#7fd0bd}
.cover .desc{margin:22px 0 0; font-size:18px; color:#b6c5d4; max-width:820px; line-height:1.65}
.cover .meta{margin-top:26px; display:flex; gap:34px; font-size:13.5px; color:#8fa2b4}
.cover .meta b{color:#dbe6ef; font-weight:600}
.cover .pillars{display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-top:44px; max-width:1130px}
.cover .p{border:1px solid rgba(127,208,189,.28); background:rgba(255,255,255,.045); border-radius:8px; padding:14px 15px}
.cover .p .n{font-family:var(--mono); font-size:11px; color:#7fd0bd; letter-spacing:.1em}
.cover .p h4{margin:6px 0 4px; font-size:15px; color:#fff; font-weight:700; line-height:1.3}
.cover .p p{margin:0; font-size:11.5px; line-height:1.5; color:#93a6b8}

/* 目录 */
.agenda{display:grid; grid-template-columns:1fr 1fr; gap:14px 26px}
.ag{display:flex; gap:16px; align-items:flex-start; border-bottom:1px solid var(--line); padding:14px 0}
.ag .no{font-family:var(--mono); font-size:13px; font-weight:700; color:var(--teal); min-width:26px; padding-top:4px}
.ag h4{margin:0 0 3px; font-size:19px; color:var(--ink)}
.ag p{margin:0; font-size:13.5px; color:var(--ink-3); line-height:1.55}
.ag .time{margin-left:auto; font-family:var(--mono); font-size:12.5px; color:var(--ink-4); white-space:nowrap}
.ag.demo h4:after{content:"演示"; font-size:10.5px; font-weight:700; color:#fff; background:var(--teal); border-radius:4px; padding:2px 6px; margin-left:9px; vertical-align:2px; letter-spacing:.04em}

/* 数字带 */
.statband{display:grid; grid-template-columns:repeat(4,1fr); gap:0; border:1px solid var(--line); border-radius:10px; overflow:hidden; background:var(--card)}
.statband .s{padding:20px 20px; border-right:1px solid var(--line)}
.statband .s:last-child{border-right:none}
.statband .v{font-family:var(--serif); font-size:40px; font-weight:700; color:var(--teal-2); line-height:1.1}
.statband .v small{font-family:var(--sans); font-size:15px; color:var(--ink-3); font-weight:600; margin-left:4px}
.statband .k{font-size:13px; color:var(--ink-4); margin-top:6px; letter-spacing:.02em}

/* 链路图 */
.chain{display:flex; align-items:stretch; gap:0; border:1px solid var(--line); border-radius:10px; overflow:hidden; background:var(--card); margin:6px 0 20px}
.chain .n{flex:1; padding:14px 10px; text-align:center; font-size:14px; color:var(--ink-2); border-right:1px solid var(--line)}
.chain .n:last-child{border-right:none}
.chain .n b{display:block; font-size:11px; color:var(--teal); letter-spacing:.1em; margin-bottom:3px; font-family:var(--mono)}
.chain .n.hot{background:var(--teal-soft)}

/* 双列布局 */
.split{display:grid; grid-template-columns:1fr 1fr; gap:22px; align-items:start}
.panel{background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px 20px}
.panel h4{margin:0 0 10px; font-size:16px; display:flex; align-items:center; gap:8px; color:var(--ink)}
.panel h4 .badge{font-size:10.5px; letter-spacing:.1em; color:#fff; background:var(--ink-2); border-radius:3px; padding:2px 6px}
.panel.good{border-color:#c7e4dd; background:var(--teal-soft)}
.panel.good h4 .badge{background:var(--teal)}
.panel.bad{border-color:#eed3d0; background:var(--red-soft)}
.panel.bad h4 .badge{background:var(--red)}
.panel p{margin:0; font-size:14.5px; line-height:1.65; color:var(--ink-3)}
.panel ul{margin:0; padding-left:18px; font-size:14.5px; line-height:1.7; color:var(--ink-3)}
.panel ul b{color:var(--ink-2)}

/* 结束页 */
.end{position:absolute; inset:0; padding:90px; display:flex; flex-direction:column; justify-content:center; align-items:flex-start}
.end h1{font-family:var(--serif); font-size:58px; color:#fff; margin:0 0 18px; line-height:1.2}
.end .line{font-size:22px; color:#9db0c2; letter-spacing:.06em; margin:0 0 36px}
.end .grid3{display:grid; grid-template-columns:repeat(3,1fr); gap:14px; width:100%; max-width:1080px}
.end .q{border:1px solid rgba(255,255,255,.16); background:rgba(255,255,255,.04); border-radius:8px; padding:16px 18px}
.end .q b{display:block; color:#7fd0bd; font-size:12px; letter-spacing:.12em; margin-bottom:5px}
.end .q p{margin:0; color:#c3d2df; font-size:15px; line-height:1.55}
.end .thanks{margin-top:40px; font-size:26px; color:#fff; font-family:var(--serif); letter-spacing:.08em}

/* 提示条（首次进入） */
.hint-bar{position:fixed; left:50%; bottom:18px; transform:translateX(-50%); z-index:20; background:rgba(10,16,24,.72); color:#c9d6e2; border:1px solid rgba(255,255,255,.14); backdrop-filter:blur(8px); border-radius:999px; padding:7px 16px; font-size:12px; letter-spacing:.04em; display:flex; gap:14px; align-items:center; transition:opacity .4s}
.hint-bar b{color:#7fd0bd; font-weight:700}
.hint-bar.hide{opacity:0; pointer-events:none}
.hint-bar kbd{font-family:var(--mono); font-size:11px; border:1px solid rgba(255,255,255,.25); border-bottom-width:2px; border-radius:4px; padding:1px 5px; color:#e3ecf4}

/* 打印：一页一张 */
@media print{
  @page{size:1280px 720px; margin:0}
  html,body{background:#fff; overflow:visible; height:auto}
  #stage{position:relative; left:auto; top:auto; transform:none!important; width:1280px; height:auto; margin:0; box-shadow:none; overflow:visible}
  .deck{position:static; inset:auto}
  .slide{display:block!important; position:relative!important; inset:auto!important; width:1280px; height:720px; break-after:page; page-break-after:always; overflow:hidden}
  .slide:last-child{break-after:auto; page-break-after:auto}
  .hint-bar{display:none!important}
}
</style>
</head>
<body>
<div id="stage">
  <div class="deck" id="deck">
