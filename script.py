import websocket
import zstd
from PIL import Image
import threading
import time
import queue

height = 600
width = 1000

start_x = 0
start_y = 0

img = Image.open("img.png")

token = []

board = []
for i in range(0, width):
    board.append([])
    for j in range(0, height):
        board[i].append([0, 0, 0])
        
pic = []
for i in range(0, img.size[0]):
    pic.append([])
    for j in range(0, img.size[1]):
        pic[i].append([0, 0, 0])

ws_app_list = []

def update_paint_board(x, y, color):
    board[x][y] = color
    
def update_picture(x, y, color):
    if color[0] <= 16 and color[1] <= 16 and color[2] <= 16:
        pic[x][y] = [16, 16, 16]
        
    pic[x][y][0] = pic[x][y][0] + color[0]
    pic[x][y][1] = pic[x][y][1] + color[1]
    pic[x][y][2] = pic[x][y][2] + color[2]
    
def compare_color(lhs, rhs):
    if lhs[0] == rhs[0] and lhs[1] == rhs[1] and lhs[2] == rhs[2]:
        return True
    else:
        return False
    
def on_open(ws):
    hex_token = token[ws.now_token].replace("-", "")
    token_msg = [0xff]
    for i in range(0, len(hex_token) - 1, 2):
        token_msg.append(int(hex_token[i : i + 2], 16))
    
    ws.send(bytes(token_msg), opcode = websocket.ABNF.OPCODE_BINARY)
    
def on_message(ws, message):
    raw_data = bytes(message)
    opr = raw_data[0]
    data = raw_data[1:];
    if opr == 0xfd:
        print("This token was unavailable.")
        
    elif opr == 0xfc: # Token auth
        ws.send(bytes([0xf9]), opcode = websocket.ABNF.OPCODE_BINARY)
        print("Token authenticated.")
        
    elif opr == 0xfb: # Init board
        board = zstd.decompress(data)
        if(len(board) != 1800000): # Damaged
            print("Paint board is damaged. Please contact your administrator.")
            
        else: # Normal
            print("Board initialized.")
            idx = 0
            for x in range(0, width):
                for y in range(0, height):
                    update_paint_board(x, y, board[idx : idx + 3])
                    idx = idx + 3
            
    elif opr == 0xfa: # Update board
        for i in range(0, len(data), 7):
            x = data[i + 1] * 256 + data[i]
            y = data[i + 3] * 256 + data[i + 2]
            color = data[i + 4 : i + 7]
            update_paint_board(x, y, color)
            
    else:
        print("Unknown operation. Maybe you should check your internet connection.")
    
class WsApp(object):
    now_token : int
    message_queue : queue.Queue
    ws_connection : websocket.WebSocketApp 
    def message_loop(self):
        while True:
            #while self.message_queue.empty() == False:
            #    self.message_queue.get()
                
            for x in range(0, img.size[0]):
                for y in range(0, img.size[1]):
                    now_x = x + start_x
                    now_y = y + start_y
                    #if pic[x][y] != [255, 255, 255]:
                    message = [
                        0xfe,
                        now_x & 255, (now_x >> 8) & 255,
                        now_y & 255, (now_y >> 8) & 255,
                        pic[x][y][0], pic[x][y][1], pic[x][y][2]
                    ]
                            
                    self.message_queue.put(message)
            
            time.sleep(5)

    def paint_loop(self):
        # global board
        while True:
            if self.message_queue.empty() == False:
                message = self.message_queue.get()
                x = message[1] + message[2] * 256
                y = message[3] + message[4] * 256
                if board[x][y] != [message[5], message[6], message[7]]:
                    board[x][y] = [message[5], message[6], message[7]]
                    self.ws_connection.send(bytes(message), opcode = websocket.ABNF.OPCODE_BINARY)
                    time.sleep(0.50014)
                    print("Token %d painted (%d, %d) with color: R = %d, G = %d, B = %d."
                        %(self.now_token, x, y, message[5], message[6], message[7]))
                
    def main_loop(self):
        print("Opening websocket...")
        self.ws_connection.binary_type = "arraybuffer"
        print("Starting websocket thread...")
        thread_websocket = threading.Thread(target = self.ws_connection.run_forever, args = ())
        thread_websocket.start()
        time.sleep(0.5)
        print("Starting message thread...")
        thread_message = threading.Thread(target = self.message_loop, args = ())
        thread_message.start()
        time.sleep(0.5)
        print("Starting paint thread...")
        thread_paint = threading.Thread(target = self.paint_loop, args = ())
        thread_paint.start()
        
        thread_websocket.join()
        thread_message.join()
        thread_paint.join()
    
    def __init__(self, now_token):
        self.now_token = now_token
        self.message_queue = queue.Queue()
        self.ws_connection = websocket.WebSocketApp(
            url = "wss://paint.yurzhang.com/api/ws",
            on_open = on_open,
            on_message = on_message
        )  
        setattr(self.ws_connection, "now_token", self.now_token)
        self.main_loop()
        
# Procedure

def welcome():
    print("Welcome to Yur Board Painter!!!")
    
def init():
    print("Generating picture data...")
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            color = img.getpixel((x, y))
            update_picture(x, y, [color[0], color[1], color[2]])
    
def main():
    welcome()
    init()
    for i in range(0, len(token)):
        print("Loading token %d" %i)
        tmp_thread = threading.Thread(target = WsApp, args = (i, ))
        ws_app_list.append(tmp_thread)
        
    for i in range(0, len(token)):  
        time.sleep(0.1)
        ws_app_list[i].start()
    
    for i in range(0, len(token)): 
        ws_app_list[i].join()

if __name__ == '__main__':
    # websocket.enableTrace(True)
    main()