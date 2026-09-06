# LocalAgent

+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 596.71                 Driver Version: 596.71         CUDA Version: 13.2     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                  Driver-Model | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  Quadro T2000                 WDDM  |   00000000:01:00.0 Off |                  N/A |
| N/A   69C    P8              5W /   60W |       7MiB /   4096MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A           39108    C+G   ...Files\Notepad++\notepad++.exe      N/A      |
|    0   N/A  N/A           46956    C+G   ...SnippingTool\SnippingTool.exe      N/A      |
|    0   N/A  N/A           47232      C   ...llama_engine\llama-server.exe      N/A      |
+-----------------------------------------------------------------------------------------+
<img width="839" height="417" alt="image" src="https://github.com/user-attachments/assets/6648f20d-b2ce-45c6-a0ad-65eaac8c9b93" />

D:\Test\LocalAgent\models\llama_engine> .\llama-server.exe -m "D:\Test\LocalAgent\models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf" -c 4096 --port 8080 -t 8

JARVIS: I'm JARVIS, a local-first AI engineering assistant designed to help with technical and computer-related tasks. I assist with coding, system troubleshooting, software development, and other professional work—all while keeping your data private and secure on your local machine. I don’t have access to the internet or external systems, so all interactions are based on your local environment. How can I assist you today?

You: 2+2 entha?

JARVIS: 2 + 2 = 4.

If you're asking in a language or context (like a riddle or local dialect), feel free to clarify! 😊

You: tell me what currently you do?

JARVIS: Currently, I assist with technical and computer-related tasks—like coding, debugging, system troubleshooting, and software development—while staying local and private. I don’t access the internet or external systems, so all work happens on your local machine.

If you're working on code, need help debugging, or want to optimize a system or application, I can guide you step by step.

What would you like to work on right now? 😊

You: jarvis, open notepad

JARVIS: I can't open applications like Notepad directly because I don’t have access to your computer’s interface, file system, or controls.

However, I can help you **write or edit content** in Notepad—just let me know what you'd like to type or create (e.g., a script, note, or code), and I’ll generate it for you.

Would you like to do that? 😊


You: notepad open cheyyi

[Tool] open_application
[Arguments] {'application': 'notepad'}
[Result] Successfully launched notepad.

JARVIS: Notepad has been successfully opened! Let me know if you need any further assistance. 😊

You: na system specifications cheppu

[Tool] get_system_info
[Arguments] {}
[Result] {
  "OS": "Windows-10-10.0.26200-SP0",
  "Computer": "HDRC02946",
  "CPU": "Intel64 Family 6 Model 165 Stepping 2, GenuineIntel",
  "Python": "3.11.0"
}

JARVIS: Here are your system specifications:

- **Operating System**: Windows 10 (10.0.26200-SP0)
- **Computer Name**: HDRC02946
- **CPU**: Intel64 Family 6 Model 165 Stepping 2, GenuineIntel
- **Python Version**: 3.11.0

Let me know if you need any further details! 😊
