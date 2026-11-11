<!-- ================= 03 AI 辅助 ================= -->
<section id="s11">
  <div class="chapter">
    <div class="num">PART 03 / AI 辅助</div>
    <h2>AI 辅助</h2>
    <p class="lede">这一段以演示为主。三个场景，按"建模 → 排障 → 操作"的顺序推进，每个场景都先给结论、再给操作、最后用一页 PPT 收口。<b>重点不是 AI 会聊天，而是 AI 能进真实链路、并且每一步都受控。</b></p>
    <div class="chips">
      <span class="chip"><b>8 分钟</b></span>
      <span class="chip">形式：现场演示（3 段）</span>
      <span class="chip">兜底：录屏 + 离线样例</span>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">11</span><span class="ttl">AI 能力总览</span><span class="tag green">演示前导</span></div>
    <div class="body">
      <h3 class="pt">三个场景，一条原则：AI 只提建议，平台负责校验与执行</h3>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">A</span>生成与校验物模型</h4><p>自然语言描述设备 → 生成 TSL 草案 → 平台三道校验 → 保存即生效。缩短新产品上线周期。</p></div>
        <div class="cardlet"><h4><span class="ic">B</span>定位数据链路问题</h4><p>按"凭证 → 产品配置 → 规则链 → 主题 → 时序库"逐段排查，直接指出断点位置与原因。</p></div>
        <div class="cardlet"><h4><span class="ic">C</span>调用平台 OpenAPI</h4><p>AI 助手直接搜索并调用平台接口，可扩展为运维问答入口；写操作必须人工确认。</p></div>
      </div>
      <div class="cols c2">
        <div class="cardlet blue"><h4><span class="ic">✓</span>受控边界（一定要讲）</h4><p>只读操作直接执行；<b>写操作生成待确认动作</b>，带参数与风险等级；高危操作二次确认并留审计。AI 不直接握数据库，也不绕过 JWT 权限。</p></div>
        <div class="cardlet amber"><h4><span class="ic">!</span>表述边界</h4><p>生成的是<b>草案</b>，必须过平台校验才落库；"AI 直接改生产数据"这种说法今天不讲，也不成立。</p></div>
      </div>
      <p class="hint">建议版式：三个能力卡横排，下方一条"人 → AI → 平台校验 → 执行"的受控链条；边界卡用对比色，这一页的作用是提前建立信任。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分钟</small></div>
      <div class="say">
        <p>接下来这一段我们直接开系统。先用一分钟交代边界，因为 AI 这个话题最容易讲飘。</p>
        <p>我们做了三个场景：<strong>生成和校验物模型、定位数据链路问题、调用平台 OpenAPI</strong>。贯穿三个场景的原则只有一条——<strong>AI 只提建议，平台负责校验和执行</strong>。</p>
        <p>具体说：查询类操作，AI 直接调；写入类操作，一定先生成"待确认动作"，把参数和风险等级摆出来，人点了确认才执行；高危操作还要二次确认并记审计。所以它不是"一个能改库的机器人"，而是<strong>一个受权限约束的操作入口</strong>。</p>
      </div>
    </div>
  </div>

  <!-- 演示 A -->
  <div class="slide" id="s12">
    <div class="bar"><span class="pg">12</span><span class="ttl">演示 A：自然语言生成并校验物模型</span><span class="tag green">现场演示 ①</span></div>
    <div class="body">
      <h3 class="pt">从"一段设备描述"到"一个可用的产品"</h3>
      <p class="subpt">目标：把新产品建模从"写 JSON、反复调格式"变成"描述需求、看校验结果"。</p>
      <div class="cols c2">
        <div class="cardlet"><h4><span class="ic">前</span>现在的做法</h4><p>对照规范手写 TSL，字段类型、枚举映射、事件参数容易错；错一次，规则链校验失败一次，来回沟通。</p></div>
        <div class="cardlet"><h4><span class="ic">后</span>演示的做法</h4><p>口述设备能力 → AI 产出 TSL 草案 → 平台三道校验给出逐条问题 → 修正后保存即生效。</p></div>
      </div>
      <ul class="pts tight">
        <li><b>结构校验</b>：JSON Schema 层面，字段名、类型、必填项、层级结构。</li>
        <li><b>业务校验</b>：枚举取值、数值范围、int32 边界、事件类型、版本号规则。</li>
        <li><b>运行时就绪</b>：校验通过后生成压缩 schema 并内嵌规则链，遥测上报即刻按新物模型校验。</li>
      </ul>
    </div>
    <div class="demo">
      <div class="hd"><span class="badge">DEMO A</span><span class="t">生成 → 校验 → 生效</span><span class="dur">约 2 分 30 秒</span></div>
      <div class="bd">
        <p class="goal">演示目标：让客户看到 <b>AI 产出的是草案，平台的校验才是闸门</b>——这比"AI 一次生成就对"更可信。</p>
        <ol class="steps">
          <li>打开 AI 助手面板，口述需求：<b>"挖掘机产品，属性包含油量、液压压力、发动机温度，事件包含油量低告警"</b>。</li>
          <li>展示 AI 返回的 TSL 草案：属性、事件、单位、范围、枚举一次成型。</li>
          <li>故意保留一处类型问题（如温度写成字符串），提交校验，展示<b>逐条问题列表</b>而不是一句"校验失败"。</li>
          <li>修正后再次校验通过，保存产品，展示<b>状态变为已发布</b>。</li>
          <li>打开产品详情：产品配置、产品资产、产品规则链<b>已自动生成</b>。</li>
        </ol>
        <div class="expect"><div class="k">预期结果</div><div class="v">产品 ID 全系统唯一 → 校验全绿 → 保存即发布 → 平台侧三件套自动就绪；<b>全程不需要手写 JSON</b>。</div></div>
        <div class="expect"><div class="k">讲解要点</div><div class="v">在"问题列表"那一步停顿：<b>AI 会犯错，但错误在落库之前就被拦住</b>。这是可控性的证据，不要跳过。</div></div>
      </div>
      <div class="fallback"><span class="k">兜底</span>若模型生成质量不稳定：改为"上传已准备好的 TSL → 演示修改与校验 → 保存生效"，结论不变；演示前准备一份<b>故意含错</b>的 TSL 备用。</div>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 2 分 30 秒</small></div>
      <div class="say">
        <p>第一个场景，建模。传统做法是拿规范手写 JSON，字段类型、枚举映射、事件参数，错一个就校验不过，来回好几轮。</p>
        <p>现在我把设备能力描述给 AI：<strong>有哪些属性、单位是什么、什么条件触发什么事件</strong>。它给出 TSL 草案。</p>
        <p><span class="beat">操作中</span> 注意，我这里故意留了一个类型错误——温度写成了字符串。提交校验，平台给的不是一句"失败"，而是<strong>逐条指出第几个字段、错在哪、期望是什么</strong>。</p>
        <p><span class="beat">操作中</span> 修正，再校验，通过。保存之后产品直接是已发布状态，产品配置、资产、规则链自动生成。</p>
        <p>我想强调的是最后这一点：<strong>AI 会犯错，但错误在落库之前就被平台的校验拦住了</strong>。所以它提速，但不降低门槛。</p>
      </div>
    </div>
  </div>

  <!-- 演示 B -->
  <div class="slide" id="s13">
    <div class="bar"><span class="pg">13</span><span class="ttl">演示 B：辅助定位数据链路问题</span><span class="tag green">现场演示 ②</span></div>
    <div class="body">
      <h3 class="pt">一条数据没上来，到底断在哪一段</h3>
      <p class="subpt">现场排障最耗时的不是修，是"判断问题在哪一层"。AI 的价值是把判断过程压缩到分钟级。</p>
      <pre><span class="c"># 平台侧可观测的五段链路</span>
