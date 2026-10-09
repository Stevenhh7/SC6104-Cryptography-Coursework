# 小组整合版本

目录中的 `rsa_audit` 是 A 的检测引擎，`rsa_lab` 是 B 的完整实验与演示。`rsa_lab/detection.py` 只转换接口，调用 A 的引擎。

## 最终展示

双击 `presentation/final.html` 打开离线总展示。8 页正文、导航按钮、补充窗口和讲稿全部为英文。总展示包含 A 的三页动画、B 的实测性能图、真实 OAEP 演示记录和修复结论。下方按钮切换总页面，点击动画内的按钮控制数学步骤。第 5、6、8 页的补充窗口提供阶段耗时、私钥恢复、对照实验及弱素数池证据，适合问答时使用。

现场操作运行 `run_demo.cmd`，或在仓库根目录执行：

```powershell
..\.venv\Scripts\python.exe -X utf8 -m rsa_lab demo
```

这里使用上一层原 B 项目的已安装环境。若在别处克隆，需要新建环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m rsa_lab demo
```

完整安装也可以用 `pip install -e ".[lab]"`。原来的 `python -m rsa_audit` 命令仍然有效。

## 主要文件

- `docs/INTEGRATION.md`：接口变更与验证。
- `docs/B_CODE_GUIDE.md`：B 核心代码解释。
- `docs/PRESENTATION.md`：8 分钟讲稿。
- `docs/GITHUB_HANDOFF.md`：GitHub 上传清单和队友整合步骤。
- `docs/B_IMPROVEMENTS.md`：B 实现与课程要求的对应改进。
- `artifacts/RESULTS.md`：本整合版本的实测报告。
- `artifacts/benchmark/`：每次测量、汇总、环境和配置。
- `artifacts/figures/`：最终图表。

## 复查

```powershell
..\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
..\.venv\Scripts\python.exe -X utf8 -m rsa_lab validate
..\.venv\Scripts\python.exe -X utf8 -m rsa_lab benchmark --backend gmpy2
```

测试在 Windows 上建议设置 `PYTHONUTF8=1`，使测试启动的子进程统一用 UTF-8。性能实验需要先生成或保留本地 `data/bench`。完整复测步骤见 README。
