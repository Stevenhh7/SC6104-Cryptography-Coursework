# SC6104 最终演示

演示所需的网页、动画、讲稿、图表、公开样本、实验记录、运行代码和检查脚本集中在本目录。

## 本机启动

双击 **`run_presentation.cmd`**，保持服务运行，打开：

**http://127.0.0.1:8765/presentation/final.html**

启动器优先使用本目录的 `.venv`，否则复用上一级课程项目的 `.venv`。本机依赖已安装。端口被占用时，在本目录执行 `run_presentation.cmd --port 8766`，并使用对应网址。

第 6 页点击 **Run Python pipeline → Run pipeline**，实际执行批量扫描、私钥恢复与 OAEP 解密，核对归档结果，再重扫已保存的换钥集合。**Save run log** 保存当次真实输出。

直接打开根目录的 **`final.html`** 或 **`presentation/final.html`**，可离线展示八页和动画；实际 Python 执行需要上面的本地服务。

## 文件位置

| 路径 | 内容 |
|---|---|
| `final.html` | 双击进入正式展示的快捷入口 |
| `presentation/final.html` | 八页正式展示网页 |
| `presentation/assets/`、`presentation/embed/` | 样式、动画、脚本及展示数据 |
| `docs/FINAL_SPEECH.md` | 八分钟讲稿、两人分工、现场操作及问答 |
| `docs/A_PRESENTATION.md`、`docs/B_CODE_GUIDE.md` | 各自实现的理解材料 |
| `artifacts/figures/` | 性能图、阶段耗时、弱素数池与共享因子图 |
| `artifacts/demo/` | 2048-bit 公钥、OAEP 密文、恢复证据和换钥集合 |
| `artifacts/benchmark/`、`artifacts/pool/`、`artifacts/controls/` | 原始实验记录、环境、配置和核验结果 |
| `rsa_audit/`、`rsa_lab/` | 现场执行所用的项目 Python 模块 |
| `scripts/presentation_server.py` | 本地网页服务及固定现场执行接口 |
| `scripts/verify_showcase.py` | 归档完整性和 OAEP 重放检查 |
| `tests/` | 数学、交互、流式输出及服务检查 |
| `requirements.txt`、`requirements.lock.txt` | 依赖范围与原环境版本记录 |

运行代码是整理时项目实现的副本。修改检测或恢复实现后，需要同步本目录对应模块，并重新核验；网页与归档数据也应保持一致。

## 复制到另一台电脑

可以直接复制整个 `final_presentation` 文件夹。安装 Python 3.10+ 后，在本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_presentation.cmd
```

已安装依赖后，展示及现场重放不需要网络。完整操作说明在 `presentation/README.md`，正式讲稿单独放在 `docs/FINAL_SPEECH.md`。