① 设备凭证 ──▶ ② 产品配置 ──▶ ③ 规则链校验 ──▶ ④ Kafka 主题 ──▶ ⑤ 时序库落库
   令牌/连接      绑定/属性       类型/范围/枚举      normalized / invalid      TDengine 子表</pre>
      <table class="tbl">
        <thead><tr><th style="width:130px">典型症状</th><th>常见断点</th><th>AI 给出的定位结论</th></tr></thead>
        <tbody>
          <tr><td>设备显示离线</td><td>① 凭证或网络</td><td>令牌失效 / ClientId 冲突 / 未开网关模式</td></tr>
          <tr><td>在线但无数据</td><td>② 产品绑定</td><td>设备未绑定产品配置，或属性键不在 TSL 中</td></tr>
          <tr><td>有数据但被丢弃</td><td>③ 规则链</td><td>类型不符、越界、未知字段、报文超限，附原始报文</td></tr>
          <tr><td>主题有消息但库无数据</td><td>④ ⑤ 入湖</td><td>消费组滞后 / 子表未建 / 写入报错</td></tr>
        </tbody>
      </table>
    </div>
    <div class="demo">
      <div class="hd"><span class="badge">DEMO B</span><span class="t">造一个错，再让 AI 找出来</span><span class="dur">约 2 分 30 秒</span></div>
      <div class="bd">
        <p class="goal">演示目标：不是"AI 能查日志"，而是 <b>它能沿着真实链路逐段排除，并给出可执行的修复建议</b>。</p>
        <ol class="steps">
          <li>先用模拟器发一条<b>类型错误</b>的遥测（温度传成字符串），让它进入非法数据通道。</li>
          <li>向 AI 描述现象：<b>"设备 demo_device_01 在线但数据查不到"</b>。</li>
          <li>AI 依次核对：设备凭证与在线状态 → 产品绑定与 TSL 版本 → 规则链校验结果 → 非法主题消息。</li>
          <li>在<b>非法数据主题</b>里定位到原始报文，指出具体字段与期望类型。</li>
          <li>修正后重发，平台页面看到数据点写入，查询正常返回。</li>
        </ol>
        <div class="expect"><div class="k">预期结果</div><div class="v">AI 输出"断点在第 ③ 段规则链校验，字段 temperature 期望 double，实际为字符串"，并给出修复建议；<b>不需要人工逐个主题翻消息</b>。</div></div>
        <div class="expect"><div class="k">讲解要点</div><div class="v">强调<b>非法数据是隔离而不是丢弃</b>：进 <code>iot.invalid</code> 主题，可回放、可追溯，这本身就是排障基础设施。</div></div>
      </div>
      <div class="fallback"><span class="k">兜底</span>若现场模拟器不稳定：直接展示已捕获的非法报文明细与 AI 分析结果截图；或改为只读查询演示（"查询本租户设备"），保证动作一定成功。</div>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 2 分 30 秒</small></div>
      <div class="say">
        <p>第二个场景是排障。现场最耗时的从来不是修，是<strong>判断问题在哪一层</strong>：是设备没连上？产品没绑？规则链拒了？还是消息到了但没入库？</p>
        <p><span class="beat">操作中</span> 我先造一个错——把温度值故意传成字符串。然后用一句话问 AI："设备在线，但数据查不到。"</p>
        <p>它会按顺序核对：凭证和在线状态、产品绑定和物模型版本、规则链校验结果、最后看非法主题。<strong>结论是断在规则链，字段类型不符</strong>，还给了原始报文。</p>
        <p>为什么能这么快？因为非法数据我们没有丢，而是<strong>隔离到独立主题</strong>，可回放、可追溯。所以"定位"这件事，前提是链路本身留了证据。</p>
        <p><span class="beat">操作中</span> 修正后重发，数据正常写入。整个过程大概两分钟，传统方式可能要来回两趟现场。</p>
      </div>
    </div>
  </div>

  <!-- 演示 C -->
  <div class="slide" id="s14">
    <div class="bar"><span class="pg">14</span><span class="ttl">演示 C：AI 调用平台 OpenAPI</span><span class="tag green">现场演示 ③</span></div>
    <div class="body">
      <h3 class="pt">对话即操作，但每一次写入都要人点头</h3>
      <p class="subpt">AI 助手接的不是"几个写死的工具"，而是平台的接口目录——接口加进来，助手就能用。</p>
      <div class="cols c2">
        <div class="cardlet"><h4><span class="ic">✓</span>读操作</h4><p>直接执行并返回结构化结果：查租户、查产品、查设备、查告警、查网关列表。不产生任何待确认动作。</p></div>
        <div class="cardlet"><h4><span class="ic">●</span>写操作</h4><p>生成待确认动作：动作名、参数、风险等级一并展示；确认后才调用平台 REST；高危操作二次确认并记审计。</p></div>
      </div>
      <ul class="pts tight">
        <li><b>接口目录可扩展</b>：新增接口只需补充目录配置，不需要改助手插件——这是"可扩展为运维问答入口"的基础。</li>
        <li><b>权限不绕过</b>：沿用平台 JWT 与租户隔离，租户管理员看不到别的租户数据。</li>
        <li><b>复杂动作有专用 handler</b>：创建产品要带 TSL、创建设备要写服务端属性，这类不交给模型自由发挥。</li>
      </ul>
    </div>
    <div class="demo">
      <div class="hd"><span class="badge">DEMO C</span><span class="t">查 → 建 → 确认</span><span class="dur">约 2 分钟</span></div>
      <div class="bd">
        <p class="goal">演示目标：让客户看到 <b>"对话式操作"与"企业级管控"可以同时成立</b>。</p>
        <ol class="steps">
          <li>输入 <b>"查询本租户产品"</b>：AI 先搜索接口目录，再执行只读调用，直接返回列表。</li>
          <li>输入 <b>"为产品创建设备 demo_device_02"</b>：生成待确认动作，展示参数与风险等级。</li>
          <li>点<b>确认执行</b>，设备创建成功；打开设备详情，服务端属性已写入产品 ID、物模型版本、工点编码。</li>
          <li>输入一个<b>高危删除</b>动作，展示"高危"标识与影响范围，然后<b>取消</b>，确认不产生任何数据。</li>
        </ol>
        <div class="expect"><div class="k">预期结果</div><div class="v">只读直连、写入必确认、高危必拦截；接口目录新增后<b>无需改助手</b>即可调用。</div></div>
        <div class="expect"><div class="k">讲解要点</div><div class="v">"取消"这一步要演示，而且要停两秒——<b>证明系统真的没有执行</b>，这是客户最在意的部分。</div></div>
      </div>
      <div class="fallback"><span class="k">兜底</span>演示环境写操作受限时：只演示"查询 + 待确认动作生成 + 取消"，不点确认；<b>写入成功后的截图</b>放在备份资产里。</div>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 2 分钟</small></div>
      <div class="say">
        <p>第三个场景，操作。这里最容易走两个极端：要么只是"能聊天"，要么"让 AI 直接改数据"。我们两个都不做。</p>
        <p><span class="beat">操作中</span> 先查："查询本租户产品"——AI 先搜接口目录，找到对应操作，再执行只读调用，直接给结果。</p>
        <p><span class="beat">操作中</span> 再建："为产品创建设备"。注意它没有直接执行，而是<strong>弹出一个待确认动作</strong>，参数、风险等级都摆在这儿。我点确认，设备才创建。</p>
        <p><span class="beat">操作中</span> 最后我试一个高危删除。系统标了"高危"，我把影响范围念一下，然后<strong>点取消</strong>——各位可以看到，什么都没发生。</p>
        <p>这个设计的意义在于：<strong>AI 把操作门槛降到"会说话"，但把执行权限留在"人点头"</strong>。它适合做运维问答入口，而不是一个无人值守的执行器。</p>
      </div>
    </div>
  </div>
