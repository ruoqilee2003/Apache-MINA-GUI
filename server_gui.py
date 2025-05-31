import asyncio
import random
import tkinter as tk
from tkinter import scrolledtext, ttk

# 全局變數
clients = []
turn_order = []
current_turn = 0
game_started = False
players_ready = asyncio.Event()
game_over = False

MAX_WAIT_SECONDS = 60
secret_number = ''.join(random.choices('0123456789', k=4))
print(f"[DEBUG] Secret number: {secret_number}")

def compute_1a2b(secret, guess):
    A = sum(s == g for s, g in zip(secret, guess))
    secret_rest = [s for s, g in zip(secret, guess) if s != g]
    guess_rest = [g for s, g in zip(secret, guess) if s != g]
    B = 0
    for g in guess_rest:
        if g in secret_rest:
            B += 1
            secret_rest.remove(g)
    return f"{A}A{B}B"

async def broadcast(message, exclude_writer=None):
    for c in clients:
        if c['writer'] != exclude_writer:
            try:
                c['writer'].write((message + "\n").encode())
                await c['writer'].drain()
            except:
                continue

def get_player_index(writer):
    for i, c in enumerate(clients):
        if c['writer'] == writer:
            return i
    return -1

async def rotate_turn(output_text, client_listbox, current_turn_label):
    global current_turn
    if len(turn_order) < 2:
        return False
    current_turn = (current_turn + 1) % len(turn_order)
    # 回合切換後立即更新 GUI
    update_gui(output_text, f"Turn switched to: {clients[turn_order[current_turn]]['name']}", client_listbox, current_turn_label)
    return True

def update_gui(output_text, message, client_listbox, current_turn_label):
    output_text.configure(state='normal')
    output_text.insert(tk.END, message + "\n")
    output_text.configure(state='disabled')
    output_text.see(tk.END)
    client_listbox.delete(0, tk.END)
    for c in clients:
        client_listbox.insert(tk.END, f"{c['name']} {'(Connected)' if not c['writer'].is_closing() else '(Disconnected)'}")
    # 僅在遊戲開始且 turn_order 已初始化後顯示當前回合
    if game_started and turn_order and 0 <= current_turn < len(turn_order):
        current_turn_label.config(text=f"Current Turn: {clients[turn_order[current_turn]]['name']}")
    else:
        current_turn_label.config(text="Current Turn: N/A")

async def handle_client(reader, writer, output_text, client_listbox, current_turn_label, app):
    global current_turn, game_over

    try:
        writer.write(b"Please enter your nickname\n")
        await writer.drain()
        data = await reader.readline()
        if not data:
            writer.close()
            return
        name = data.decode().strip()

        clients.append({'reader': reader, 'writer': writer, 'name': name})
        update_gui(output_text, f"[JOIN] {name} joined.", client_listbox, current_turn_label)
        print(f"[JOIN] {name} joined.")
        writer.write(f"Welcome {name}! Waiting for other players to join...\n".encode())
        await writer.drain()

        await players_ready.wait()

        while True:
            if game_over:
                break

            try:
                data = await asyncio.wait_for(reader.readline(), timeout=300)
            except asyncio.TimeoutError:
                update_gui(output_text, f"[TIMEOUT] {name} timed out.", client_listbox, current_turn_label)
                print(f"[TIMEOUT] {name} timed out.")
                break

            if not data:
                update_gui(output_text, f"[DISCONNECT] {name} disconnected.", client_listbox, current_turn_label)
                print(f"[DISCONNECT] {name} disconnected.")
                break

            guess = data.decode().strip()
            player_index = get_player_index(writer)

            if player_index == -1 or turn_order[current_turn] != player_index:
                writer.write(b"Not your turn! Please wait.\n")
                await writer.drain()
                continue

            update_gui(output_text, f"[TURN] {name} guessed: {guess}", client_listbox, current_turn_label)
            print(f"[TURN] {name} guessed: {guess}")

            if len(guess) != 4 or not guess.isdigit():
                writer.write(b"Invalid input. Enter a 4-digit number.\n")
            else:
                result = compute_1a2b(secret_number, guess)
                await broadcast(f"{name} guessed {guess} → {result}")

                if result == "4A0B":
                    await broadcast(f"{name} WON! The number was {secret_number}")
                    await broadcast("Game over. Thank you for playing!")
                    game_over = True
                    # 關閉所有客戶端連線
                    for c in clients:
                        try:
                            c['writer'].close()
                            await c['writer'].wait_closed()
                        except:
                            pass
                    # 關閉伺服器和 GUI
                    app.root.after(100, app.on_closing)
                    break

                if await rotate_turn(output_text, client_listbox, current_turn_label):
                    next_player = clients[turn_order[current_turn]]
                    await broadcast(f"Now it's {next_player['name']}'s turn!")
                    next_player['writer'].write(b"Your turn!\n")
                    await next_player['writer'].drain()
                else:
                    await broadcast("Not enough players to continue. Game over.")
                    game_over = True
                    # 關閉所有客戶端連線
                    for c in clients:
                        try:
                            c['writer'].close()
                            await c['writer'].wait_closed()
                        except:
                            pass
                    # 關閉伺服器和 GUI
                    app.root.after(100, app.on_closing)
                    break

            await writer.drain()

    except Exception as e:
        update_gui(output_text, f"[ERROR] {e}", client_listbox, current_turn_label)
        print(f"[ERROR] {e}")

    for i, c in enumerate(clients):
        if c['writer'] == writer:
            update_gui(output_text, f"[REMOVE] {c['name']} removed from game.", client_listbox, current_turn_label)
            print(f"[REMOVE] {c['name']} removed from game.")
            left_index = i
            clients.pop(i)

            if game_over:
                break

            if left_index in turn_order:
                turn_order.remove(left_index)
                turn_order[:] = [idx - 1 if idx > left_index else idx for idx in turn_order]

            if len(turn_order) < 2:
                await broadcast("Not enough players to continue. Game over.")
                game_over = True
                # 關閉所有客戶端連線
                for c in clients:
                    try:
                        c['writer'].close()
                        await c['writer'].wait_closed()
                    except:
                        pass
                # 關閉伺服器和 GUI
                app.root.after(100, app.on_closing)
                break

            if current_turn >= len(turn_order):
                current_turn = 0

            if turn_order:
                await broadcast(f"{c['name']} disconnected. Now it's {clients[turn_order[current_turn]]['name']}'s turn!")
                clients[turn_order[current_turn]]['writer'].write(b"Your turn!\n")
                await clients[turn_order[current_turn]]['writer'].drain()
                # 更新 GUI 顯示當前回合
                update_gui(output_text, f"[UPDATE] Current turn after disconnect: {clients[turn_order[current_turn]]['name']}", client_listbox, current_turn_label)

            break

    writer.close()
    await writer.wait_closed()

