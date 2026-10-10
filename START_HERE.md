# 小组整合版本

目录中的 `rsa_audit` 是 A 的检测引擎，`rsa_lab` 是 B 的完整实验与演示。`rsa_lab/detection.py` 只转换接口，调用 A 的引擎。

## 最终展示

演示资料集中在 `final_presentation/`。双击 `final_presentation/final.html` 打开离线总展示；现场执行使用 `final_presentation/run_presentation.cmd`，打开服务输出的网址，并在第 6 页点击 **Run Python pipeline**。10 页正文、导航按钮和补充窗口为英文，讲稿独立放在 `final_presentation/docs/FINAL_SPEECH.md`。总展示包含 A 的三页动画、实测性能、OAEP 恢复与换钥结果，以及第 9、10 页的 A/B 核心代码。

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
- `final_presentation/docs/FINAL_SPEECH.md`：正式 8 分钟讲稿、分工和现场操作。
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