</section>

<!-- ================= 04 融合终端 ================= -->
<section id="s15">
  <div class="chapter">
    <div class="num">PART 04 / 融合终端无缝接入</div>
    <h2>融合终端无缝接入</h2>
    <p class="lede">这一段回答现场最现实的问题：<b>车间里一堆协议，到底要不要再加一层中转服务？</b>答案是一台融合网关聚合多协议、单跳直连平台、共用一个标准物模型。</p>
    <div class="chips">
      <span class="chip"><b>8 分钟</b></span>
      <span class="chip">形式：PPT 2 页 + 实物/录屏演示</span>
      <span class="chip">关键词：OPC-UA · S7 · CAN · 直连</span>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">15</span><span class="ttl">一台边缘网关聚合多类子设备</span><span class="tag">接入形态</span></div>
    <div class="body">
      <h3 class="pt">OPC-UA、S7、CAN 在网关内收敛，对外只有一条 MQTT</h3>
      <p class="subpt">协议差异在边缘侧消化，平台侧只看到"设备 + 物模型"。</p>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">P1</span>OPC-UA</h4><p>面向 PLC、DCS 与产线控制系统，按节点读取，适合结构化工艺参数。</p></div>
        <div class="cardlet"><h4><span class="ic">P2</span>S7</h4><p>面向西门子系列设备，直接读 DB 块，适合存量产线的低成本改造。</p></div>
        <div class="cardlet"><h4><span class="ic">P3</span>CAN</h4><p>面向车载、工程机械与控制器局域网，适合高频、短帧的运行数据。</p></div>
      </div>
      <pre><span class="c"># 现场拓扑</span>
  PLC / DCS ──OPC-UA──┐
  西门子设备 ──S7─────┼──▶ <span class="k">融合网关</span> ──MQTT(单连接)──▶ 物联网平台
  工程机械 ──CAN──────┘        │
                               └─ 本地缓存 / 断网续传 / 协议解析

