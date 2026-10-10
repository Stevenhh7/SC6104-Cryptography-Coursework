# 正式展示与动画

`final.html` 是八页正式展示版。正文、数学说明及按钮为英文，不包含主讲人、计时、演讲提示或讲稿入口。逐页讲稿、两人分工、八分钟节奏和问答在 `../docs/FINAL_SPEECH.md`。

## 现场运行 Python

在仓库根目录双击 `run_presentation.cmd`，打开：

http://127.0.0.1:8765/presentation/final.html

或者使用 `.venv\Scripts\python.exe -X utf8 scripts/presentation_server.py`。已有静态服务占用端口时，可加 `--port 8766`，并使用对应网址。程序只监听本机回环地址。

第 6 页点击 **Run Python pipeline**，再点 **Run pipeline**。窗口展示真实命令、stdout、输入摘要、逐阶段结果和耗时；**Save run log** 可下载运行记录。执行流程：

1. 校验归档的公开输入及实际 2048-bit 位长。
2. 在新进程中调用原有 `rsa_lab scan`（通过适配层调用 A 的 `rsa_audit`）。
3. 在新进程中调用原有 `rsa_lab recover`，恢复私钥并解密 OAEP。
4. 攻击后才对比归档的已验证状态及明文，验证因子乘积。
5. 重新扫描已保存的替换密钥集合。

这是**现场重算并对照归档**，不是重播日志，也不重新生成密钥、不重跑完整独立真值评估或性能实验。结果写入临时目录，不修改归档，不保存私钥文件。失败会显示错误，不伪装成成功。执行请求不接受任意命令或文件路径，同一时刻只允许一次运行。

本机依赖已经安装；其他机器使用 Python 3.10+ 并安装 `requirements.txt`。完整实验仍可使用 `run_demo.cmd`。普通 `python -m http.server` 不能提供执行接口。

## 离线与动画

直接打开 `final.html` 可以离线展示全部八页、数学动画和归档实验结果。只有实际 Python 执行需要本地演示服务。

- 总页码按钮、Previous / Next 切换八页。
- 动画内 Next step / Previous 控制数学步骤；方向键、空格同样有效。
- 动画获得焦点后，PageDown / PageUp 切换总展示并同步页码；1 / 2 / 3 选择三页数学动画。
- P 自动播放或暂停，Home 重置当前数学动画；自动播放到最后一步停止，离开动画页暂停。
- Full screen 为整组页面全屏。系统减少动画设置仍受支持。
- 第 4 页开关用于比较 full-overlap 的回退与 unresolved，右侧正式核验证据不随教学开关变化。

步骤切换复用图形元素，数字交叉渐变、数据点沿树路径移动；快速切换会取消旧过渡。第 6 页可按阶段直接查看记录结果，并有独立的现场执行窗口。补充窗口包含私钥公式、对照实验、分阶段耗时、弱素数池和共享因子图。

## 数据口径

正式展示统一为 102 条记录、100 个不同的实际 2048-bit 模数、5 个恢复密钥和 6 条核对明文。两条记录重复，其中一条对应脆弱密钥。三个全重叠候选使用九次回退 GCD。换钥后检测到零个共享因子，原完整实验的六条新消息通过合法 OAEP round trip。

性能图使用同输入、同 GMP 后端、每条件三次运行：1000 个模数约 32.8 倍；3000 个模数的 pairwise 三次超过 45 秒，不能计算完整实测速比。现场单次耗时独立显示，不替换历史图表。

独立 A 练习页 `index.html`、`batch-gcd.html`、`edge-cases.html` 保留旧小型 fixture 证据及可选讲解提示。正式 `final.html` 嵌入时隐藏提示，并使用整组最终实验数据。

## 维护与检查

```powershell
node --check presentation/assets/final.js
node --check presentation/assets/live.js
node tests/presentation_math.test.cjs
node tests/presentation_interactions.test.cjs
node tests/presentation_live.test.cjs
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_presentation_server.py -v
```

网页归档数据由 `scripts/export_showcase.py` 生成。新增正式讲稿是 `docs/FINAL_SPEECH.md`；旧 `docs/PRESENTATION.md` 是历史自动生成稿，不是本版配套讲稿。
