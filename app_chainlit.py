import os
import sys
from pathlib import Path

# 将当前目录添加到 sys.path
root = Path(__file__).absolute().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# 导入 Chainlit 应用
# 注意：Chainlit 运行是通过命令行 'chainlit run app_chainlit.py' 触发的
# 我们将逻辑直接指向 marathon_qa_assistant/apps/chainlit_app.py
from marathon_qa_assistant.apps.chainlit_app import *

if __name__ == "__main__":
    print("请使用以下命令启动应用：")
    print("chainlit run app_chainlit.py -w")
