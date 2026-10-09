# A 的三页 HTML 讲解

直接用浏览器打开 `index.html`。三页正文为英文，提供逐步骤的中文讲解提示和英文口播句。所有字体、样式、脚本及验证数据均可离线使用；页面之间通过相对链接切换。

## 三页内容

| 页面 | 讲解内容 | 建议时间 |
|---|---|---|
| `index.html` | 公钥 → 欧几里得算法 → 共享素因子 → 余因子 → 私钥恢复连接点 | 约 1 分钟 |
| `batch-gcd.html` | 乘积树向上合并、奇数叶子携带、平方模数余数树向下传播、整除与最终 GCD | 约 1 分 30 秒 |
| `edge-cases.html` | 重复模数映射、三角共享结构、全重叠回退、未解决状态及验证范围 | 约 1 分钟 |

## 演讲操作

- 点击 `Next step` 或按右方向键逐步前进；左方向键返回。
- 空格前进，`P` 自动播放／暂停，`Home` 重启当前页。
- `1 / 2 / 3` 切换页面；`PageDown / PageUp` 翻页。
- `N` 展开／收起中文讲解提示；默认收起，适合投影。
- `F` 或 `Full screen` 进入全屏，`Esc` 退出。
- 第三页可关闭 `Enable pairwise fallback`，比较预算为 0 时的未解决结果。
- 自动播放在当前页最后一步停止，切换到后台也会暂停。
- 页面尊重系统减少动画设置；仍可逐步查看全部信息。

提示：正式演讲优先手动逐步播放，每一步停下来解释当前数据变化。自动播放适合排练。浏览器全屏也可使用 F11。

## 与真实实现的关系

动画中的小整数使用 JavaScript BigInt 实时计算，演示与 Python 检测器相同的数学流程。它们是教学算术，并非浏览器现场执行 2048-bit Python 扫描。

验证区数据来自 `tests/fixtures/rsa2048_public.jsonl` 和成功的 Python 测试记录：16 条记录、14 个不同 2048-bit 模数、6 个成功分解的不同模数、4 个全重叠候选项被拆分。OAEP 解密验证已在 Python 集成测试完成。

第一页面的 `e=17` 只服务于小整数演示；真实测试样本采用 `e=65537`。A 实现提供因子与检测状态，密钥恢复连接点用于说明交接给 B 的输入。

## 检查和更新

在仓库根目录执行：

```powershell
node --check presentation/assets/slides.js
node tests/presentation_math.test.cjs
.\.venv\Scripts\python.exe presentation/export_validation.py
```

导出工具检查固定样本哈希和恢复集合，并读取 `results/unittest.txt` 中已有的成功测试记录。修改核心实现或样本后，应先重新运行 Python 测试并保存该日志，再更新验证区。

如需本地服务预览：

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory presentation
```

然后打开 `http://127.0.0.1:8765/`。正式展示不依赖本地服务，直接打开文件即可。

数学解释与英文完整讲稿见 `docs/A_PRESENTATION.md`。参考算法：Heninger et al., *Mining Your Ps and Qs*, USENIX Security 2012, §3.3。