async def wait_for_players(output_text, client_listbox, current_turn_label):
    print(f"[等待中] 等待玩家連線中（{MAX_WAIT_SECONDS} 秒）")
    await asyncio.sleep(MAX_WAIT_SECONDS)
    if len(clients) < 2:
        print("[取消] 玩家不足，遊戲終止")
        await broadcast("Game canceled: need at least 2 players.")
        for c in clients:
            c['writer'].close()
        return False
    players_ready.set()
    return True

async def start_game(output_text, client_listbox, current_turn_label):
    global turn_order, game_started, current_turn
    turn_order = list(range(len(clients)))
    random.shuffle(turn_order)
    current_turn = 0
    game_started = True

    await broadcast("Game start!")
    await broadcast("Player order: " + " → ".join(clients[i]['name'] for i in turn_order))
    await broadcast(f"First turn: {clients[turn_order[0]]['name']}")
    clients[turn_order[0]]['writer'].write(b"Your turn!\n")
    await clients[turn_order[0]]['writer'].drain()
    # 立即更新 GUI 以顯示當前回合
    update_gui(output_text, f"Game started. First turn: {clients[turn_order[current_turn]]['name']}", client_listbox, current_turn_label)

class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("1A2B 伺服器")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 使用 ttk 主題改進視覺效果
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 當前回合顯示
        self.current_turn_label = ttk.Label(self.main_frame, text="Current Turn: N/A", font=("Arial", 12, "bold"))
        self.current_turn_label.pack(pady=5)

        # 訊息顯示區域
        ttk.Label(self.main_frame, text="遊戲訊息：", font=("Arial", 10)).pack()
        self.output_text = scrolledtext.ScrolledText(self.main_frame, width=60, height=15, state='disabled', font=("Arial", 10))
        self.output_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 客戶端列表
        ttk.Label(self.main_frame, text="連線中的客戶端：", font=("Arial", 10)).pack()
        self.client_listbox = tk.Listbox(self.main_frame, width=30, height=10, font=("Arial", 10))
        self.client_listbox.pack(padx=10, pady=5)

        # 按鈕框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=5)

        # 關閉按鈕
        self.exit_button = ttk.Button(button_frame, text="關閉", command=self.on_closing)
        self.exit_button.pack(side=tk.LEFT, padx=5)

        self.running = True
        self.loop = asyncio.get_event_loop()

    def on_closing(self):
        self.running = False
        # 關閉所有客戶端連線
        for c in clients:
            try:
                c['writer'].close()
                asyncio.run_coroutine_threadsafe(c['writer'].wait_closed(), self.loop)
            except:
                pass
        self.root.destroy()

    def update(self):
        if self.running:
            self.root.after(100, self.update)

async def run_server(app):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, app.output_text, app.client_listbox, app.current_turn_label, app), '127.0.0.1', 8888
    )
    print("Server started on port 8888")
    update_gui(app.output_text, "Server started on port 8888", app.client_listbox, app.current_turn_label)

    async with server:
        ready = await wait_for_players(app.output_text, app.client_listbox, app.current_turn_label)
        if ready:
            await start_game(app.output_text, app.client_listbox, app.current_turn_label)
        await server.serve_forever()

def start_server_in_thread(app):
    loop = app.loop
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_server(app))

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerApp(root)
    update_gui(app.output_text, "Initializing server...", app.client_listbox, app.current_turn_label)

    # 啟動伺服器在獨立線程
    import threading
    server_thread = threading.Thread(target=start_server_in_thread, args=(app,), daemon=True)
    server_thread.start()

    # 啟動 Tkinter 事件迴圈
    app.update()
    root.mainloop()