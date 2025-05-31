import asyncio
import tkinter as tk
from tkinter import scrolledtext, ttk

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("1A2B 多人遊戲")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 使用 ttk 主題改進視覺效果
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 暱稱輸入
        self.nickname_frame = ttk.Frame(self.main_frame)
        self.nickname_frame.pack(pady=5, fill=tk.X)
        ttk.Label(self.nickname_frame, text="請輸入您的暱稱：", font=("Arial", 10)).pack(side=tk.LEFT)
        self.nickname_entry = ttk.Entry(self.nickname_frame, width=20)
        self.nickname_entry.pack(side=tk.LEFT, padx=5)
        self.submit_nickname_button = ttk.Button(self.nickname_frame, text="提交暱稱", command=self.submit_nickname)
        self.submit_nickname_button.pack(side=tk.LEFT)

        # 訊息顯示區域
        ttk.Label(self.main_frame, text="遊戲訊息：", font=("Arial", 10)).pack()
        self.output_text = scrolledtext.ScrolledText(self.main_frame, width=50, height=10, state='disabled', font=("Arial", 10))
        self.output_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 猜測歷史記錄
        ttk.Label(self.main_frame, text="猜測歷史：", font=("Arial", 10)).pack()
        self.history_text = scrolledtext.ScrolledText(self.main_frame, width=50, height=5, state='disabled', font=("Arial", 10))
        self.history_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 猜測輸入
        self.guess_frame = ttk.Frame(self.main_frame)
        self.guess_frame.pack(pady=5, fill=tk.X)
        ttk.Label(self.guess_frame, text="輸入您的猜測（4 位數字）：", font=("Arial", 10)).pack(side=tk.LEFT)
        self.guess_entry = ttk.Entry(self.guess_frame, width=10)
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        self.submit_guess_button = ttk.Button(self.guess_frame, text="提交猜測", command=self.submit_guess, state='disabled')
        self.submit_guess_button.pack(side=tk.LEFT)

        # 離開按鈕
        self.exit_button = ttk.Button(self.main_frame, text="離開", command=self.on_closing)
        self.exit_button.pack(pady=5)

        self.writer = None
        self.reader = None
        self.running = True
        self.guess_history = []

    def on_closing(self):
        self.running = False
        if self.writer:
            self.writer.close()
        self.root.destroy()

    def submit_nickname(self):
        nickname = self.nickname_entry.get().strip()
        if nickname:
            self.writer.write(f"{nickname}\n".encode())
            asyncio.create_task(self.writer.drain())
            self.nickname_entry.config(state='disabled')
            self.submit_nickname_button.config(state='disabled')
            self.update_output("[提示] 暱稱已提交，等待其他玩家...")
        else:
            self.update_output("[錯誤] 請輸入有效的暱稱！")

    def submit_guess(self):
        guess = self.guess_entry.get().strip()
        if guess:
            self.writer.write(f"{guess}\n".encode())
            asyncio.create_task(self.writer.drain())
            self.guess_history.append(f"Guess: {guess} (Waiting for result...)")
            self.update_history()
            self.guess_entry.delete(0, tk.END)

    def update_output(self, message):
        self.output_text.configure(state='normal')
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.configure(state='disabled')
        self.output_text.see(tk.END)

        # 更新猜測歷史中的結果
        if "guessed" in message and "→" in message:
            guess = message.split("guessed")[1].split("→")[0].strip()
            result = message.split("→")[1].strip()
            for i, entry in enumerate(self.guess_history):
                if f"Guess: {guess}" in entry:
                    self.guess_history[i] = f"Guess: {guess} → {result}"
                    self.update_history()
                    break

    def update_history(self):
        self.history_text.configure(state='normal')
        self.history_text.delete(1.0, tk.END)
        for entry in self.guess_history:
            self.history_text.insert(tk.END, entry + "\n")
        self.history_text.configure(state='disabled')
        self.history_text.see(tk.END)

    def enable_guess(self):
        self.submit_guess_button.config(state='normal')

    def disable_guess(self):
        self.submit_guess_button.config(state='disabled')

async def client_game():
    root = tk.Tk()
    app = ClientApp(root)

    app.reader, app.writer = await asyncio.open_connection('127.0.0.1', 8888)

    prompt = await app.reader.readline()
    app.update_output(prompt.decode().strip())

    async def listen_and_play():
        while app.running:
            try:
                data = await asyncio.wait_for(app.reader.readline(), timeout=0.1)
                if not data:
                    app.update_output("[連線中斷] 伺服器已斷線。")
                    app.on_closing()
                    break
                msg = data.decode().strip()
                app.update_output(f"伺服器: {msg}")

                if msg == "Your turn!":
                    app.enable_guess()
                elif "WON!" in msg or "Game over" in msg or "Game canceled" in msg:
                    app.disable_guess()
                    app.root.after(100, app.on_closing)  # 收到遊戲結束訊息後直接退出
                    break

            except asyncio.TimeoutError:
                pass
            except (ConnectionResetError, asyncio.IncompleteReadError):
                app.update_output("[連線中斷] 伺服器已斷線。")
                app.on_closing()
                break

        if app.writer:
            app.writer.close()
            await app.writer.wait_closed()

    asyncio.create_task(listen_and_play())
    while app.running:
        root.update()
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(client_game())