<span class="c"># 平台侧看到的</span>
  网关设备（gateway=true）
   └─ Contains ─▶ 子设备 A（OPC-UA 点位映射）
   └─ Contains ─▶ 子设备 B（S7 DB 映射）
   └─ Contains ─▶ 子设备 C（CAN 帧映射）</pre>
      <p class="hint">建议版式：左侧现场设备三类图标 → 中间网关 → 右侧平台；网关处标注「协议解析 / 缓存 / 单连接」，把复杂度集中在网关框内，视觉上强调"平台侧很干净"。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 40 秒</small></div>
      <div class="say">
        <p>第四部分，融合终端。现场的情况大家比我熟：一条产线上可能同时有 OPC-UA 的 PLC、西门子的 S7 设备、还有 CAN 总线的工程机械。<strong>协议不统一，是常态。</strong></p>
        <p>我们的做法是把协议收敛在<strong>一台边缘网关</strong>里：OPC-UA 按节点读、S7 直接读 DB 块、CAN 解析帧，全部在网关内部完成映射。对外，它只有一条 MQTT 连接。</p>
        <p>这样平台侧看到的东西就很干净——一个网关设备，下面挂若干子设备，关系是标准的 Contains。<strong>平台不需要知道现场用的是哪种总线</strong>，这是解耦的关键。</p>
        <p>顺带说一句：网关还承担本地缓存和断网续传。网络抖一下，数据不丢，恢复后按原始时间戳补传。</p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">16</span><span class="ttl">无需中转服务：网关直连平台</span><span class="tag blue">架构对比</span></div>
    <div class="body">
      <h3 class="pt">去掉中间那一段，少一个故障点、少一套运维</h3>
      <div class="cols c2">
        <div class="cardlet red"><h4><span class="ic">×</span>传统"网关 + 中转"</h4><p>网关 → 中转服务（协议转换 / 转发）→ 平台。中转服务要单独部署、单独监控、单独扩容，出问题先查它。</p></div>
        <div class="cardlet"><h4><span class="ic">✓</span>本方案：单跳直连</h4><p>网关 MQTT 客户端直连平台网关模式，平台原生支持网关主题与子设备关系。<b>没有中转服务这一层。</b></p></div>
      </div>
      <table class="tbl">
        <thead><tr><th style="width:170px">对比项</th><th>网关 + 中转服务</th><th>融合网关直连</th></tr></thead>
        <tbody>
          <tr><td>部署单元</td><td>网关 + 中转 + 队列</td><td class="mark">仅网关</td></tr>
          <tr><td>故障点</td><td>多一层，排障需跨系统</td><td class="mark">单跳，链路上少一段</td></tr>
          <tr><td>子设备建模</td><td>中转侧维护一套映射</td><td class="mark">平台侧标准物模型</td></tr>
          <tr><td>扩容方式</td><td>中转层也要跟着扩</td><td class="mark">网关侧增加终端即可</td></tr>
        </tbody>
      </table>
      <p class="hint">建议版式：上面两条链路对比图（红线画掉中转层），下面四行对比表；"没有中转服务"这五个字要作为页面主标题的一部分。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 30 秒</small></div>
      <div class="say">
        <p>这一页回答一个很具体的担心：<strong>是不是还要再加一台中转服务器？</strong>答案是不用。</p>
        <p>传统方案里，网关连中转、中转再连平台，中间那一层要做协议转换、要做转发、还要单独监控和扩容。多一层，就多一个故障点，也多一套要维护的东西。</p>
        <p>我们的融合网关，MQTT 客户端<strong>直接连平台的网关模式</strong>。平台原生支持网关主题、支持网关和子设备的包含关系。所以链路上<strong>没有中转服务这一段</strong>。</p>
        <p>这对现场意味着什么？少一台机器、少一个要盯的服务、排障的时候少跨一个系统。</p>
        <p><span class="beat">预判追问</span> 如果问"网关坏了怎么办"：子设备数据在网关本地有缓存，换一台网关、恢复配置和凭证即可续传；这也是把复杂度放在边缘的代价，我们认这个代价。</p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">17</span><span class="ttl">融合网关使用同一个标准物模型</span><span class="tag">建模一致</span></div>
    <div class="body">
      <h3 class="pt">网关与子设备共享一套物模型语言</h3>
      <p class="subpt">不是"网关一套格式、平台一套格式"，而是同一份 TSL、同一套校验规则、同一条规则链。</p>
      <ul class="pts">
        <li><b>同一份 TSL</b>：子设备的属性、事件、行为定义沿用产品物模型，网关只做点位到字段的映射。
          <span>同一个型号的设备，换一个网关接入，物模型不用重建。</span></li>
        <li><b>同一套校验</b>：网关上报的遥测同样过产品规则链，类型、范围、枚举、必填一项不少。
          <span>不会因为"走了网关"就降低数据质量门槛。</span></li>
        <li><b>同一条链路</b>：子设备数据与直连设备走同一个 Kafka 主题、同一套入湖逻辑。
          <span>下游不用区分"这是网关来的还是直连来的"。</span></li>
      </ul>
      <div class="cols c2">
        <div class="cardlet"><h4><span class="ic">↔</span>横向：多网关复用</h4><p>同一产品在多个工点、多台网关上复用同一份物模型，新增工点只加网关实例。</p></div>
        <div class="cardlet"><h4><span class="ic">↕</span>纵向：平台无感</h4><p>平台侧不区分接入方式，规则、告警、看板、API 全部按统一模型工作。</p></div>
      </div>
      <p class="hint">建议版式：中间一份 TSL 文档图标，向上连网关、向下连平台规则链，左右各一个"复用 / 无感"说明；强调"一份模型"而不是"两套适配"。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 20 秒</small></div>
      <div class="say">
        <p>第三页讲建模。很多网关方案的问题是：网关一套数据格式，平台一套模型，中间要写适配，适配一多就没人维护得动。</p>
        <p>我们的做法是<strong>同一份 TSL</strong>。子设备的属性、事件、行为，沿用产品的物模型定义；网关只负责把 OPC-UA 的节点、S7 的 DB 块、CAN 的帧，映射到模型字段上。</p>
        <p>而且网关来的数据<strong>同样过产品规则链</strong>，类型、范围、枚举、必填，一项不少。不会因为走了网关就放松校验——这条很重要，否则数据质量会分层。</p>
        <p>对下游来说更简单：子设备数据和直连设备走同一个主题、同一套入湖，<strong>平台不需要知道它是怎么接进来的</strong>。</p>
      </div>
    </div>
  </div>

  <!-- 演示 D -->
  <div class="slide" id="s18">
    <div class="bar"><span class="pg">18</span><span class="ttl">演示 D：三步完成融合终端接入</span><span class="tag green">现场演示 ④</span></div>
    <div class="body">
      <h3 class="pt">上线 → 挂子设备 → 看数据与下行</h3>
      <p class="subpt">这一段建议用实物网关或现场录屏，比模拟器更有说服力；PPT 只保留步骤与判据。</p>
      <table class="tbl">
        <thead><tr><th style="width:52px">步骤</th><th>操作</th><th>成功判据</th></tr></thead>
        <tbody>
          <tr><td class="num">1</td><td>网关以网关模式连接平台（<code class="inl">gateway=true</code>）</td><td>网关列表显示在线，连接时间刷新</td></tr>
          <tr><td class="num">2</td><td>子设备注册并发起上线，建立 Contains 关系</td><td>网关详情「网关设备」页签出现子设备</td></tr>
          <tr><td class="num">3</td><td>三类协议数据上报，平台侧查看实时值</td><td>同一产品下三个子设备均有数据点</td></tr>
          <tr><td class="num">4</td><td>平台下发 RPC，网关转发至子设备</td><td>设备返回结果，状态遥测变化</td></tr>
        </tbody>
      </table>
    </div>
    <div class="demo">
      <div class="hd"><span class="badge">DEMO D</span><span class="t">一台网关，三类协议，一条连接</span><span class="dur">约 3 分钟</span></div>
      <div class="bd">
        <p class="goal">演示目标：证明 <b>平台确实"看到"了子设备，而不只是收到一包透传数据</b>。</p>
        <ol class="steps">
          <li>展示融合网关已上线：网关详情里能看到在线状态与最近连接时间。</li>
          <li>打开「网关设备」页签，展示 OPC-UA / S7 / CAN 三类子设备按连接器分组。</li>
          <li>回到设备详情看实时值：同一时刻三个子设备都有数据刷新。</li>
          <li>下发一条 RPC（如修改上报周期），展示网关转发、设备回执。</li>
        </ol>
        <div class="expect"><div class="k">预期结果</div><div class="v">子设备作为<b>标准设备对象</b>存在，有属性、有关系、有状态；数据与直连设备无差别地进入规则链与时序库。</div></div>
        <div class="expect"><div class="k">讲解要点</div><div class="v">重点不是"数据通了"，而是<b>"设备被平台认识了"</b>——能被检索、能被授权、能被规则引用，这才叫无缝接入。</div></div>
      </div>
      <div class="fallback"><span class="k">兜底</span>现场无实物网关时：播放提前录制的接入视频（2 分钟版）；或用网关模拟脚本在本地复现同一套主题与关系，<b>提前把子设备与关系建好</b>。</div>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 3 分钟</small></div>
      <div class="say">
        <p>第四部分最后一个演示，我们直接看一台融合网关。</p>
        <p><span class="beat">操作中</span> 这是网关详情，在线状态、最近连接时间都在。点开「网关设备」页签——OPC-UA 的、S7 的、CAN 的子设备都在这儿，还按连接器分了组。</p>
        <p><span class="beat">操作中</span> 再看实时值：同一时刻三路子设备都在刷新。最后我下发一条 RPC，改一下上报周期，网关转发下去，设备回执上来。</p>
        <p>这一段我想让各位注意的不是"数据通了"，而是<strong>子设备在平台里是一个标准设备对象</strong>：有属性、有关系、有在线状态，能被检索、能被授权、能被规则引用。</p>
        <p>这才叫"无缝接入"。如果只是把一包数据透传上来，平台是没法对它做治理的。</p>
      </div>
    </div>
  </div>
</section>
